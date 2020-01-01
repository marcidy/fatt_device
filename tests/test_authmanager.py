from unittest.mock import patch
from main import AuthManager


@patch('main.load_whitelist', return_value=['asdf'])
def test_authmanager_init(mock_whitelist):

    test_whitelist = ['test1234', 'test0987']
    mock_whitelist.configure_mock(**{'return_value': test_whitelist})
    manager = AuthManager()
    assert manager.authorized_rfid is None
    assert not manager.authorized
    assert mock_whitelist.called
    assert manager.whitelist == test_whitelist


@patch('main.report_attempt')
@patch('main.load_whitelist')
def test_authmanager_check_rfid(mock_whitelist, mock_report):
    manager = AuthManager()
    test_id = 'test1234'

    # Successful attempt
    manager.whitelist = [test_id]
    assert manager.check_rfid(test_id)
    assert mock_report.called_with(test_id, True)

    # Unsuccessful attemped
    manager.whitelist = []
    assert not manager.check_rfid(test_id)
    assert mock_report.called_with(test_id, False)


@patch('main.report_attempt')
@patch('main.load_whitelist')
def test_authmanager_login(mock_whitelist, mock_report):
    manager = AuthManager()
    successful_id = 'test1234'
    unsuccessful_id = 'test0987'
    manager.whitelist = [successful_id]

    manager.login(successful_id)
    assert manager.authorized is True
    assert manager.authorized_rfid == successful_id

    manager.logout()
    assert manager.authorized is False
    assert manager.authorized_rfid is None

    manager.login(unsuccessful_id)
    assert manager.authorized is False
    assert manager.authorized_rfid is None
