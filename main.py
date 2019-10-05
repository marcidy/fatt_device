import RPi.GPIO as gpio
import time
from defaults import set_defaults

bit_string = ''  # ID string of bits e.g. '1001'
previous_bit_detected_time = 0  # Time of last bit detected
bit_detected = False  # have we started detecting a scan?
bit_string_time_out_ms = 100  # miliseconds

locked = True  # is the door currently locked?
lock_opened_time = 0  # when did we unlock the door?
lock_open_delay_s = 1  # open delay in seconds

DEBUG = True

def reset_scan():
    global bit_string
    global bit_detected

    bit_detected = False
    bit_string = ''


def detect(pin):
    global bit_string
    global bit_detected
    global previous_bit_detected_time

    bit_detected = True
    previous_bit_detected_time = time.time()
    values = {7: '0', 13: '1'}
    bit_string += values[pin]
    if DEBUG:
        print("detecting: {}, prevtime: {}, bs: {}".format(bit_detected, previous_bit_detected_time, bit_string))


def unlock_door():
    global locked
    global lock_opened_time
    
    gpio.output(31, gpio.HIGH)
    lock_opened_time = time.time()
    locked = False


def lock_door():
    global locked
    gpio.output(31, gpio.LOW)
    locked = True


gpio.setmode(gpio.BOARD)
# setting default pins to give somewhat calmer electrical behavior on makerspace-auth board
set_defaults([7, 13, 31])
# Confgure weigan reader pins as inputs, pulled up, which call the 'detect' function when a falling edge
# is detected.
gpio.setup(7, gpio.IN, pull_up_down=gpio.PUD_UP)
gpio.setup(13, gpio.IN, pull_up_down=gpio.PUD_UP)
gpio.add_event_detect(7, gpio.FALLING, callback=detect)
gpio.add_event_detect(13, gpio.FALLING, callback=detect)

# pin 31 connects to J12 connector which is the relay
gpio.setup(31, gpio.OUT)


if __name__ == "__main__":

    reset_scan()
    lock_door()
    authorized = False
    scanned_id = ''

    with open("authorized.txt", 'r') as f:
        authorized_rfids = f.read().split("\n")

    while True:
        if (bit_detected and (time.time() - previous_bit_detected_time)*1000 > bit_string_time_out_ms):
            # Noise from load currently triggers spurious reads on wiegand inputs.
            # More than 30 bits of data on the interface indicates a decent attempted at an RFID.
            if len(bit_string) > 30:   
                scanned_id = str(hex(int(bit_string[:-1], 2))).upper()[3:]
                authorized = scanned_id in authorized_rfids
                print("ID: {} Authorized: {}".format(scanned_id, authorized))
            reset_scan()

        if authorized and locked is True:
            authorized = False
            unlock_door()

        if (not locked and (time.time() - lock_opened_time) > lock_open_delay_s):
            lock_door()

        time.sleep(.001)
