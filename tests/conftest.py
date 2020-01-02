import pytest
from unittest.mock import Mock, MagicMock, patch
import tempfile
from main import Laser, Controller


AUTHORIZED_RFIDS = [
    'test1234',
    'test0987']


@pytest.fixture(scope='function')
@patch('main.Serial')
def MockLaser(serial):
    fake_usb = tempfile.NamedTemporaryFile()
    fake_usb.write = Mock()
    Laser.USB_PATH = fake_usb.name

    serial = Mock()
    serial.read_until = MagicMock(return_value=b'\n')
    serial.in_waiting = 0

    Laser.read = Mock()
    Laser.write = Mock()

    return Laser()


@pytest.fixture(scope='function')
@patch('main.Laser')
@patch('main.AuthManager')
def MockController(manager, laser):

    laser.odometer = 100
    laser.rfid_flag = '0'
    laser.enabled = False
    laser.cost = Mock(return_value=123.45)
    manager.authorized = False
    manager.authorized_rfid = None

    mock_controller = Controller(manager, laser)
    return mock_controller


@pytest.fixture(scope='function')
@patch('main.Laser')
@patch('main.AuthManager')
def MockControllerState(manager, laser):
    laser.odometer = 1000
    laser.rfid_flag = '0'
    laser.enabled = False
    manager.authorized = False
    manager.authorized_rfid = None

    mock_controller = Controller(manager, laser)
    mock_controller.calculate_state = Mock()

    return mock_controller
