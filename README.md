# PyLibre

A Python client for interacting with the Libre blockchain.

## Installation 

```bash
pip install pylibre
```

## Usage

### Global Options
- `--api-url`: API endpoint URL (required)
  - Testnet: `https://testnet.libre.org`
  - Mainnet: `https://lb.libre.org`
- `--env-file`: Environment file path (default: .env.testnet)
- `--unlock`: Unlock wallet for transactions (requires password file)

### Query Table Data
```bash
# Get filtered rows from a table
pylibre --api-url https://testnet.libre.org table farm.libre account BTCUSD --lower-bound cesarcv --upper-bound cesarcv

# Get all rows from a table
pylibre --api-url https://testnet.libre.org table-all stake.libre stake stake.libre
```

### Get Token Balance
```bash
pylibre --api-url https://testnet.libre.org balance usdt.libre myaccount USDT
```

### Transfer Tokens
```bash
# Simple transfer (contract from_account to_account quantity memo)
pylibre --api-url https://testnet.libre.org transfer usdt.libre sender recipient "1.00000000 USDT" "memo"

# Transfer with wallet unlock
pylibre --api-url https://testnet.libre.org --unlock transfer usdt.libre sender recipient "1.00000000 USDT" "memo"
```

### Execute Contract Actions
```bash
pylibre --api-url https://testnet.libre.org execute reward.libre updateall myaccount '{"max_steps":"500"}'
```

## Environment Setup

Create a `.env.testnet` or `.env.mainnet` file:
```bash
# For testnet
API_URL=https://testnet.libre.org

# For mainnet
# API_URL=https://lb.libre.org
```

For transactions requiring authorization, create a wallet password file:
```bash
# Create wallet and save password
cleos wallet create -n myaccount -f myaccount_wallet.pwd
```

## Common Token Contracts
- USDT: usdt.libre (8 decimals)
- BTC: btc.libre (8 decimals)
- LIBRE: eosio.token (4 decimals)

## License

MIT License