import time
from machine import RTC, I2C, Pin

internal_rtc = RTC()

i2c = I2C(0, scl=Pin(23), sda=Pin(22))  # For XIAO c6 board
DS3231_I2C_ADDR = 0x68


def bin2bcd(value):
    return (value // 10) << 4 | (value % 10)


def bcd2bin(value):
    return ((value >> 4) * 10) + (value & 0x0F)


def set_time_to_ds3231(year, month, day, hour, minute, second):
    data = bytearray([
        bin2bcd(second),
        bin2bcd(minute),
        bin2bcd(hour),
        bin2bcd(0),  # Day of week (1-7, not used)
        bin2bcd(day),
        bin2bcd(month),
        bin2bcd(year - 2000)
    ])
    i2c.writeto_mem(DS3231_I2C_ADDR, 0, data)


def get_time_from_ds3231():
    """Read time from the external DS3231 RTC module"""
    data = i2c.readfrom_mem(DS3231_I2C_ADDR, 0, 7)

    second = bcd2bin(data[0] & 0x7F)
    minute = bcd2bin(data[1] & 0x7F)
    hour = bcd2bin(data[2] & 0x3F)
    day = bcd2bin(data[4] & 0x3F)
    month = bcd2bin(data[5] & 0x1F)
    year = bcd2bin(data[6]) + 2000

    return (year, month, day, 0, hour, minute, second, 0)  # Format for internal RTC


def sync_rtc():
    """Synchronize the internal RTC with the external DS3231"""
    ds3231_time = get_time_from_ds3231()
    internal_rtc.datetime(ds3231_time)


def get_current_time():
    """Get formatted time from internal RTC"""
    dt = internal_rtc.datetime()
    return f"{dt[0]}-{dt[1]:02d}-{dt[2]:02d} {dt[4]:02d}:{dt[5]:02d}:{dt[6]:02d}"


def seconds_since_2000():
    rtc = RTC()
    current_datetime = rtc.datetime()
    year, month, day, weekday, hours, minutes, seconds, subseconds = current_datetime

    # Calculate days since 1/1/2000
    days_per_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    year_days = (year - 2000) * 365 + ((year - 2000) // 4)  # Add leap years
    month_days = sum(days_per_month[:month - 1])  # Days in previous months this year
    # Adjust for leap year if current year is a leap year and we're past February
    if month > 2 and (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)):
        month_days += 1
    total_days = year_days + month_days + day - 1  # -1 because we start from day 1
    total_seconds = total_days * 86400 + hours * 3600 + minutes * 60 + seconds
    return total_seconds


def iso8601_time():
    # Get the current time as a tuple (year, month, day, hour, minute, second, ...)
    t = time.localtime()

    nanoseconds = time.time_ns() - time.time() * 1_000_000_000
    milliseconds = int(nanoseconds / 1_000_000)

    # Format it as ISO 8601 with milliseconds (YYYY-MM-DDTHH:MM:SS.mmm)
    return "{:04d}-{:02d}-{:02d}T{:02d}:{:02d}:{:02d}.{:03d}".format(
        t[0], t[1], t[2],  # Year, month, day
        t[3], t[4], t[5],  # Hour, minute, second
        milliseconds  # Milliseconds
    )


def check_drift():
    for i in range(100000):
        rtc_time1 = get_time_from_ds3231()
        time.sleep_us(10)
        rtc_time2 = get_time_from_ds3231()
        int_time = internal_rtc.datetime()
        if (rtc_time1[6] != rtc_time2[6]):
            print("DS3231 time:", rtc_time2)
            print("Internal tm:", int_time)
    print('==========')


if __name__ == "__main__":
    # set_time_to_ds3231(2025, 3, 24, 22, 25, 40)
    # sync_rtc()
    print("External RTC time:", get_time_from_ds3231())
    print("Internal RTC time:", internal_rtc.datetime())
    print("iso8601_time:", iso8601_time())
