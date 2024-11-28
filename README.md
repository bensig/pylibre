# PyLibre

A Python client for interacting with the Libre blockchain.

## Installation 

From PyPI (not yet available):
```bash
pip install pylibre
```

For local development:
```bash
git clone https://github.com/bensig/pylibre.git
cd pylibre
pip install -e .
```

## Prerequisites

- cleos
- keosd
- a wallet for the account you want to use **
- a .env.testnet file in the root of the project with the following variables:
```
API_URL=https://testnet.libre.org
```

** If you are going to be using authorization keys, you must have keosd running locally with keys in a wallet loaded - the password for the wallet must be in a file called account_wallet.pwd in the root of the project for any accounts you use.

Create a wallet for the account you want to use - example my libre account is "bentester":

```bash
cleos create wallet -n bentester -f bentester_wallet.pwd
```

# Usage 

It does a few simple things - pretty easy to use - downloading an entire table, doing a transfer, or getting specific row data from a table using a filter "upper/lower bound"… 

###Transfer example: 
```
client.transfer("usdt.libre", "bentester", "bentest3", "0.00100000 USDT", "Test")
```

### Download an entire table: 
```
client.get_table(
    code="stake.libre",
    table="stake",
    scope="stake.libre"
)
```

### Or just get a single row using the cli and filtering for an account:
```
pylibre --env-file .env.mainnet --contract farm.libre --action get_table \  --actor bentester --data '{"table":"account","scope":"BTCUSD","limit":1,"lower_bound":"cesarcv","upper_bound":"cesarcv","index_position":"primary","key_type":"name"}' | jq .
```

It still uses cleos for packing, signing, and broadcasting - but it's faster than EOSJS still by about 30-40% based on my testing. 


## More Python Examples

Check out or run [examples.py](examples/examples.py) - of course you must change bentester to the account you have a key for...

## More CLI Examples 

### Get Balance
```bash
pylibre --contract btc.libre --action get_balance --actor bentester --symbol BTC --get-balance
```

### Transfer with unlock - requires a wallet password file for sender - ex: "bentester_wallet.pwd"
```bash
pylibre --contract usdt.libre --action transfer --actor bentester --unlock --data '{"from":"bentester","to":"bentest3","quantity":"0.00100000 USDT","memo":"Test"}'
```

### Run an action on a contract with data
```bash
pylibre --contract reward.libre --action updateall --data '{"max_steps":"500"}' --actor bentester
```

## License

MIT License