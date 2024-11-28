# PyLibre

A Python client for interacting with the Libre blockchain.

## Installation 

```bash
pip install pylibre
```


## Usage
```python
from pylibre import LibreClient
Initialize client
client = LibreClient("https://api.libre.org")
Load account keys
client.load_account_keys(".env.testnet")
Get token balance
balance = client.get_currency_balance("contractname", "accountname", "SYMBOL")
print(balance)
```

```bash
pylibre --contract mycontract --action transfer --actor myaccount --data '{"to": "recipient", "quantity": "1.0000 SYMBOL", "memo": "Test transfer"}'
```

## License

MIT License