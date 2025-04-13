#!/usr/bin/env python
import os
import json
import argparse
from datetime import datetime
import sys

def force_price_update(base_symbol, quote_symbol, price):
    """Manually write a price update with timestamp to the price file."""
    # Create shared_data directory if it doesn't exist
    if not os.path.exists("shared_data"):
        os.makedirs("shared_data")
    
    # Construct the price file path
    price_file_path = "shared_data/{0}{1}_price.json".format(base_symbol.lower(), quote_symbol.lower())
    
    # Create the price data with current timestamp
    data = {
        "price": float(price),
        "last_updated": datetime.now().isoformat()
    }
    
    # Write the data to the file
    try:
        with open(price_file_path, 'w') as f:
            json.dump(data, f)
        print("✅ Successfully wrote price {0} for {1}/{2} to {3}".format(
            price, base_symbol, quote_symbol, price_file_path))
        print("⏰ Timestamp: {0}".format(data['last_updated']))
        return True
    except Exception as e:
        print("❌ Error writing price data: {0}".format(e))
        return False

def main():
    """Parse arguments and force a price update."""
    parser = argparse.ArgumentParser(description='Force update a price file with timestamp')
    parser.add_argument('--base', required=True, help='Base symbol (e.g., BTC)')
    parser.add_argument('--quote', required=True, help='Quote symbol (e.g., USDT)')
    parser.add_argument('--price', required=True, type=float, help='Price value to set')
    
    args = parser.parse_args()
    
    # Normalize symbols
    base_symbol = args.base.upper()
    quote_symbol = args.quote.upper()
    
    # Force the price update
    success = force_price_update(base_symbol, quote_symbol, args.price)
    
    # Exit with appropriate status
    sys.exit(0 if success else 1)
    
if __name__ == "__main__":
    main() 