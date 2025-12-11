from machine import Pin
from time import sleep

led = Pin(2, Pin.OUT)   # ESP32/ में PIN 2 पर LED

while True:
    led.value(1)
    sleep(0.5)
    led.value(0)
    sleep(0.5)
#micro python
