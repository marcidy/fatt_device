import pytest
from unittest.mock import Mock, MagicMock, patch
import tempfile
from main import Laser


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
