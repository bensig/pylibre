import pytest
import json
from unittest.mock import patch, mock_open, MagicMock
from pylibre.client import LibreClient
import subprocess

@pytest.fixture
def client():
    return LibreClient("https://testnet.libre.org")

# Test get_currency_balance
def test_get_currency_balance_success(client):
    mock_response = MagicMock()
    mock_response.json.return_value = ["1.00000000 USDT"]
    mock_response.raise_for_status.return_value = None
    
    with patch('requests.post', return_value=mock_response):
        balance = client.get_currency_balance("usdt.libre", "testaccount", "USDT")
        assert balance == "1.00000000 USDT"

def test_get_currency_balance_empty(client):
    mock_response = MagicMock()
    mock_response.json.return_value = []
    mock_response.raise_for_status.return_value = None
    
    with patch('requests.post', return_value=mock_response):
        balance = client.get_currency_balance("usdt.libre", "testaccount", "USDT")
        assert balance == "0.00000000 USDT"

# Test get_table_rows
def test_get_table_rows_success(client):
    expected_rows = [{"id": 1, "data": "test"}]
    mock_response = MagicMock()
    mock_response.json.return_value = {"rows": expected_rows}
    mock_response.raise_for_status.return_value = None
    
    with patch('requests.post', return_value=mock_response):
        rows = client.get_table_rows("test.contract", "testtable", "testscope")
        assert rows == expected_rows

def test_get_table_rows_with_params(client):
    with patch('requests.post') as mock_post:
        client.get_table_rows(
            "test.contract", 
            "testtable", 
            "testscope",
            limit=5,
            lower_bound="1",
            upper_bound="10",
            index_position="secondary",
            key_type="i64"
        )
        
        # Verify correct parameters were sent
        called_args = mock_post.call_args[1]['json']
        assert called_args['limit'] == 5
        assert called_args['lower_bound'] == "1"
        assert called_args['upper_bound'] == "10"
        assert called_args['index_position'] == "secondary"
        assert called_args['key_type'] == "i64"

# Test get_table (pagination)
def test_get_table_pagination(client):
    # Mock two pagination responses
    mock_responses = [
        MagicMock(json=lambda: {"rows": [{"id": 1}], "more": True, "next_key": "2"}),
        MagicMock(json=lambda: {"rows": [{"id": 2}], "more": False})
    ]
    
    with patch('requests.post', side_effect=mock_responses):
        rows = client.get_table("test.contract", "testtable", "testscope")
        assert len(rows) == 2
        assert rows[0]["id"] == 1
        assert rows[1]["id"] == 2

# Test execute_action
def test_execute_action_success(client):
    mock_process = MagicMock()
    mock_process.stdout = '{"transaction_id": "test123"}'
    mock_process.returncode = 0
    
    with patch('subprocess.run', return_value=mock_process):
        result = client.execute_action(
            "test.contract",
            "testaction",
            {"param": "value"},
            "testactor"
        )
        assert result["success"] is True
        assert result["data"]["transaction_id"] == "test123"

def test_execute_action_failure(client):
    # Create mock process with error message
    error_message = "Error message"
    mock_error = subprocess.CalledProcessError(1, [])
    mock_error.stdout = error_message
    
    with patch('subprocess.run', side_effect=mock_error):
        result = client.execute_action(
            "test.contract",
            "testaction",
            {"param": "value"},
            "testactor"
        )
        assert result["success"] is False
        assert result["error"] == error_message

# Test transfer
def test_transfer_success(client):
    # Mock successful execution
    mock_process = MagicMock()
    mock_process.stdout = '{"transaction_id": "test123"}'
    mock_process.returncode = 0
    
    with patch('subprocess.run', return_value=mock_process):
        result = client.transfer(
            from_account="sender",
            to_account="receiver",
            quantity="1.00000000 USDT"
        )
        assert result["success"] is True
        assert result["data"]["transaction_id"] == "test123"

def test_transfer_invalid_quantity(client):
    result = client.transfer(
        from_account="sender",
        to_account="receiver",
        quantity="invalid"
    )
    assert result["success"] is False
    assert "Invalid quantity format" in result["error"]

def test_transfer_unknown_token(client):
    result = client.transfer(
        from_account="sender",
        to_account="receiver",
        quantity="1.00000000 UNKNOWN"
    )
    assert result["success"] is False
    assert "No contract specified" in result["error"]

def test_transfer_libre_auto_contract(client):
    mock_process = MagicMock()
    mock_process.stdout = '{"transaction_id": "test123"}'
    mock_process.returncode = 0
    
    with patch('subprocess.run', return_value=mock_process) as mock_run:
        result = client.transfer(
            from_account="sender",
            to_account="receiver",
            quantity="100.0000 LIBRE"  # LIBRE uses 4 decimals
        )
        assert result["success"] is True
        assert result["data"]["transaction_id"] == "test123"
        # Verify it used eosio.token contract
        called_args = mock_run.call_args[0][0]  # Get the command args
        assert "eosio.token" in called_args

def test_transfer_btc_auto_contract(client):
    mock_process = MagicMock()
    mock_process.stdout = '{"transaction_id": "test123"}'
    mock_process.returncode = 0
    
    with patch('subprocess.run', return_value=mock_process) as mock_run:
        result = client.transfer(
            from_account="sender",
            to_account="receiver",
            quantity="0.00000001 BTC"  # BTC uses 8 decimals
        )
        assert result["success"] is True
        assert result["data"]["transaction_id"] == "test123"
        # Verify it used btc.libre contract
        called_args = mock_run.call_args[0][0]  # Get the command args
        assert "btc.libre" in called_args

# Test format_response helper
def test_format_response_success(client):
    response = client.format_response(True, data={"test": "value"})
    assert response["success"] is True
    assert response["data"]["test"] == "value"

def test_format_response_error(client):
    response = client.format_response(False, error="Test error")
    assert response["success"] is False
    assert response["error"] == "Test error"