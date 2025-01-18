#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import argparse
from pylibre.client import LibreClient
from pylibre.manager.config_manager import ConfigManager
import logging
import yaml

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    # Initialize client with YAML config
    client = LibreClient(
        network='testnet',
        config_path='config/config.yaml',
        verbose=True
    )
    
    from_account = "bentester"
    to_account = "dextrader"
    
    # Check initial balances
    print("\nInitial balances:")
    print(f"{from_account} USDT:", client.get_currency_balance(from_account, "USDT"))
    print(f"{to_account} USDT:", client.get_currency_balance(to_account, "USDT"))
    
    # Perform transfer
    print("\nExecuting transfer...")
    result = client.transfer(
        from_account=from_account,
        to_account=to_account,
        quantity="1.00000000 USDT"
    )
    
    if result["success"]:
        print("Transfer successful!")
        print("Transaction ID:", result["data"]["transaction_id"])
    else:
        print("Transfer failed:", result["error"])
    
    # Check final balances
    print("\nFinal balances:")
    print(f"{from_account} USDT:", client.get_currency_balance(from_account, "USDT"))
    print(f"{to_account} USDT:", client.get_currency_balance(to_account, "USDT"))

if __name__ == "__main__":
    main() 