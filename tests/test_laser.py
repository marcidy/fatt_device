import os
import pytest
from main import Laser, LASER_COST
from unittest.mock import patch, Mock, MagicMock
import tempfile


@patch('main.Serial')
@patch('main.Laser.USB_PATH')
def test_laser_init(serial, usb_path):
    fake_usb = tempfile.NamedTemporaryFile()
    fake_usb.write = Mock()
    usb_path = fake_usb.name
    serial = Mock()
    serial.read_until = MagicMock(return_value=b'\n')
    serial.in_waiting = 0

    Laser.read = Mock()
    Laser.write = Mock()
    Laser()

    assert fake_usb.write.called_with("0")
    assert fake_usb.write.called_with("1")


def test_laser_interface(MockLaser):
    laser = MockLaser

    laser.enable()
    assert laser.write.called_with("e")
    assert laser.enabled

    laser.disable()
    assert laser.write.called_with("d")
    assert not laser.enabled

    laser.read = Mock(return_value="test")
    laser.rfid()
    assert laser.write.called_with("r")

    laser.status()
    assert laser.write.called_with("o")

    laser.display("a")
    assert laser.write.called_with("pa")

    laser.display(line1="a")
    assert laser.write.called_with("pa")

    laser.display(None, "b")
    assert laser.write.called_with("qb")

    laser.display(line2="b")
    assert laser.write.called_with("qb")

    laser.display("a", "b")
    assert laser.write.called_with("paqb")

    laser.reset_cut_time()
    assert laser.write.called_with('x')

    laser.update_cut_time()
    assert laser.write.called_with('y')

    laser.read_cut_time()
    assert laser.write.called_with('z')


def test_laser_response(MockLaser):
    laser = MockLaser

    laser.read = Mock(return_value='o1337x0')
    laser.status()
    assert laser.odometer == '1337'
    assert laser.rfid_flag == '0'

    laser.read = Mock(return_value='o9999x1')
    laser.status()
    assert laser.odometer == '9999'
    assert laser.rfid_flag == '1'

    test_rfid = '12345678'
    laser.read = Mock(return_value='r'+test_rfid)

    data = laser.rfid()
    assert data == test_rfid

    laser.read = Mock(return_value='r00'+test_rfid)
    data = laser.rfid()
    assert data == test_rfid


def test_laser_cost(MockLaser):
    laser = MockLaser
    test_time = 100
    assert laser.cost(test_time) == test_time / 60 * LASER_COST
