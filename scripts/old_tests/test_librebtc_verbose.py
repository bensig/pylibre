#!/usr/bin/env python3
"""
Test script for LIBRE/BTC buy orders with more verbose error logging.
This script uses the LibreClient with enhanced error logging.
"""

import sys
import os
import time
import json
import logging
from decimal import Decimal

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from pylibre.client import LibreClient

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("LibreBTCTest")

def place_buy_order(client, account, quantity, price, base_symbol, quote_symbol, dex_contract):
    """Place a buy order for a specific trading pair with verbose error logging."""
    logger.info(f"Placing buy order: {quantity} {base_symbol} @ {price} {quote_symbol}")
    
    # Calculate the amount of quote currency to send
    quote_amount = Decimal(str(quantity)) * Decimal(str(price))
    quote_amount_str = f"{quote_amount:.8f}"
    
    # Determine the contract for the quote symbol
    quote_contract = f"{quote_symbol.lower()}.libre"
    
    # Create the memo with the correct format
    memo = f"buy:{quantity} {base_symbol}:{price} {quote_symbol}"
    
    logger.info(f"Transfer Details:")
    logger.info(f"From: {account}")
    logger.info(f"To: {dex_contract}")
    logger.info(f"Amount: {quote_amount_str} {quote_symbol}")
    logger.info(f"Contract: {quote_contract}")
    logger.info(f"Memo: {memo}")
    
    # Enable verbose mode for the client
    client.verbose = True
    
    # Monkey patch the client's error handling to log more details
    original_execute_action = client.execute_action
    
    def verbose_execute_action(*args, **kwargs):
        logger.debug(f"Executing action with args: {args}")
        logger.debug(f"Executing action with kwargs: {kwargs}")
        try:
            result = original_execute_action(*args, **kwargs)
            logger.debug(f"Action result: {json.dumps(result, indent=2)}")
            return result
        except Exception as e:
            logger.error(f"Error in execute_action: {str(e)}", exc_info=True)
            raise
    
    # Replace the method temporarily
    client.execute_action = verbose_execute_action
    
    try:
        # Try to place the order
        result = client.transfer(
            from_account=account,
            to_account=dex_contract,
            quantity=f"{quote_amount_str} {quote_symbol}",
            memo=memo,
            contract=quote_contract
        )
        
        # Log the result
        if isinstance(result, dict):
            logger.info(f"Transfer result: {json.dumps(result, indent=2)}")
        else:
            logger.info(f"Transfer result: {result}")
        
        if result.get("success"):
            logger.info("✅ Buy order placed successfully")
            logger.info(f"Transaction ID: {result.get('data', {}).get('transaction_id')}")
            return True
        else:
            error = result.get("error", "Unknown error")
            logger.error(f"❌ Failed to place buy order: {error}")
            
            # Try to extract more error details
            if isinstance(error, dict):
                logger.error(f"Error details: {json.dumps(error, indent=2)}")
            elif isinstance(error, str):
                logger.error(f"Error message: {error}")
                
                # Try to parse the error string as JSON
                try:
                    error_json = json.loads(error)
                    logger.error(f"Parsed error: {json.dumps(error_json, indent=2)}")
                except:
                    pass
            
            return False
    except Exception as e:
        logger.error(f"❌ Exception placing buy order: {str(e)}", exc_info=True)
        return False
    finally:
        # Restore the original method
        client.execute_action = original_execute_action

def main():
    # Initialize client
    logger.info("Initializing LibreClient...")
    client = LibreClient(network='testnet', verbose=True)
    
    # Define account to test
    account = "bentest3"
    
    # Define trading pair parameters
    base_symbol = "LIBRE"
    quote_symbol = "BTC"
    dex_contract = "dex.libre"
    
    logger.info(f"Testing LIBRE/BTC Buy Order with Verbose Logging")
    
    # Check initial balances
    logger.info("Checking initial balances...")
    base_balance = client.get_currency_balance(account, base_symbol)
    quote_balance = client.get_currency_balance(account, quote_symbol)
    
    logger.info(f"{account} {base_symbol} balance: {base_balance}")
    logger.info(f"{account} {quote_symbol} balance: {quote_balance}")
    
    # Test a buy order with minimum BTC value
    quantity = "1000.0000"  # LIBRE
    price = "0.00000010"    # BTC per LIBRE (0.00010000 BTC total)
    
    logger.info(f"Testing buy order: {quantity} {base_symbol} @ {price} {quote_symbol}")
    logger.info(f"Total value: {Decimal(quantity) * Decimal(price):.8f} {quote_symbol}")
    
    # Try to place the order
    success = place_buy_order(
        client=client,
        account=account,
        quantity=quantity,
        price=price,
        base_symbol=base_symbol,
        quote_symbol=quote_symbol,
        dex_contract=dex_contract
    )
    
    # Check final balances
    logger.info("Checking final balances...")
    base_balance_after = client.get_currency_balance(account, base_symbol)
    quote_balance_after = client.get_currency_balance(account, quote_symbol)
    
    logger.info(f"{account} {base_symbol} balance: {base_balance_after}")
    logger.info(f"{account} {quote_symbol} balance: {quote_balance_after}")
    
    # Print summary
    logger.info("Buy Order Test Summary:")
    status = "Success" if success else "Failed"
    logger.info(f"Buy order ({quantity} {base_symbol} @ {price} {quote_symbol}): {status}")
    
    logger.info("Testing completed!")

if __name__ == "__main__":
    main() 