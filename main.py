import time
from enum import Enum
from serial import Serial
from util import (
    report_attempt,
    load_whitelist,
)


DEBUG = True
ACTIVITY_TIMEOUT = 10*60  # 10min activity timeout
LASER_COST = 0.5
MIN_CUT_TIME = 60  # minumum cut time is 60s.  All laser activity separated by less than 60s is a single cut


class StateValues(Enum):
    ''' Enum for controller states '''
    INIT = 0
    ENABLED = 1
    FIRING = 2


class Timer:
    '''Basic timer which starts, stops, reports if it's runnings, etc.

    :param seconds: Length between timer.start called and timer.check is True
    :type seconds: float
    '''

    def __init__(self, seconds):
        self.seconds = seconds
        self.running = False
        self.timeout = False
        self.start_time = 0

    def start(self):
        ''' sets self.running to True and sets self.start_time '''
        self.running = True
        self.start_time = time.time()

    def check(self):
        '''True if timer is disabled or not timed out
        sets self.timeout to True if timer is expired

        :returns: if timer is still active
        :rtype: bool
        '''
        if self.running:
            self.timeout = time.time() - self.start_time > self.seconds
        return self.timeout or not self.running

    def stop(self):
        '''Stops the timer, sets self.running to False'''
        self.running = False

    def reset(self):
        '''Resets the start time, resetting the timer without stopping it'''
        self.start_time = time.time()
        self.timeout = False


class Laser:
    '''The pi interfaces with the laser through a Teensy connected via
    a USB port.  The Teensy responds to binary encoded ascii characters,
    and sends binary encoded ascii strings.  The interface is
    documented here: https://github.com/acemonstertoys/laser-rfid

    The USB port needs to be reset on initialization to capture it.  This
    requires writing to the USB_PATH as root.

    The Teensy itself runs firmware from the same repo as above.

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
    continually poll the laser state and manage it's authorization state.

    :param port: system serial port path
    :type port: string
    :param baudrate: serial port baudrate
    :type baudrate: int
    '''
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
        self.conn.reset_input_buffer()
        self.conn.write(msg)

    def write(self, msg):
        self.write_raw(bytes('{}\n'.format(msg), 'ascii'))

    def read_raw(self):
        # default terminator is '\n' but explict is good
        return self.conn.read_until(b'\n')

    def read(self):
        ''' Grabs data from the serial port, decodes, and strips protocol
        control chars, currently '\n'.  This function should be used rather
        than reading hte Sesrial connection directly for uniformity.
        '''
        more = True
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
        ''' Enables the laser through Teensy '''
        self.write("e")
        self.enabled = True

    def disable(self):
        ''' Disable the laser through Teensy '''
        self.write("d")
        self.enabled = False

    def reset_usb(self):
        ''' Resets the USB port, specific to sysfs paths'''
        with open(self.USB_PATH, 'w') as f:
            f.write('0')
            time.sleep(1)
            f.write('1')

    def display(self, line1='', line2=''):
        ''' Displays on the 2-line VCD display connected to Teesy '''
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
            except (IndexError, TypeError) as e:
                print("{}: status - {}".format(e, data))

    def rfid(self):
        ''' requests rfid string from Teensy, returns 8 bits only.  For
        compatibility, can use 8bit or 10bits.
        '''
        self.write("r")
        time.sleep(.1)
        data = self.read()[1:]
        if len(data) == 8:
            return data
        if len(data) == 10:
            return data[2:]

    def reset_cut_time(self):
        ''' Part of Teensy laser interface.  Resets odometer on teensy'''
        self.write('x')

    def update_cut_time(self):
        ''' Explicit update of odometer'''
        self.write('y')

    def read_cut_time(self):
        ''' Retrieve odometer from Teensy'''
        self.write('z')

    def cost(self, firing_time):
        return firing_time / 60 * LASER_COST


