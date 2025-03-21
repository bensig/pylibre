#!/usr/bin/env python3
import os
import sys
import json
import argparse
from datetime import datetime
import time

def format_time_since(timestamp_str):
    """Format the time since the given timestamp in a human-readable format."""
    try:
        last_time = datetime.fromisoformat(timestamp_str)
        now = datetime.now()
        delta = now - last_time
        
        seconds = delta.total_seconds()
        if seconds < 60:
            return f"{int(seconds)}s ago"
        elif seconds < 3600:
            return f"{int(seconds/60)}m ago"
        elif seconds < 86400:
            return f"{int(seconds/3600)}h ago"
        else:
            return f"{int(seconds/86400)}d ago"
    except Exception:
        return timestamp_str

def display_price_data(base_symbol, quote_symbol):
    """Display the current price data for a trading pair."""
    # Construct the price file path (same logic as in MarketPriceTrackerStrategy)
    price_file_path = f"shared_data/{base_symbol.lower()}{quote_symbol.lower()}_price.json"
    
    # Check if file exists
    if not os.path.exists(price_file_path):
        print(f"❌ No price data found for {base_symbol}/{quote_symbol}")
        print(f"Expected file: {price_file_path}")
        return False
    
    try:
        # Read the price data - force reloading from disk with no caching
        with open(price_file_path, 'r') as f:
            data = json.load(f)
        
        # Extract data
        if isinstance(data, dict):
            price = data.get("price")
            last_updated = data.get("last_updated")
            
            # Format output
            print(f"📊 Current price for {base_symbol}/{quote_symbol}: {price}")
            
            if last_updated:
                time_since = format_time_since(last_updated)
                parsed_time = datetime.fromisoformat(last_updated)
                readable_time = parsed_time.strftime("%Y-%m-%d %H:%M:%S")
                print(f"⏰ Last updated: {readable_time} ({time_since})")
            else:
                print("⚠️ No timestamp information available")
            
            return True
        else:
            # Old format (just the price)
            print(f"📊 Current price for {base_symbol}/{quote_symbol}: {data}")
            print("⚠️ No timestamp information available (old format)")
            return True
            
    except Exception as e:
        print(f"❌ Error reading price data: {e}")
        return False

def main():
    """Main function to parse arguments and check price."""
    parser = argparse.ArgumentParser(description='Check the current price data')
    parser.add_argument('--base', required=True, help='Base symbol (e.g., BTC)')
    parser.add_argument('--quote', required=True, help='Quote symbol (e.g., USDT)')
    parser.add_argument('--watch', action='store_true', help='Watch for changes in real-time')
    parser.add_argument('--interval', type=int, default=5, help='Watch interval in seconds (default: 5)')
    
    args = parser.parse_args()
    
    # Normalize symbols
    base_symbol = args.base.upper()
    quote_symbol = args.quote.upper()
    
    if args.watch:
        print(f"👀 Watching price for {base_symbol}/{quote_symbol} (press Ctrl+C to stop)...")
        try:
            while True:
                # Clear screen
                os.system('cls' if os.name == 'nt' else 'clear')
                print(f"👀 Watching price for {base_symbol}/{quote_symbol} (press Ctrl+C to stop)...")
                print(f"⏱️  Refresh interval: {args.interval} seconds")
                
                # Add file modified time information
                price_file_path = f"shared_data/{base_symbol.lower()}{quote_symbol.lower()}_price.json"
                if os.path.exists(price_file_path):
                    file_mod_time = datetime.fromtimestamp(os.path.getmtime(price_file_path))
                    formatted_time = file_mod_time.strftime("%Y-%m-%d %H:%M:%S")
                    print(f"📄 File last modified: {formatted_time}")
                
                print("-" * 50)
                
                # Display the current price
                display_price_data(base_symbol, quote_symbol)
                
                # Wait for the next interval
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\n✅ Watch stopped by user")
    else:
        # Just display the current price once
        display_price_data(base_symbol, quote_symbol)
        
if __name__ == "__main__":
    main() 