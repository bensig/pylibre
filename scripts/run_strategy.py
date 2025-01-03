from pylibre import LibreClient
from pylibre.manager.account_manager import AccountManager
from pylibre.strategies.random_walk import RandomWalkStrategy
from pylibre.strategies.market_rate import MarketRateStrategy
from pylibre.strategies.order_book_maker import OrderBookMakerStrategy
from decimal import Decimal, ROUND_DOWN
import argparse
import sys

def get_strategy_class(strategy_name: str):
    """Get the strategy class based on the strategy name."""
    strategies = {
        'RandomWalkStrategy': RandomWalkStrategy,
        'MarketRateStrategy': MarketRateStrategy,
        'OrderBookMakerStrategy': OrderBookMakerStrategy
    }
    return strategies.get(strategy_name)

def main():
    parser = argparse.ArgumentParser(description='Run a trading strategy')
    parser.add_argument('--account', required=True, help='Trading account name')
    parser.add_argument('--strategy', required=True, help='Strategy name')
    parser.add_argument('--base', default='LIBRE', help='Base asset symbol')
    parser.add_argument('--quote', default='BTC', help='Quote asset symbol')
    parser.add_argument('--price', default='0.0000000100', help='Initial price')
    args = parser.parse_args()

    # Initialize client (will use default endpoint based on env file)
    client = LibreClient(verbose=True)

    # Check if we have the key loaded
    if args.account.lower() not in client.private_keys:
        print(f"❌ No private key found for account: {args.account}")
        print(f"Make sure ACCOUNT_{args.account.upper()}=<private_key> exists in .env.testnet")
        return

    # Default trading configuration
    trading_config = {
        'current_price': Decimal(args.price),
        'min_change_percentage': Decimal('0.01'),   # 1%
        'max_change_percentage': Decimal('0.20'),   # 20%
        'spread_percentage': Decimal('0.02'),       # 2%
        'quantity': '100.00000000',                # Amount per order
        'interval': 5,                              # Seconds between iterations
        'num_orders': 20,                         # Default to 20 orders
        'quantity_distribution': 'equal',        # Default distribution method
        'order_spacing': 'linear'               # Default spacing method
    }

    # Check account balances with explicit contracts
    base_contract = {
        'BTC': 'btc.libre',
        'USDT': 'usdt.libre',
        'LIBRE': 'eosio.token'
    }.get(args.base.upper())
    
    quote_contract = {
        'BTC': 'btc.libre',
        'USDT': 'usdt.libre',
        'LIBRE': 'eosio.token'
    }.get(args.quote.upper())
    
    base_balance = client.get_currency_balance(args.account, args.base, contract=base_contract)
    quote_balance = client.get_currency_balance(args.account, args.quote, contract=quote_contract)
    
    print(f"\n💰 Account Balances:")
    print(f"{args.base}: {base_balance}")
    print(f"{args.quote}: {quote_balance}")

    # Initialize strategy
    strategy_class = get_strategy_class(args.strategy)
    if not strategy_class:
        print(f"❌ Strategy not found: {args.strategy}")
        return

    # Initialize strategy with correct contract names
    strategy = strategy_class(
        client=client,
        account=args.account,
        base_symbol=args.base,
        quote_symbol=args.quote,
        config=trading_config
    )

    try:
        strategy.run()
    except KeyboardInterrupt:
        print("\n⚠️ Strategy interrupted by user")
        print("Cleaning up...")
        strategy.cleanup()
        print("Done!")

if __name__ == "__main__":
    main() 