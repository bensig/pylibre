#!/usr/bin/env python3
"""
Script to check and fix price issues in the shared_data files.
"""
import os
import sys
import json
import time
from datetime import datetime
import argparse

def list_price_files():
    """List all price files in the shared_data directory."""
    if not os.path.exists("shared_data"):
        print("❌ shared_data directory doesn't exist")
        return
        
    files = os.listdir("shared_data")
    price_files = [f for f in files if f.endswith("_price.json")]
    
    if not price_files:
        print("❌ No price files found in shared_data directory")
        return
        
    print(f"📊 Found {len(price_files)} price files:")
    for file in price_files:
        file_path = os.path.join("shared_data", file)
        mod_time = os.path.getmtime(file_path)
        mod_time_str = datetime.fromtimestamp(mod_time).strftime("%Y-%m-%d %H:%M:%S")
        
        # Try to read the file contents
        try:
            with open(file_path, "r") as f:
                data = json.load(f)
            
            if isinstance(data, dict) and "price" in data:
                price = data["price"]
                last_updated = data.get("last_updated", "Unknown")
                
                if isinstance(last_updated, str):
                    try:
                        dt = datetime.fromisoformat(last_updated)
                        last_updated = dt.strftime("%Y-%m-%d %H:%M:%S")
                    except:
                        pass
                        
                print(f"  📄 {file}: Price={price}, Last Updated={last_updated}")
            else:
                print(f"  📄 {file}: {data} (old format)")
                
            print(f"     File last modified: {mod_time_str}")
        except Exception as e:
            print(f"  ❌ Error reading {file}: {e}")
            
    print("")
    
def check_price_file(base_symbol, quote_symbol):
    """Check a specific price file."""
    file_name = f"{base_symbol.lower()}{quote_symbol.lower()}_price.json"
    file_path = os.path.join("shared_data", file_name)
    
    if not os.path.exists(file_path):
        print(f"❌ Price file for {base_symbol}/{quote_symbol} doesn't exist")
        print(f"  Expected path: {file_path}")
        return None
        
    try:
        with open(file_path, "r") as f:
            data = json.load(f)
            
        if isinstance(data, dict) and "price" in data:
            price = data["price"]
            last_updated = data.get("last_updated", "Unknown")
            
            if isinstance(last_updated, str):
                try:
                    dt = datetime.fromisoformat(last_updated)
                    last_updated_ago = (datetime.now() - dt).total_seconds()
                    last_updated_str = dt.strftime("%Y-%m-%d %H:%M:%S")
                    last_updated_ago_str = f"{int(last_updated_ago)}s ago" if last_updated_ago < 60 else f"{int(last_updated_ago/60)}m ago"
                    print(f"✅ Found price file for {base_symbol}/{quote_symbol}")
                    print(f"  Price: {price}")
                    print(f"  Last updated: {last_updated_str} ({last_updated_ago_str})")
                except Exception as e:
                    print(f"⚠️ Invalid timestamp format in {file_name}: {e}")
                    print(f"  Raw value: {last_updated}")
            else:
                print(f"⚠️ No valid timestamp in {file_name}")
                print(f"  Price: {price}")
                
            # Check file permissions and modification time
            mod_time = os.path.getmtime(file_path)
            mod_time_str = datetime.fromtimestamp(mod_time).strftime("%Y-%m-%d %H:%M:%S")
            print(f"  File last modified: {mod_time_str}")
            print(f"  File permissions: {oct(os.stat(file_path).st_mode)[-3:]}")
            
            return data
        else:
            print(f"⚠️ {file_name} uses old format (no timestamp)")
            print(f"  Data: {data}")
            return data
    except Exception as e:
        print(f"❌ Error reading {file_name}: {e}")
        return None
        
def update_price(base_symbol, quote_symbol, price):
    """Update the price for a specific trading pair."""
    file_name = f"{base_symbol.lower()}{quote_symbol.lower()}_price.json"
    file_path = os.path.join("shared_data", file_name)
    
    # Create shared_data directory if it doesn't exist
    if not os.path.exists("shared_data"):
        os.makedirs("shared_data")
        
    # Create the updated data
    data = {
        "price": float(price),
        "last_updated": datetime.now().isoformat()
    }
    
    try:
        # Use atomic write
        temp_file = file_path + ".tmp"
        with open(temp_file, "w") as f:
            json.dump(data, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
            
        os.rename(temp_file, file_path)
        
        print(f"✅ Successfully updated price for {base_symbol}/{quote_symbol}")
        print(f"  New price: {price}")
        print(f"  Last updated: {data['last_updated']}")
        return True
    except Exception as e:
        print(f"❌ Error updating price: {e}")
        return False

def main():
    """Main function to parse arguments."""
    parser = argparse.ArgumentParser(description='Check and fix price files')
    parser.add_argument('--list', action='store_true', help='List all price files')
    parser.add_argument('--base', help='Base symbol (e.g., BTC)')
    parser.add_argument('--quote', help='Quote symbol (e.g., USDT)')
    parser.add_argument('--set-price', type=float, help='Set a new price value')
    
    args = parser.parse_args()
    
    if args.list:
        list_price_files()
        return
        
    if args.base and args.quote:
        base_symbol = args.base.upper()
        quote_symbol = args.quote.upper()
        
        # Check the price file
        data = check_price_file(base_symbol, quote_symbol)
        
        # Set a new price if requested
        if args.set_price is not None:
            update_price(base_symbol, quote_symbol, args.set_price)
    else:
        parser.print_help()
        
if __name__ == "__main__":
    main() 