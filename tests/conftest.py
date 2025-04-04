import pytest
from importlib import reload
from unittest.mock import patch
from unittest.mock import MagicMock, Mock

@pytest.fixture
def mock_security():
    with patch('darwin_composer.DarwinComposer.darwin_security', return_value=None) as mock:
        yield mock

@pytest.fixture
def mock_logging():
    with patch('darwin_composer.DarwinComposer.darwin_logs', return_value=None) as mock:
        yield mock
        
@pytest.fixture
def reload_module(mock_logging, mock_security):
    """
    Reloads the 'src.app.main' module before each test case.
    
    Yields:
        None
    """
    import src.app.main
    reload(src.app.main)
    yield

@pytest.fixture
def mock_request():
    """
    Mocks the request.

    Returns:
        MagicMock: A mock object representing the request object.
    """

    mock = MagicMock()

    return mock

@pytest.fixture
def mock_app_logger():
    mock_logger = Mock()
    mock_logger.logger.info = "some value"