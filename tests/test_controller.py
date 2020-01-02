import time
from unittest.mock import Mock
from main import StateValues


def test_controler_init(MockController):
    controller = MockController
    assert controller
    assert controller.state == StateValues.INIT
    assert not controller.manager.authorized
    assert not controller.activity_timer.running
    print(controller.internal_states)


def test_scan_no_new_card(MockController):
    controller = MockController

    # Scan from INIT state, no new scan
    assert controller.state == StateValues.INIT
    controller.scan()
    assert controller.resource.rfid_flag == '0'
    assert controller.manager.authorized_rfid is None
    assert not controller.manager.authorized


def test_scan_new_card(MockController):
    controller = MockController
    # Indicate new scan, no previous login
    controller.resource.rfid_flag = '1'
    controller.resource.rfid.return_value = '01234567'

    controller.scan()
    assert controller.resource.rfid.called
    assert controller.resource.rfid_flag == '0'
    assert not controller.manager.logout.called
    assert controller.manager.login.called


def test_scan_logout(MockController):
    controller = MockController

    # log a user in
    controller.manager.authorized = True
    controller.manager.authorized_rfid = '01234567'

    # set up new scan
    controller.resource.rfid_flag = '1'
    controller.resource.rfid.return_value = '01234567'

    controller.scan()
    assert controller.manager.logout.called
    assert not controller.manager.login.called


def test_scan_switch(MockController):
    controller = MockController

    # log a user in
    controller.manager.authorized = True
    controller.manager.authorized_rfid = '01234567'

    # set up new scan with different id
    controller.resource.rfid_flag = '1'
    controller.resource.rfid.return_value = 'ABCDEFGH'

    controller.scan()
    assert controller.manager.logout.called
    assert controller.manager.login.called


def test_emit_state(MockController):
    controller = MockController

    new_state = controller.emit_state()
    assert new_state['odometer'] == 100
    assert new_state['enabled'] is False
    assert new_state['authorized'] is False
    assert new_state['scanned'] is False

    # Trigger a new scan and check that state is updated
    controller.resource.rfid_flag = '1'
    new_state = controller.emit_state()
    assert new_state['odometer'] == 100
    assert new_state['enabled'] is False
    assert new_state['authorized'] is False
    assert new_state['scanned'] is True


def test_calculate_state(MockController):
    controller = MockController

    next_state = controller.calculate_state()
    assert controller.state == StateValues.INIT
    assert next_state == StateValues.INIT


def test_bad_firing_state(MockController):
    controller = MockController

    # This is a critical test, so explicitly confirming good test conditions
    assert not controller.manager.authorized
    assert not controller.resource.enabled

    # Create laser firing condition
    controller.resource.odometer += 10

    next_state = controller.calculate_state()
    assert next_state == StateValues.INIT


def test_laser_firing_state(MockController):
    controller = MockController

    # Test conditions:
    #   manger is authorized
    #   resource is enabled
    #   laser is firing
    controller.manager.authorized = True
    controller.resource.enabled = True
    controller.resource.odometer += 10

    next_state = controller.calculate_state()
    assert next_state == StateValues.FIRING


def test_enable_state(MockController):
    controller = MockController

    controller.manager.authorized = True

    next_state = controller.calculate_state()
    assert next_state == StateValues.ENABLED


def test_run(MockController):
    controller = MockController
    controller.calculate_state = Mock(return_value=StateValues.INIT)

    controller.run()
    assert controller.resource.disable.called
    assert controller.manager.logout.called


def test_run_init_to_enabled(MockControllerState):
    controller = MockControllerState

    # assert good test condition
    assert controller.state == StateValues.INIT

    controller.calculate_state.return_value = StateValues.ENABLED
    controller.run()
    assert controller.resource.enable.called
    assert controller.activity_timer.running


def test_run_enabled_to_activity_timeout(MockController):
    controller = MockController

    # use a 1s timeout for test
    timeout = 1
    controller.activity_timer.seconds = timeout

    # put controller into enabled state when run
    controller.resource.enabled = True
    controller.manager.authorized = True

    controller.run()
    assert controller.state == StateValues.ENABLED
    assert controller.activity_timer.running
    time.sleep(timeout + 1)
    assert not controller.activity_timer.check()
    controller.run()
    assert controller.state == StateValues.INIT
    assert controller.resource.disable.called
    assert controller.manager.logout.called


def test_run_start_firing_time(MockController):
    controller = MockController

    controller.resource.enabled = True
    controller.resource.odometer += 10
    controller.resource.cost.return_value = 123.45
    controller.manager.authorized = True
    controller.run()

    assert controller.firing_start > 0
    assert time.time() - controller.firing_start > 0

    time.sleep(2)
    # odometer from laser is the same, so it will not update
    controller.run()
    assert controller.state == StateValues.ENABLED


def test_firing_steady_state(MockController):
    controller = MockController
    controller.resource.enabled = True
    controller.resource.odometer += 10
    controller.manager.authorized = True
    controller.state = StateValues.FIRING

    controller.run()
    assert controller.state == StateValues.FIRING


def test_display(MockController):
    controller = MockController

    firing_time = 1
    firing_cost = 0.01
    controller.resource.cost.return_value = firing_cost
    expected_line1 = "Time: {}".format(firing_time)
    expected_line2 = "Cost: {}".format(firing_cost)

    controller.display(1)
    assert controller.resource.display.called_with(expected_line1,
                                                   expected_line2)

    for m in range(100):
        for s in range(60):
            test_time = m*60 + s
            expected_line1 = "Time: {}:{}".format(m, s)
            controller.display(test_time)
            assert controller.resource.display.called_with(expected_line1)

    for c in range(0, 100000):
        dollars = c // 100
        cents = round(c/100 % 1, 2)
        expected_line2 = "{}.{}".format(dollars, cents)
        controller.resource.cost.return_value = c
        assert controller.resource.display.called_with(expected_line2)
