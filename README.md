MicroPython data logger for the ESP32. Tested on the XIAO ESP32-C6.
Log data via the A2d converter onto a micro SD card. Create a new csv file every day. 
Use an external RTC to initialize the time. Also log temperature and pressure from a BMP280.
Use BLE to boradcast occassional status.

External dependencies found elsewhere:
  * sdcard
  * bmp280
  * ble_module
