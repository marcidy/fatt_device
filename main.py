import time
from enum import Enum
from serial import Serial
from util import (
    report_attempt,
    load_whitelist,
)


DEBUG = True
ACTIVITY_TIMEOUT = 5*60  # 5min activity timeout
LASER_COST = 0.5


class StateValues(Enum):
    INIT = 0
    AUTHORIZED = 1
    ENABLED = 2
    FIRING = 3
    DEAUTHORIZED = 4
    DISABLED = 5


class Timer:

    def __init__(self, seconds):
        self.seconds = seconds
        self.running = False
        self.timeout = False
        self.start_time = 0

    def start(self):
        self.running = True
        self.start_time = time.time()

    def check(self):
        '''True if timer is disabled or not timed out'''
        self.timeout = (not self.running or
                        time.time() - self.start_time < self.seconds)
        return self.timeout

    def stop(self):
        self.running = False

    def reset(self):
        self.start_time = time.time()


class Laser:
    '''The pi interfaces with the laser through a Teensy connected via
    a USB port.  The Teensy responds to binary encoded ascii characters,
    and sends binary encoded ascii strings.  The complete interface is
    documented :FIXME:.

    The USB port needs to be reset on initialization to capture it.  This
    requires writing to the USB_PATH as root.

    The Teensy itself runs firmware from :FIXME:

    The Teensy responds to a status command 'o' with the current time
    it's been firing and a flag indiciating a new rfid scan.

    The Teensy state is reported as 'current firiing time since last reset' and
    'new rfid scan'.

    If there has been a new scan, the Teensy will send the ID following a 'r'
    command.

    The pi needs to manage the implications of the state (e.g. an increase in
    firing time indicates the laser has been on, and the pi determines if the
    rfid token is authorized.)

    The laser is a reporting a simple state when polled.  So the pi must
    continually poll the laser state and manage it's authorization state.'''

    USB_PATH = "/sys/bus/usb/devices/usb1/authorized"
    # would prefer if the Teensy weren't so opinionated about what to do.
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

    def cost(self, firing_time):
        return firing_time / 60 * LASER_COST


class AuthManager:

    def __init__(self):
        print("Laser service starting....")
        print(time.time())
        self.rfid_update_time = 0
        self.authorized_rfid = None
        self.update_rfids()
        self.authorized = False

    def update_rfids(self):
        self.whitelist = load_whitelist()

    def check_rfid(self, rfid):
        report_attempt(rfid, self.authorized)
        return rfid in self.whitelist

    def login(self, rfid):
        if self.check_rfid(rfid):
            self.authorized = True
            self.authorized_rfid = rfid
            print("Logged in: {}".format(rfid))

    def logout(self):
        if self.authorized:
            print("Logging out: {}".format(self.authorized_rfid))
        self.authorized = False
        self.authorized_rfid = None


class Controller:

    def __init__(self, manager, resource):
        self.manager = manager
        self.resource = resource
        self.internal_states = self.emit_state()
        self.state = StateValues.INIT
        self.activity_timer = Timer(ACTIVITY_TIMEOUT)
        self.firing_start = 0
        self.firing_end = 0

    def scan(self):
        current_rfid = self.manager.authorized_rfid
        new_rfid = self.resource.rfid()
        self.resource.rfid_flag = '0'

        if self.manager.authorized:
            self.manager.logout()

        if new_rfid != current_rfid:
            self.manager.login(new_rfid)

    def emit_state(self):
        return {
            'odometer': self.resource.odometer,
            'enabled': self.resource.enabled,
            'authorized': self.manager.authorized,
            'scanned': self.resource.rfid_flag == '1'}

    def calculate_state(self):
        new_internal_state = self.emit_state()
        scanned = new_internal_state['scanned']

        if self.state == StateValues.INIT and scanned:
            # only scans new fobs when in INIT state
            self.scan()
            # overwrite new state taking into account scan result
            new_internal_state = self.emit_state()

        enabled = new_internal_state['enabled']
        laser_on = (new_internal_state['odometer'] >
                    self.internal_states['odometer'])
        authorized = new_internal_state['authorized']
        scanned = new_internal_state['scanned']

        # by default, next state = current state
        next_state = self.state

        if laser_on and (not authorized or not enabled):
            print("Error - Laser firing without auth or enable flag set")
            next_state = StateValues.INIT

        elif laser_on:
            next_state = StateValues.FIRING

        elif not laser_on and not authorized:
            next_state = StateValues.INIT

        elif not laser_on and authorized:
            next_state = StateValues.ENABLED

        if not self.activity_timer.check():
            # activity timeout
            next_state = StateValues.INIT

        self.internal_states = new_internal_state
        return next_state

    def run(self):
        self.resource.status()
        next_state = self.calculate_state()

        if next_state == StateValues.INIT:
            self.resource.disable()
            self.manager.logout()
            self.activity_timer.stop()
            self.activity_timer.reset()
            self.resource.display("Please swipe", "fob to continue")

        if self.state == StateValues.INIT and next_state != StateValues.INIT:
            self.activity_timer.start()

        if self.state == StateValues.INIT and next_state == StateValues.ENABLED:
            self.resource.enable()
            self.resource.display("Welcome", self.manager.authorized_rfid)

        if self.state != StateValues.FIRING and next_state == StateValues.FIRING:
            # set up cut and start tracking time and cost
            self.activity_timer.reset()
            self.firing_start = time.time()
            self.resource.display("Elapsed: 1", "Cost: 0")
            print("Firing Start: {}".format(self.firing_start))

        if self.state == next_state and self.state == StateValues.FIRING:
            # update screen with time / cost
            self.activity_timer.reset()
            current_time = min(1, time.time() - self.firing_start)  # in seconds
            self.display(current_time)

        if self.state == StateValues.FIRING and next_state != StateValues.FIRING:
            # end cut, report cost, etc,
            end_time = time.time()
            firing_time = min(1, end_time - self.firing_start)
            self.display(firing_time)
            print("Firing End: {}".format(end_time))
            print("Completed Cut: {},{},{},{},{}".format(
                self.manager.authorized_rfid,
                self.firing_start,
                end_time,
                firing_time,
                self.resource.cost(firing_time)))

        if DEBUG and self.state != next_state:
            print("{} --> {}".format(self.state, next_state))

        self.state = next_state

    def display(self, firing_time):
        display_cost = round(self.resource.cost(firing_time), 2)
        mins = int(firing_time / 60)
        secs = firing_time % 60
        display_time = "{: 2}:{:02}".format(mins, secs)

        self.resource.display("Time: {}".format(display_time),
                              "Cost: {:1.2f}".format(display_cost))


def main():

    manager = AuthManager()
    laser = Laser()
    controller = Controller(manager, laser)
    whitelist_update_timer = Timer(60)
    whitelist_update_timer.start()
    laser.display("Please Wait...", "")

    while True:
        controller.run()
        if not whitelist_update_timer.check():
            manager.update_rfids()
            whitelist_update_timer.reset()
        time.sleep(.1)


if __name__ == '__main__':
    main()
