# PyLibre

A Python client for interacting with the Libre blockchain.

## Project Structure

```
pylibre/
├── accounts/                  # Account configurations
│   └── accounts.json         # Trading account settings
├── src/
│   └── pylibre/
│       ├── client.py         # LibreClient core functionality
│       ├── dex.py           # DEX interaction methods
│       ├── manager/         # Account management
│       │   └── account.py   # AccountManager class
│       └── strategies/      # Trading strategies
│           ├── templates/   # Base strategy templates
│           └── random_walk.py
├── examples/                # Example scripts
├── scripts/                # CLI tools
└── tests/                  # Unit tests
```

## Installation 

```bash
pip install pylibre
```

## Configuration

### Account Setup

Create an `accounts/accounts.json` file to configure trading accounts:

```json
{
    "myaccount": {
        "wallet_name": "myaccount",
        "wallet_password_file": "myaccount_wallet.pwd",
        "allowed_strategies": [
            "RandomWalkStrategy"
        ],
        "allowed_pairs": [
            "LIBRE/BTC",
            "LIBRE/USDT"
        ],
        "default_settings": {
            "interval": 5,
            "quantity": "100.00000000",
            "min_change_percentage": 0.01,
            "max_change_percentage": 0.20,
            "spread_percentage": 0.02
        },
        "strategy_settings": {
            "RandomWalkStrategy": {
                "interval": 5,
                "quantity": "100.00000000"
            }
        }
    }
}
```

### Environment Setup

Create a `.env.testnet` or `.env.mainnet` file:
```bash
# For testnet
API_URL=https://testnet.libre.org

# For mainnet
# API_URL=https://lb.libre.org
```

### Wallet Setup
For transactions requiring authorization, create a wallet password file:
```bash
# Create wallet and save password
cleos wallet create -n myaccount -f myaccount_wallet.pwd
```

## Usage

### Python Client

```python
from pylibre import LibreClient

# Initialize client
client = LibreClient("https://testnet.libre.org")

# Get balance
balance = client.get_currency_balance("usdt.libre", "myaccount", "USDT")
```

### Trading Strategies

Run a trading strategy:
```bash
python scripts/run_strategy.py --account myaccount --strategy RandomWalkStrategy --base BTC --quote LIBRE
```

Or use the example scripts:
```bash
python examples/run_random_walk.py
```

### CLI Commands

Query table data:
```bash
# Get filtered rows from a table
pylibre --api-url https://lb.libre.org table farm.libre account BTCUSD --lower-bound myaccount

# Get all rows from a table
pylibre --api-url https://testnet.libre.org table-all stake.libre stake stake.libre
```

Transfer tokens:
```bash
# Simple transfer
pylibre --api-url https://testnet.libre.org transfer myaccount recipient "1.00000000 USDT" "memo"

# Transfer with wallet unlock
pylibre --api-url https://testnet.libre.org --unlock transfer usdt.libre myaccount recipient "1.00000000 USDT" "memo"
```

Execute contract actions:
```bash
pylibre --api-url https://testnet.libre.org execute reward.libre updateall myaccount '{"max_steps":"500"}'
```

## Development

### Running Tests
```bash
pytest tests/
```

### Adding New Strategies

1. Create a new strategy class in `src/pylibre/strategies/`
2. Inherit from `BaseStrategy`
3. Implement `generate_signal()` and any other required methods
4. Add strategy configuration to `accounts.json`

## Common Token Contracts
- USDT: usdt.libre (8 decimals)
- BTC: btc.libre (8 decimals)
- LIBRE: eosio.token (4 decimals)

## License

MIT License