import gc
import time
import os
import sdcard
import machine
from machine import ADC, Pin, PWM, SPI, I2C, WDT
from bmp280 import BMP280, BMP280_CASE_INDOOR
import ble_module
import clock
import logger

ADC_PIN = 0
SPI_SCK = 19
SPI_MOSI = 18
SPI_MISO = 20
SPI_CS = 17  # assigned SPI chip select for SD card
SDA_PIN = 22
SCL_PIN = 23
LED_PIN = 15  # internal LED for XIAO ESP32-C6

MAX_BUFFER_LINES = 120
INTERVAL_MS = 500  # wait this long between A2D samples in the main loop
BMP_MIN_INTERVAL_MS = 60000  # wait this long between taking temperature/pressure samples

last_log_line = "..."
last_data_line = "???"
temp_f = 0
pressure_inhg = 0
buffer = []
bmp_sample_time = 0


def print_and_log(line):
    global last_log_line
    last_log_line = logger.log(line)


print_and_log('Restarting.')

# try the must-have initialization and reset if it fails
try:
    led = Pin(LED_PIN, Pin.OUT)

    adc = ADC(Pin(ADC_PIN))
    adc.atten(ADC.ATTN_11DB)

    clock.sync_rtc()
    wdt = WDT(timeout=30 * 1000)  # 30 second timeout

    spi = SPI(1, baudrate=400000, sck=Pin(SPI_SCK), mosi=Pin(SPI_MOSI), miso=Pin(SPI_MISO))
    print(f"SPI Parameters: {spi}")
    time.sleep_ms(100)
    sd = sdcard.SDCard(spi, Pin(SPI_CS))
    vfs = os.VfsFat(sd)
    os.mount(vfs, "/sd")

except Exception as e:
    print_and_log(f"Critical init error: {e}")
    time.sleep(5)
    machine.reset()

# try the nice-to-have initialization
try:
    i2c = I2C(0, scl=Pin(SCL_PIN), sda=Pin(SDA_PIN))
    bmp = BMP280(i2c)
    bmp.use_case(BMP280_CASE_INDOOR)

    time.sleep_ms(500)
    ble_module.start_advertising()
except Exception as e:
    print_and_log(f"Secondary init error: {e}")

print_and_log('Initialized.')


def get_filepath_for_buffer(buffer):
    first_sample_timestamp = buffer[0].split(',')[0]
    filename = first_sample_timestamp.split('T')[0]  # split on 'T' for daily or ':' for hourly files
    return f"/sd/{filename}.csv"
    # return f"{filename}.csv" # to save in internal flash memory


def read_sample_line():
    global last_data_line, temp_f, pressure_inhg, bmp_sample_time
    timestamp = clock.iso8601_time()

    elapsed_time_from_bmp_sample = time.ticks_diff(time.ticks_ms(), bmp_sample_time)
    if elapsed_time_from_bmp_sample >= BMP_MIN_INTERVAL_MS:
        print(f'taking another temperature sample at {timestamp}')
        try:
            temp_c = bmp.temperature
            pressure_pa = bmp.pressure
            temp_f = temp_c * 9 / 5 + 32
            pressure_inhg = pressure_pa * 0.0002953
            bmp_sample_time = time.ticks_ms()
        except Exception:
            temp_f = -459.67  # absolute zero
            pressure_inhg = 0

    try:
        adc_mv = round(adc.read_uv() / 1000)
    except Exception:
        adc_mv = 0

    if 100 < adc_mv < 3300:
        # toggle the LED to indicate we're getting reasonable readings
        led.value(not led.value())
    data_line = f"{timestamp}, {adc_mv:5d}, {temp_f:5.1f}, {pressure_inhg:5.2f}"
    last_data_line = data_line
    return f"{data_line}\n"


while True:
    try:
        sample_time = time.ticks_ms()
        sample_row = read_sample_line()
        buffer.append(sample_row)
        wdt.feed()

        if len(buffer) % 60 == 10:
            try:
                ble_data = last_log_line + '\n' + last_data_line
                ble_module.write_and_notify(ble_data)
            except Exception as ble_e:
                print_and_log(f"Bluetooth notification error: {ble_e}")

        if len(buffer) >= MAX_BUFFER_LINES:
            file_path = get_filepath_for_buffer(buffer)

            try:
                with open(file_path, "a") as f:
                    f.write("".join(buffer))  # Write all rows at once
            except OSError as e:
                print_and_log(f"Error writing to file: {e}")

            buffer.clear()
            free_memory = gc.mem_free()
            if free_memory < 100000:
                print_and_log(f"Free memory before GC: {free_memory}")
            gc.collect()
            free_memory = gc.mem_free()
            if free_memory < 200000:
                print_and_log(f"Free memory after GC: {free_memory}")

        # Aim for a total of INTERVAL_MS ms between samples (yes, it will still drift. there are better ways...)
        elapsed_time = time.ticks_diff(time.ticks_ms(), sample_time)
        sleep_duration = max(0, INTERVAL_MS - elapsed_time)
        if sleep_duration < INTERVAL_MS / 2:
            print_and_log(f'sleeping for {sleep_duration} ms')
        time.sleep_ms(sleep_duration)

    except Exception as e:
        print_and_log(f"Unexpected error: {e}")
        time.sleep(5)
        machine.reset()
