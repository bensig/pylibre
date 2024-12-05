from pylibre import LibreClient
from pylibre.manager.account_manager import AccountManager
from pylibre.strategies.random_walk import RandomWalkStrategy
from pylibre.strategies.market_rate import MarketRateStrategy
from decimal import Decimal, ROUND_DOWN
import argparse
import sys

def main():
    parser = argparse.ArgumentParser(description='Run a trading strategy')
    parser.add_argument('--account', required=True, help='Trading account name')
    parser.add_argument('--strategy', required=True, help='Strategy name')
    parser.add_argument('--base', default='LIBRE', help='Base asset symbol')
    parser.add_argument('--quote', default='BTC', help='Quote asset symbol')
    parser.add_argument('--price', default='0.0000000100', help='Initial price')
    args = parser.parse_args()

    # Initialize account manager
    account_manager = AccountManager()

    # Validate account configuration
    if not account_manager.validate_account(
        args.account, 
        args.strategy, 
        args.quote, 
        args.base
    ):
        return

    # Get account configuration
    account_config = account_manager.get_account_config(args.account)
    trading_config = account_manager.get_trading_config(args.account, args.strategy)
    
    # Add required configuration with defaults
    default_config = {
        'current_price': Decimal(args.price),
        'min_change_percentage': Decimal('0.01'),   # 1%
        'max_change_percentage': Decimal('0.20'),   # 20%
        'spread_percentage': Decimal('0.02'),       # 2%
        'quantity': '100.00000000',                # Amount per order
        'interval': 5                              # Seconds between iterations
    }

    # Update with defaults only if not already in trading_config
    for key, value in default_config.items():
        if key not in trading_config:
            trading_config[key] = value
        else:
            # Convert numeric values to appropriate types
            if key in ['min_change_percentage', 'max_change_percentage', 'spread_percentage']:
                trading_config[key] = Decimal(str(trading_config[key]))
            elif key == 'quantity':
                trading_config[key] = str(trading_config[key])  # Ensure quantity is string
            elif key == 'interval':
                trading_config[key] = int(trading_config[key])  # Ensure interval is integer

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

    # Check account balances
    base_balance = client.get_currency_balance(None, args.account, args.base)
    quote_balance = client.get_currency_balance(None, args.account, args.quote)
    
    if isinstance(base_balance, dict) and not base_balance.get("success"):
        print(f"❌ Failed to fetch base balance: {base_balance.get('error')}")
        return
    if isinstance(quote_balance, dict) and not quote_balance.get("success"):
        print(f"❌ Failed to fetch quote balance: {quote_balance.get('error')}")
        return

    # Extract amounts from balance strings (format: "1.00000000 SYMBOL")
    base_amount = Decimal(base_balance.split()[0]).normalize()
    quote_amount = Decimal(quote_balance.split()[0]).normalize()
    
    print(f"💰 Account balances:")
    print(f"   {base_amount:.8f} {args.base}")
    print(f"   {quote_amount:.8f} {args.quote}")

    # Calculate maximum possible trade quantity based on balances
    price = Decimal(args.price).normalize()
    
    # For BTC/USDT pair, we need different precision and calculations
    if args.base == "BTC":
        max_base_trade = base_amount.quantize(Decimal('0.00000001'), rounding=ROUND_DOWN)
        max_quote_trade = (quote_amount / price).quantize(Decimal('0.00000001'), rounding=ROUND_DOWN)
        
        # Adjust default quantity for BTC
        if trading_config['quantity'] == '100.00000000':  # If it's still the default value
            trading_config['quantity'] = '0.00100000'     # Default to 0.001 BTC for BTC pairs
    else:
        max_base_trade = base_amount.quantize(Decimal('0.00000001'), rounding=ROUND_DOWN)
        max_quote_trade = (quote_amount / price).quantize(Decimal('0.00000001'), rounding=ROUND_DOWN)

    # Use the smaller of the requested quantity or maximum possible trade
    requested_quantity = Decimal(trading_config['quantity']).normalize()
    safe_quantity = min(requested_quantity, max_base_trade, max_quote_trade)
    
    if safe_quantity < requested_quantity:
        print(f"⚠️  Reducing trade quantity from {requested_quantity:.8f} to {safe_quantity:.8f} due to balance constraints")
        if safe_quantity == 0:
            print("❌ Insufficient balance to trade")
            return
    
    trading_config['quantity'] = str(safe_quantity)

    # Initialize and run strategy
    if args.strategy == "RandomWalkStrategy":
        strategy = RandomWalkStrategy(
            client=client,
            account=args.account,
            quote_symbol=args.quote,
            base_symbol=args.base,
            config=trading_config
        )
        strategy.run()
    elif args.strategy == "MarketRateStrategy":
        strategy = MarketRateStrategy(
            client=client,
            account=args.account,
            quote_symbol=args.quote,
            base_symbol=args.base,
            config=trading_config
        )
        strategy.run()
    else:
        print(f"❌ Unknown strategy: {args.strategy}")

if __name__ == "__main__":
    main() 