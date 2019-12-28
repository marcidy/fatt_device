import time
from enum import Enum
try:
    from subprocess import run
except ImportError:
    from subprocess import call as run
from serial import Serial
from util import (
    report_attempt,
    load_whitelist,
)


DEBUG = True


class Timer:

    def __init__(self, seconds):
        self.__seconds = seconds
        self.__running = False
        self.__timeout = False
        self.start_time = 0

    def start(self):
        self.__running = True
        self.__start_time = time.time()

    def check(self):
        '''True if timer is disabled or not timed out'''
        self.__timeout = (not self.__running or
                          time.time() - self.__start_time < self.__seconds)
        return self.__timeout

    def stop(self):
        self.__running = False

    def reset(self):
        self.__start_time = time.time()


class Laser:

    USB_PATH = "/sys/bus/usb/devices/usb1/authorized"
    # would prefer if the ATTINY weren't so opinionated about what to do.
    # why save to eeprom when you can just send information about if the
    # laser is firing to the rpi and save it there?
    # Why using such a slow baudrate?  ATTINYs are fast.

    def __init__(self, port='/dev/ttyACM0', baudrate=9600):
        self.reset_usb()
        time.sleep(1)
        self.conn = Serial(port, baudrate)
        self.disable()  # Do I need to send disable on service start?
        self.status()

    def write_raw(self, msg):
        self.conn.write(msg)

    def write(self, msg):
        self.write_raw(bytes('{}\n'.format(msg), 'ascii'))

    def read_raw(self):
        # default terminator is '\n' but explict is good
        return self.conn.read_until(b'\n')

    def read(self):
        more = self.conn.in_waiting > 0
        data = b''
        while more:
            data += self.read_raw()
            if self.conn.in_waiting <= 0:
                more = False
        if data:
            return data.decode('ascii').strip('\n')
        else:
            return ''

    def enable(self):
        self.write("e")
        self.enabled = True

    def disable(self):
        self.write("d")
        self.enabled = False

    def reset_usb(self):
        with open(self.USB_PATH, 'w') as f:
            f.write('0')
            time.sleep(1)
            f.write('1')

    def display(self, line1='', line2=''):
        if line1:
            self.write('p'+line1)
        if line2:
            self.write('q'+line2)

    def status(self):
        ''' Reads status from the laser, which is a string
        'o{cut_time}x{rfid_flag}'
        cut_time is how long the laser has been firing for
        rfid_flag indicates if a swipe was done'''

        self.write('o')
        time.sleep(.1)
        data = self.read()
        if data:
            try:
                self.odometer, self.rfid_flag = data[1:].split('x')
            except Exception:
                print("Error: status - {}".format(data))

    def rfid(self):
        self.write("r")
        time.sleep(.1)
        data = self.read()[1:]
        if len(data) == 8:
            return data
        if len(data) == 10:
            return data[2:]

    def reset_cut_time(self):
        self.write('x')

    def update_cut_time(self):
        self.write('y')

    def read_cut_time(self):
        self.write('z')


class AuthManager:

    def __init__(self):
        print("Laser service starting....")
        print(time.time())
        self.rfid_update_time = 0
        self.last_scanned_rfid = None
        self.authorized_rfid = None
        self.authorized = False
        self.authorization_timeout = Timer(10*60)  # 10m timeout

    def update_rfids(self):
        if time.time() - self.rfid_update_time > 60*5:
            # check for new whitelist every 5m
            self.authorized_rfids = load_whitelist()
            self.rfid_update_time = time.time()

    def check_rfid(self, rfid):
        report_attempt(rfid, self.authorized)
        return rfid in self.authorized_rfids

    def login(self, rfid):
        if self.check_rfid(rfid):
            self.authorized = True
            self.authorized_rfid = rfid
            print("Logged in: {}".format(rfid))
            self.authorization.timeout.start()

    def logout(self):
        if self.authorized:
            print("Logging out: {}".format(self.authorized_rfid))
        self.authorized = False
        self.authorized_rfid = None
        self.authorization_timeout.stop()
        self.authorization_timeout.reset()

    def pet(self):
        self.authorization_timeout.reset()


class State(Enum):
    INIT = 0
    AUTHORIZED = 1
    ENABLED = 2
    FIRING = 3
    DEAUTHORIZED = 4


def main():

    # Pull status from Teensy.  Updates RFID flag and cut time
    manager = AuthManager()
    laser = Laser()
    state = State.INIT
    rfid = None
    next_state = state
    laser.display("Scan fob to start", "")
    last_laser_odometer = laser.odometer()

    while True:
        laser.status()

        if laser.odometer > last_laser_odometer:
            # If the odometer is increasing, the laser is firing.  This is
            # defined behavior in the teensy firmware.  This is not the
            # ideal indicator, we should bring the actual value of the
            # firing pin directly to the pi.
            state = State.FIRING
            # This is an immediate set as it is reflecting existing state.

        if state == State.FIRING and not manager.authorized:
            # catch bad state
            laser.disable()
            manager.logout()
            next_state = State.Init
            line1, line2 = ("** ERROR **", "Bad Laser State!")
            print("ERROR: Laser fired without Authorization Flag")

        if laser.rfid_flag == '1':
            # New scan reported by Teensy
            rfid = laser.rfid()

        if state == State.INIT:

            if rfid and not manager.authroized:
                manager.login(laser.rfid())
                laser.enable()
                next_state = State.ENABLED
                line1, line2 = ("{}".format(manager.authorized_rfid),
                                "Logged in")
            elif rfid == manager.authorized_rfid:
                next_state = State.DEAUTHORIZED

        elif state == State.ENABLED:
            # Timer is ticking down in this state
            pass

        elif state == State.FIRING and manager.authorized:
            # firing, display odometer and cost
            line1, line2 = ("IMAA FIRE", "MUH LAZOR")
            manager.pet()

        elif state == State.DEAUTHRORIZED:
            laser.disable()
            manager.logout()
            line1, line2 = ("Logging out...", "Swipe to Login")
            next_state = State.INIT

        if manager.authorization_timeout.check() is False:
            next_state = State.DEAUTHORIZED
            line1 = "Inactivity Timeout"

        # clean up, set next state
        laser.display(line1, line2)
        laser.rfid_flag = '0'
        rfid = None
        last_laser_odometer = laser.odometer()
        if DEBUG:
            if next_state != state:
                print("{} --> {}".format(state, next_state))
        state = next_state

        time.sleep(.1)


if __name__ == '__main__':
    main()
