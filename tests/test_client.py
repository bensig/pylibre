import pytest
from unittest.mock import Mock, patch, MagicMock
from pylibre.client import LibreClient
import json
import requests

@pytest.fixture
def mock_net():
    with patch('pylibre.client.Net') as mock:
        mock_instance = Mock()
        mock.return_value = mock_instance
        yield mock

@pytest.fixture
def mock_types():
    with patch('pylibre.client.types') as mock:
        # Create concrete implementations for abstract types
        mock.Name = Mock()
        mock.Asset = Mock()
        mock.String = Mock()
        mock.Int64 = Mock()
        mock.Float64 = Mock()
        mock.Bool = Mock()
        mock.Object = Mock()
        mock.Array = Mock()
        
        # Make sure the types can be instantiated
        for type_mock in [mock.Name, mock.Asset, mock.String, mock.Int64, 
                         mock.Float64, mock.Bool, mock.Object, mock.Array]:
            type_mock.return_value = Mock(__bytes__=Mock(), from_bytes=Mock())
        
        yield mock

@pytest.fixture
def mock_action():
    with patch('pylibre.client.Action') as mock:
        mock_instance = Mock()
        mock.return_value = mock_instance
        yield mock

@pytest.fixture
def mock_data():
    with patch('pylibre.client.Data') as mock:
        mock_instance = Mock()
        mock.return_value = mock_instance
        yield mock

@pytest.fixture
def mock_auth():
    with patch('pylibre.client.Authorization') as mock:
        mock_instance = Mock()
        mock.return_value = mock_instance
        yield mock

@pytest.fixture
def mock_transaction():
    with patch('pylibre.client.Transaction') as mock:
        # Create a chain of mock objects for the transaction flow
        mock_send = Mock(return_value={"transaction_id": "test_tx_id"})
        mock_signed = Mock(send=mock_send)
        mock_linked = Mock(sign=Mock(return_value=mock_signed))
        mock_instance = Mock(link=Mock(return_value=mock_linked))
        mock.return_value = mock_instance
        yield mock

@pytest.fixture
def client(mock_net, mock_types, mock_action, mock_data, mock_auth, mock_transaction):
    client = LibreClient(
        network='testnet',
        config_path='tests/fixtures/test_config.yaml'
    )
    return client

def test_execute_action_success(client):
    result = client.execute_action(
        contract="test.contract",
        action_name="test",
        actor="testactor",
        data={"param": "value"}
    )

    assert result["success"] is True
    assert result["data"]["transaction_id"] == "test_tx_id"

def test_execute_action_failure(client):
    client.private_keys = {}  # Clear private keys
    
    result = client.execute_action(
        contract="test.contract",
        action_name="test",
        actor="testactor",
        data={"param": "value"}
    )

    assert result["success"] is False
    assert "No private key found for account testactor" in result["error"]

def test_transfer_success(client):
    result = client.transfer(
        from_account="testsender",
        to_account="testreceiver",
        quantity="1.00000000 USDT",
        memo="test",
        contract="usdt.libre"
    )

    assert result["success"] is True
    assert result["data"]["transaction_id"] == "test_tx_id"

@patch('requests.post')
def test_get_currency_balance_success(mock_post):
    client = LibreClient("https://testnet.libre.org")
    mock_response = Mock()
    mock_response.json.return_value = ["1.00000000 USDT"]
    mock_response.status_code = 200
    mock_post.return_value = mock_response

    result = client.get_currency_balance(
        contract="usdt.libre",
        account="testaccount",
        symbol="USDT"
    )

    assert result == "1.00000000 USDT"

@patch('requests.post')
def test_get_currency_balance_empty(mock_post):
    client = LibreClient("https://testnet.libre.org")
    mock_response = Mock()
    mock_response.json.return_value = []
    mock_response.status_code = 200
    mock_post.return_value = mock_response

    result = client.get_currency_balance(
        contract="usdt.libre",
        account="testaccount",
        symbol="USDT"
    )

    assert result == "0.00000000 USDT"

@patch('requests.post')
def test_get_table_rows_success(mock_post):
    # Mock the response from the API
    mock_response = Mock()
    mock_response.json.return_value = {
        'rows': [{'id': 1, 'data': 'test'}]
    }
    mock_response.status_code = 200
    mock_post.return_value = mock_response

    client = LibreClient()
    result = client.get_table_rows(
        code="test.contract",
        table="test.table",
        scope="test.scope"
    )

    # Check the full response structure
    assert isinstance(result, dict)
    assert 'success' in result
    assert 'rows' in result
    assert result['success'] is True
    assert len(result['rows']) == 1
    assert result['rows'][0]['id'] == 1
    assert result['rows'][0]['data'] == 'test'

@patch('requests.post')
def test_get_table_pagination(mock_post):
    client = LibreClient("https://testnet.libre.org")
    
    # Mock multiple responses for pagination
    mock_post.side_effect = [
        Mock(
            status_code=200,
            json=lambda: {"rows": [{"id": 1}], "more": True, "next_key": "2"}
        ),
        Mock(
            status_code=200,
            json=lambda: {"rows": [{"id": 2}], "more": False}
        )
    ]

    result = client.get_table(
        code="test.contract",
        table="testtable",
        scope="testscope"
    )

    assert len(result) == 2
    assert result[0]["id"] == 1
    assert result[1]["id"] == 2