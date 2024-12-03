from pylibre import LibreClient
from pylibre.strategies.random_walk import RandomWalkStrategy
from decimal import Decimal

def main():
    # Initialize client
    client = LibreClient("https://testnet.libre.org")
    
    # Unlock wallet first
    wallet_result = client.unlock_wallet("bentester", "bentester_wallet.pwd")
    if not wallet_result["success"]:
        print(f"❌ Failed to unlock wallet: {wallet_result.get('error')}")
        return
    
    print("🔓 Wallet unlocked successfully")
    
    # Strategy configuration
    config = {
        'current_price': Decimal('0.0000000100'),  # Starting price (100 SATS)
        'min_change_percentage': Decimal('0.01'),   # 1%
        'max_change_percentage': Decimal('0.20'),   # 20%
        'spread_percentage': Decimal('0.02'),       # 2%
        'quantity': '100.00000000',                # Amount per order
        'interval': 2                              # Seconds between iterations
    }
    
    # Initialize strategy
    strategy = RandomWalkStrategy(
        client=client,
        account="bentester",
        quote_symbol="BTC",
        base_symbol="LIBRE",
        config=config
    )
    
    # Run the strategy
    strategy.run()

if __name__ == "__main__":
    main() 