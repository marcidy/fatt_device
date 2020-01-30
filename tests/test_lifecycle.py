from unittest.mock import patch, Mock
from main import StateValues


@patch('main.report_attempt')
def test_lifecycle_config(mock_report_attempt,
                          MockControllerLifecycle,
                          authorized_rfids):
    controller = MockControllerLifecycle
    assert len(controller.manager.whitelist) == 2

    assert not controller.manager.authorized
    assert not controller.manager.authorized_rfid
    assert not controller.resource.enabled
    assert controller.state == StateValues.INIT


@patch('main.requests.post')
@patch('main.report_attempt')
def test_lifecycle_basic(requests_post,
                         mock_report_attempt,
                         MockControllerLifecycle,
                         authorized_rfids):
    ''' id logs in, laser fires, and id logs out '''
    controller = MockControllerLifecycle
    test_id = authorized_rfids[0]

    # Set up the sequence of serial reads based on the Teensy protocol
    # scannned
    # read rfid
    # odometer increase (firing)
    # odometer stable (not firing)
    # scanned
    # logout
    serial_reads = ['o1000x0',
                    'o1000x1',
                    'r'+test_id,
                    'o1100x0',
                    'o1100x0',
                    'o1100x1',
                    'r'+test_id,
                    ]
    controller.resource.read.side_effect = serial_reads

    controller.run()
    assert controller.state == StateValues.INIT

    controller.run()
    assert controller.state == StateValues.ENABLED

    controller.run()
    assert controller.state == StateValues.FIRING

    controller.run()
    assert controller.state == StateValues.ENABLED

    controller.run()
    assert controller.state == StateValues.INIT


@patch('main.requests.post')
@patch('main.report_attempt')
def test_lifecycle_switch_user(requests_post,
                               mock_report_attempt,
                               MockControllerLifecycle,
                               authorized_rfids):
    controller = MockControllerLifecycle
    test_id1 = authorized_rfids[0]
    test_id2 = authorized_rfids[1]

    # Test script
    # scanned
    # read rfid
    # odometer increase (firing)
    # odometer stable (not firing)
    # scanned
    # old user logged out
    # new user logged in

    serial_reads = ['o1000x0',
                    'o1000x1',
                    'r'+test_id1,
                    'o1100x0',
                    'o1100x0',
                    'o1100x1',
                    'r'+test_id2,
                    'o1100x1',
                    'r'+test_id2,
                    ]

    controller.resource.read.side_effect = serial_reads

    controller.run()
    assert controller.state == StateValues.INIT

    controller.run()
    assert controller.state == StateValues.ENABLED

    controller.run()
    assert controller.state == StateValues.FIRING

    controller.run()
    assert controller.state == StateValues.ENABLED

    controller.run()
    assert controller.state == StateValues.INIT

    controller.run()
    assert controller.state == StateValues.ENABLED


@patch('main.requests.post')
@patch('main.report_attempt')
def test_lifecycle_scan_while_firing(requests_post,
                                     mock_report_attempt,
                                     MockControllerLifecycle,
                                     authorized_rfids):
    ''' Test that an ID scanned while the laser is firing is ignored '''
    controller = MockControllerLifecycle
    test_id = authorized_rfids[0]

    # Test script
    # scanned
    # read rfid
    # odometer increase (firing)
    # odometer increase (firing) with id scan

    serial_reads = ['o1000x0',
                    'o1000x1',
                    'r'+test_id,
                    'o1100x0',
                    'o1200x1',
                    'o1300x0',
                    'o1400x0',
                    'r'+test_id,
                    ]

    controller.resource.read.side_effect = serial_reads

    controller.run()
    assert controller.state == StateValues.INIT

    controller.run()
    assert controller.state == StateValues.ENABLED
    assert controller.manager.authorized_rfid == test_id

    controller.run()
    assert controller.state == StateValues.FIRING
    assert controller.manager.authorized_rfid == test_id

    controller.run()
    assert controller.state == StateValues.FIRING
    assert controller.manager.authorized_rfid == test_id

    controller.run()
    assert controller.state == StateValues.FIRING
    assert controller.manager.authorized_rfid == test_id

    controller.run()
    assert controller.manager.authorized_rfid == test_id


@patch('main.requests.post')
@patch('main.report_attempt')
def test_lifecycle_cut_timer(requests_post,
                             mock_report_attempt,
                             MockControllerLifecycle,
                             authorized_rfids):
    controller = MockControllerLifecycle
    test_id = authorized_rfids[0]

    serial_reads = ['o1000x0',
                    'o1000x1',
                    'r'+test_id]

    controller.resource.read.side_effect = serial_reads

    controller.run()
    assert controller.state == StateValues.INIT

    controller.run()
    assert controller.state == StateValues.ENABLED

    serial_reads = ['o1100x0',
                    'o1100x0',
                    'o1400x0',
                    'o1400x0',
                    'o1400x0',
                    'o1400x0',
                    'o1400x0',
                    'o1900x0',
                    'o1900x0',
                    'o1900x0',
                    'o1900x0',
                    'o2400x0',
                    'o2400x0',
                    'o2400x0',
                    'o2400x0']

    controller.resource.read.side_effect = serial_reads

    for step in serial_reads:
        controller.run()

    assert controller.state == StateValues.ENABLED
    assert controller.resource.odometer == '2400'

    controller.resource.read.side_effect = ['o2400x1', 'r'+test_id]
    controller.run()

    assert controller.state == StateValues.INIT
    assert controller.firing_start == '1000'