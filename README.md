# PyLibre

A Python client for interacting with the Libre blockchain.

## Project Structure

```
pylibre/
├── config/ # Configuration files
│ └── config.yaml # Main configuration
├── src/
│ └── pylibre/
│ ├── cli.py # LibreClient command line interface
│ ├── client.py # LibreClient core functionality
│ ├── dex.py # DEX interaction methods
│ ├── manager/ # System management
│ │ ├── config_manager.py
│ │ └── trading_manager.py
│ ├── utils/ # Utility functions
│ │ ├── binance_api.py
│ │ └── shared_data.py
│ └── strategies/ # Trading strategies
│ ├── templates/
│ └── random_walk.py
│ └── orderbook_maker.py
│ └── market_rate.py
├── examples/ # Examples
├── scripts/ # CLI tools
└── tests/ # Unit tests
```

## Installation 

Once on PyPi (coming soon), install with:
```bash
pip install pylibre
``

Or clone the repo and run:
```bash
pip install -e .
```

## Configuration

### Main Configuration

Create a `config/config.yaml` file based on the `config/example.config.yaml` file.

Fill in the values for the networks, accounts, and strategies.

You may also need to add credentials for external services:
- Checking IP address location to ensure non-US trading compliance (IPInfo)
- Accessing Binance API for price comparisons and market data (Binance)

### CLI Usage

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

Always specify the environment file when using the CLI:
```bash
# Basic format
pylibre --api-url https://testnet.libre.org <command> [options]

# Example transfer
pylibre --api-url https://testnet.libre.org transfer dextester bentester "0.00001000 BTC" "memo"

# Example table query
pylibre --api-url https://testnet.libre.org table farm.libre account BTCUSD
```

Run a strategy group
```bash
python scripts/run_trading.py btc_market_making --config config/config.yaml
```

Run a specific strategy
```bash
python scripts/run_strategy.py --account myaccount --strategy OrderBookFillerStrategy --base BTC --quote USDT
```

Cancel all orders for an account
```bash 
python scripts/cancel_all_orders.py --account myaccount --pair BTC/USDT
```

Run a strategy with a specific account
```bash
python scripts/run_strategy.py --account myaccount --strategy OrderBookFillerStrategy --base BTC --quote USDT
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

Available strategies:
- `OrderBookFillerStrategy`: Market making strategy with configurable spread
- `MarketRateStrategy`: Price tracking strategy based on external markets

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