''' defaults.py: set defaults specific to the makerspace-auth board

The Makerspace auth board does not contain hardware or software defaults.
This recociles it in a very simple way.   Pass the pins you intend to use to
the set_defaults function as a a list and it will skip setting defaults for
them.
'''

import RPi.GPIO as gpio

DEFAULTS = {
    7: gpio.LOW,
    11: gpio.LOW,
    12: gpio.LOW,
    13: gpio.LOW,
    15: gpio.LOW,
    16: gpio.LOW,
    18: gpio.LOW,
    22: gpio.LOW,
    29: gpio.LOW,
    31: gpio.LOW,
    32: gpio.LOW,
    33: gpio.LOW,
    35: gpio.LOW,
    36: gpio.LOW,
    37: gpio.LOW,
    38: gpio.LOW,
    40: gpio.LOW,
}


def set_defaults(except_channels):
    gpio.setmode(gpio.BOARD)
    for channel, value in DEFAULTS.items():
        if channel not in except_channels:
            gpio.setup(channel, gpio.OUT, initial=value)
