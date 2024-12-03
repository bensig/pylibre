from pylibre import LibreClient
from pylibre.manager.account_manager import AccountManager
from pylibre.strategies.random_walk import RandomWalkStrategy
from decimal import Decimal
import argparse

def main():
    parser = argparse.ArgumentParser(description='Run a trading strategy')
    parser.add_argument('--account', required=True, help='Trading account name')
    parser.add_argument('--strategy', required=True, help='Strategy name')
    parser.add_argument('--base', default='BTC', help='Base asset symbol')
    parser.add_argument('--quote', default='LIBRE', help='Quote asset symbol')
    parser.add_argument('--price', default='0.0000000100', help='Initial price')
    args = parser.parse_args()

    # Initialize account manager
    account_manager = AccountManager()

    # Validate account configuration
    if not account_manager.validate_account(
        args.account, args.strategy, args.base, args.quote
    ):
        return

    # Get account configuration
    account_config = account_manager.get_account_config(args.account)
    trading_config = account_manager.get_trading_config(args.account, args.strategy)
    
    # Add required configuration
    trading_config.update({
        'current_price': Decimal(args.price),  # Add initial price
        'min_change_percentage': Decimal('0.01'),   # 1%
        'max_change_percentage': Decimal('0.20'),   # 20%
        'spread_percentage': Decimal('0.02'),       # 2%
        'quantity': '100.00000000',                 # Amount per order
        'interval': 5                               # Seconds between iterations
    })

    # Initialize client and unlock wallet
    client = LibreClient("https://testnet.libre.org")
    wallet_result = client.unlock_wallet(
        account_config['wallet_name'],
        account_config['wallet_password_file']
    )
    
    if not wallet_result["success"]:
        print(f"❌ Failed to unlock wallet: {wallet_result.get('error')}")
        return

    print("🔓 Wallet unlocked successfully")

    # Initialize and run strategy
    if args.strategy == "RandomWalkStrategy":
        strategy = RandomWalkStrategy(
            client=client,
            account=args.account,
            base_symbol=args.base,
            quote_symbol=args.quote,
            config=trading_config
        )
        strategy.run()
    else:
        print(f"❌ Unknown strategy: {args.strategy}")

if __name__ == "__main__":
    main() 