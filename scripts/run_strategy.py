from pylibre import LibreClient
from pylibre.manager.account_manager import AccountManager
from pylibre.strategies.random_walk import RandomWalkStrategy
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
    
    # Add required configuration
    trading_config.update({
        'current_price': Decimal(args.price),
        'min_change_percentage': Decimal('0.01'),   # 1%
        'max_change_percentage': Decimal('0.20'),   # 20%
        'spread_percentage': Decimal('0.02'),       # 2%
        'quantity': '100.00000000',                # Amount per order
        'interval': 5                              # Seconds between iterations
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
    base_amount = Decimal(base_balance.split()[0])
    quote_amount = Decimal(quote_balance.split()[0])
    
    print(f"💰 Account balances:")
    print(f"   {base_amount} {args.base}")
    print(f"   {quote_amount} {args.quote}")

    # Calculate maximum possible trade quantity based on balances
    price = Decimal(args.price)
    max_base_trade = base_amount.quantize(Decimal('0.00000001'), rounding=ROUND_DOWN)
    max_quote_trade = (quote_amount / price).quantize(Decimal('0.00000001'), rounding=ROUND_DOWN)
    
    # Use the smaller of the requested quantity or maximum possible trade
    requested_quantity = Decimal(trading_config['quantity'])
    safe_quantity = min(requested_quantity, max_base_trade, max_quote_trade)
    
    if safe_quantity < requested_quantity:
        print(f"⚠️  Reducing trade quantity from {requested_quantity} to {safe_quantity} due to balance constraints")
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
    else:
        print(f"❌ Unknown strategy: {args.strategy}")

if __name__ == "__main__":
    main() 