class AuthManager:
    ''' Abstracts authentication state.  Warehouses rfid updating,
    authorization, and authorized id.
    '''

    def __init__(self):
        print("Laser service starting....")
        print(time.time())
        self.rfid_update_time = 0
        self.authorized_rfid = None
        self.update_rfids()
        self.authorized = False

    def update_rfids(self):
        ''' sets whitelist.  Should be called on a timer in the main loop '''
        self.whitelist = load_whitelist()

    def check_rfid(self, rfid):
        ''' Compares rfid to whitelist, return True if rfid in white list,
        False if not
        :param rfid: Hex string of rfid to check
        :type rfid: string

        :returns: True if rfid is in whitelist, false if not
        :rtype: bool
        '''
        authorized = rfid in self.whitelist
        report_attempt(rfid, authorized)
        return authorized

    def login(self, rfid):
        ''' logs a user in by rfid if rfid is valid, logs to system out

        :param rfid: Hex string of rfid to check
        :type rfid: string
        '''
        if self.check_rfid(rfid):
            self.authorized = True
            self.authorized_rfid = rfid
            print("Logged in: {}".format(rfid))

    def logout(self):
        ''' logs user out'''

        if self.authorized:
            print("Logging out: {}".format(self.authorized_rfid))
        self.authorized = False
        self.authorized_rfid = None


