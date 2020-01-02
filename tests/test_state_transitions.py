from unittest.mock import patch, Mock
from main import StateValues


@patch('main.report_attempt')
def test_blah(mock_report_attempt, Blah, authorized_rfids):
    controller = Blah
    assert len(controller.manager.whitelist) == 2

    assert not controller.manager.authorized
    assert not controller.manager.authorized_rfid
    assert not controller.resource.enabled
    assert controller.state == StateValues.INIT

    test_id = authorized_rfids[0]
    serial_reads = ['o1000x1', 'r'+test_id]
    controller.resource.read.side_effect = serial_reads

    controller.run()
    assert controller.manager.authorized
    assert controller.manager.authorized_rfid == test_id
    assert controller.resource.enabled
    assert controller.state == StateValues.ENABLED
