import time
try:
    from subprocess import run
except ImportError:
    from subprocess import call as run
from serial import Serial
from util import (
    report_attempt,
    load_whitelist,
)


class Cut:
    '''Handle current cut with context manager'''

    def __init__(self, user):
        self.user = user
        self.start = None
        self.stop = None

    def start(self):
        if self.start is not None:
            raise ValueError("Cut already started!")
        self.start = time.time()

    def time(self):
        '''time of cut, in seconds, since self.start'''
        _stop = self.stop if self.stop is not None else time.time()
        return _stop - self.start

    def cost(self, price_per_min):
        ''' price of cut is a cost per minute, so the length of the cut
        is turned into minutes '''
        return price_per_min * self.time()/60

    def __enter__(self):
        if self.user is None:
            raise ValueError("Attempted to cut without setting cut user")
        self.start()

    def __exit__(self):
        self.stop = time.time()

    def report(self):
        return {'time': self.time(), 'cost': self.cost()}

    def __str__(self):
        return "User: {}, Cost: {}, Start: {}, End: {}".format(
            self.user, self.cost, self.start, self.stop)


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
        self.enabled = False  # Do I need to send disable on service start?
        self.authorized = None
        self.odometer = ''
        self.rfid_flag = ''
        self.current_cut = None

    def write_raw(self, msg):
        self.conn.write(msg)

    def write(self, msg):
        self.write_raw(b'{}\n'.format(msg.encode('ascii')))

    def raw_read(self):
        # default terminator is '\n' but explict is good
        return self.conn.read_until(b'\n')

    def read(self):
        more = True
        data = b''
        while more:
            data += self.raw_read()
            if self.conn.in_waiting <= 0:
                more = False
        if data:
            return data.decode('ascii')
        else:
            return ''

    def enable(self):
        self.write("e")
        self.enabled = True

    def disable(self):
        self.write("d")
        self.enabled = False

    def reset_usb(self):
        run(["echo", "0", self.USB_PATH])
        run(["echo", "1", self.USB_PATH])
        time.sleep(2)

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
        data = self.read()
        if data:
            try:
                self.odometer, self.rfid_flag = data[1:].split('x')
            except Exception:
                print("Error: status - {}".format(data))

    def rfid(self):
        self.write("r")
        data = self.read()
        return data[1:]

    def reset_cut_time(self):
        self.write('x')

    def update_cut_time(self):
        self.write('y')

    def read_cut_time(self):
        self.write('z')


if __name__ == '__main__':
    print("Laser service starting....")
    print(time.time())
    rfid_update_time = 0
    last_scanned_rfid = None
    authorized_rfids = []
    authorized = False
    laser = Laser()
    cut = None

    while True:
        if time.time() - rfid_update_time > 60*5:
            # check for new whitelist every 5m
            authorized_rfids = load_whitelist()
            rfid_update_time = time.time()

        # Pull status from Teensy.  Updates RFID flag and cut time
        Laser.status()

        if Laser.rfid_flag == '1':
            rfid = Laser.rfid()
            if rfid:
                authorized = rfid in authorized_rfids
                report_attempt(rfid, authorized)
            cut = Cut(rfid)  # set up current cut for this user
            Laser.rfid_flag = '0'

        # What is the enble vs authorized flow?
        # 0 - not enabled, not authorized
        # 1 - authorized, not enabled
        # 2 - not authorized, enabled ( illegal )
        # 3 - authorized, enabled

        # if authorized:
        #    what does a new RFID scan mean?  Surely I dont stop the cut.
        #    ignore if enabled?

        time.sleep(.001)  # sleep to the OS for 1ms