class Controller:
    ''' The controller takes instanciated AuthManager and resource (e.g., the
    laser) and computes the current state, state transition, and manages the
    state transition.  It's a statemachine.  Hardware is a statemachine, and
    state machines are highly tractible to analyze for completeness, thus are
    ideal for cointrolling hardware.

    The below implementation can be generalized to other resources fairly
    easily, but not all resources behave like the laser.  Currently the laser
    has display, rfid scanning, and firing time all on the same interface,
    so a more general approach would abstract these inputs further.

    The only thing the main loop interacts with is the controller, which uses
    the AuthManager and inspects the resource.

    :param manager: AuthManager instance
    :type manager: AuthManager
    :param resource: Currently Laser is an example of a compliant resource
    :type resource: something which implements an odometer, rfid scanning,
    enable/disabling, and cost.
    '''

    def __init__(self, manager, resource):
        self.manager = manager
        self.resource = resource
        self.internal_states = self.emit_state()
        self.state = StateValues.INIT
        self.activity_timer = Timer(ACTIVITY_TIMEOUT)
        self.cut_timer = Timer(MIN_CUT_TIME)
        self.firing_start = 0
        self.firing_end = 0

    def scan(self):
        ''' retrieves an rfid from the resource and decides what to do with it
        based on the state of the auth manager'''

        current_rfid = self.manager.authorized_rfid
        new_rfid = self.resource.rfid()
        self.resource.rfid_flag = '0'

        if self.manager.authorized:
            self.manager.logout()

        if new_rfid != current_rfid:
            self.manager.login(new_rfid)

    def emit_state(self):
        ''' Retrieve state variables from resource and manager.'''
        return {
            'odometer': self.resource.odometer,
            'enabled': self.resource.enabled,
            'authorized': self.manager.authorized,
            'scanned': self.resource.rfid_flag == '1'}

    def calculate_state(self):
        ''' From current state information, the next state if calculated.  This
        function explicitly separates the concerns of computing the next state
        from transitioning to the next state.  This makes transitions explicit
        and separates out the dependencies.
        '''
        new_internal_state = self.emit_state()
        scanned = new_internal_state['scanned']

        # only scans new fobs when in INIT state
        if scanned and self.state in [StateValues.INIT, StateValues.ENABLED]:
            self.scan()
            # overwrite new state taking into account scan result
            new_internal_state = self.emit_state()

        # state variables
        enabled = new_internal_state['enabled']
        laser_on = (new_internal_state['odometer'] >
                    self.internal_states['odometer'])
        authorized = new_internal_state['authorized']
        scanned = new_internal_state['scanned']
        cutting = self.cut_timer.running and not self.cut_timer.timeout
        
        # by default, next state = current state
        next_state = self.state

        if laser_on and (not authorized or not enabled):
            print("Error - Laser firing without auth or enable flag set")
            next_state = StateValues.INIT

        elif laser_on:
            next_state = StateValues.FIRING

        elif not laser_on and not authorized:
            next_state = StateValues.INIT

        # cut_done adds a filter on the laser signal to keep the state in FIRING for MIN_CUT_TIME
        # if a cut had been started.  This quiets the logging / reporting since the odometer is
        # updated on 500ms intervals, and im not really interested in limiting the controller
        # unecessarily.
        #
        # cut_done is a timer. If started, check will be True until it times out.  The timer
        # is resetted during state transition each time we stop firing.  If the laser stops
        # firing, and then times out, a new cut will be started by placing the controller
        # in the ENABLED state.
        elif not laser_on and authorized and not cutting:
            next_state = StateValues.ENABLED

        # hold the laser in firing until we get a cutting timeout.
        elif self.state == StateValues.FIRING and not laser_on and authorized and cutting:
            next_state = StateValues.FIRING

        if not self.activity_timer.check():
            # activity timeout
            next_state = StateValues.INIT

        self.internal_states = new_internal_state
        return next_state

    def run(self):
        ''' Run is the only function to call, the next state is calculated
        by calling calculate_state, and hte body of the function manages the
        state transition.

        the state machines is designed to explicitly depend only on this state
        and the known next state.  This allows the state machines to be
        easy to analyze for illegal transitions, and complete coverage
        of the logic to transition between states.

        The state machiens is written as a logic statement to describe the
        transition, and what to do to perform the transition.

        The transitions are not mutually exclusive

        '''
        self.resource.status()
        next_state = self.calculate_state()

        # Base case return to INIT from a logged in state.
        if self.state != StateValues.INIT and next_state == StateValues.INIT:
            # Cut timer time out
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

        # The initial state means teh resource is disabled and the devices is
        # not authorized.
        # The activity timer is also disabled.
        if next_state == StateValues.INIT:
            self.resource.disable()
            self.manager.logout()
            self.activity_timer.stop()
            self.activity_timer.reset()
            self.cut_timer.stop()
            self.cut_timer.reset()
            self.resource.display("Please swipe", "fob to continue")

        # If we are transitioning from the INIT state, beging the activity
        # timer.
        if self.state == StateValues.INIT and next_state != StateValues.INIT:
            self.activity_timer.start()

        # If we are moving from INIT to ENABLED, enable the resource during
        # the transition
        if self.state == StateValues.INIT and next_state == StateValues.ENABLED:
            self.resource.enable()
            self.resource.display("Welcome", self.manager.authorized_rfid)

        # If we are enabled, check the cut time.  This will set up the processing
        # of a timeout next time state is checked.  If the timer isn't running, check doesn't
        # do anything.
        if self.state == next_state and next_state == StateValues.ENABLED:
            self.cut_timer.check()

        # If we are transitioning to FIRING from not firing, update the
        # activity timer, and begin tracking firing time
        if self.state != StateValues.FIRING and next_state == StateValues.FIRING:
            # set up cut and start tracking time and cost
            self.activity_timer.reset()
            self.firing_start = time.time()
            self.resource.display("Time: 1", "Cost: 0")
            print("Firing Start: {}".format(self.firing_start))

        # if we are currently firing and we're still firing, update the timer
        if self.state == next_state and self.state == StateValues.FIRING:
            # update screen with time / cost
            self.activity_timer.reset()
            current_time = min(1, time.time() - self.firing_start)  # in seconds
            self.display(current_time)

        # If we are done firing, stop the timer, and report the cut
        if self.state == StateValues.FIRING and next_state != StateValues.FIRING:
            if not self.cut_timer.running:
                self.cut_timer.start()
                if DEBUG:
                    print("Starting cut timer")
            elif self.cut_timer.check():
                self.cut_timer.reset()
                if DEBUG:
                    print("Resetting cut timer")

        if DEBUG and self.state != next_state:
            print("{} --> {}".format(self.state, next_state))

        # Transition the state variable
        self.state = next_state

    def display(self, firing_time):
        ''' Helper function to display the time and cost of an ongong cut

        :param firing_time: Time, in seconds
        :type firing_time: int
        '''

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
