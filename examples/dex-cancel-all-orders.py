from pylibre import LibreClient
from pylibre.dex import DexClient
import argparse

def main():
    # Create argument parser
    parser = argparse.ArgumentParser(description='Cancel all DEX orders for a trading pair')
    parser.add_argument('account', help='Account name')
    parser.add_argument('base_symbol', help='Base token symbol (e.g., BTC)')
    parser.add_argument('quote_symbol', help='Quote token symbol (e.g., USDT)')
    parser.add_argument('--api-url', default='https://testnet.libre.org', help='API URL')
    args = parser.parse_args()

    # Initialize clients
    client = LibreClient(args.api_url)
    dex = DexClient(client)

    # Unlock wallet
    print("\n🔐 Unlocking wallet...")
    unlock_result = client.unlock_wallet(args.account, f"{args.account}_wallet.pwd")
    if not unlock_result["success"]:
        print(f"❌ Failed to unlock wallet: {unlock_result.get('error')}")
        return
    print("✅ Wallet unlocked successfully")

    # Cancel all orders for the specified pair
    result = dex.cancel_all_orders(args.account, args.quote_symbol, args.base_symbol)
    print(result)

if __name__ == "__main__":
    main()