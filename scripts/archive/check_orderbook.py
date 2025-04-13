#!/usr/bin/env python3
"""
Script to check the orderbook for outdated orders.
This is useful for debugging and maintenance.
"""

import sys
import os
import argparse
import yaml
import logging
from decimal import Decimal
import time

# Add the parent directory to the path so we can import the pylibre module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.pylibre import LibreClient
from src.pylibre.utils.logger import StrategyLogger, LogLevel

def load_config(config_path='config/strategies.yaml'):
    """Load configuration from YAML file."""
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print("Error loading config from {}: {}".format(config_path, e))
        return {}

def setup_logging(log_level=logging.INFO):
    """Configure basic logging."""
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger("check_orderbook")

def check_orderbook(client, account, base_symbol, quote_symbol, price_threshold=0.15, market_price=None):
    """
    Check the orderbook for orders that are too far from the market price.
    
    Args:
        client: LibreClient instance
        account: Account to check orders for
        base_symbol: Base symbol (e.g., BTC)
        quote_symbol: Quote symbol (e.g., USDT)
        price_threshold: Percentage threshold for considering an order outdated
        market_price: Current market price (optional)
        
    Returns:
        tuple: (total_orders, outdated_orders, current_price)
    """
    logger = logging.getLogger("check_orderbook")
    
    # Get current market price if not provided
    if market_price is None:
        # Try to read from shared data file
        price_file_path = f"shared_data/{base_symbol.lower()}{quote_symbol.lower()}_price.json"
        try:
            with open(price_file_path, 'r') as f:
                import json
                data = json.load(f)
                market_price = Decimal(str(data.get('price', 0)))
                logger.info(f"Read market price from file: {market_price}")
        except Exception as e:
            logger.warning(f"Could not read price from file: {e}")
            
            # Try to get price from ticker
            try:
                ticker = client.get_ticker(quote_symbol=quote_symbol, base_symbol=base_symbol)
                if ticker and 'last_price' in ticker:
                    market_price = Decimal(str(ticker['last_price']))
                    logger.info(f"Got market price from ticker: {market_price}")
            except Exception as e:
                logger.error(f"Could not get price from ticker: {e}")
                
            # Use default prices for common pairs if still no price
            if market_price is None or market_price == 0:
                if base_symbol == 'BTC' and quote_symbol == 'USDT':
                    market_price = Decimal('60000')
                elif base_symbol == 'LIBRE' and quote_symbol == 'BTC':
                    market_price = Decimal('0.0000000084')
                else:
                    logger.error(f"Could not determine market price for {base_symbol}/{quote_symbol}")
                    return 0, 0, None
    
    # Fetch orderbook
    try:
        order_book = client.fetch_order_book(
            quote_symbol=quote_symbol,
            base_symbol=base_symbol
        )
    except Exception as e:
        logger.error(f"Error fetching orderbook: {e}")
        return 0, 0, market_price
    
    # Convert threshold to Decimal
    price_threshold = Decimal(str(price_threshold))
    
    # Track counts
    total_orders = 0
    outdated_orders = 0
    
    # Check buy orders (bids)
    buy_orders = []
    for bid in order_book.get("bids", []):
        if bid.get("account") == account:
            total_orders += 1
            bid_price = Decimal(str(bid.get("price", 0)))
            
            # Calculate how far this order is from market price
            if market_price > 0:
                price_deviation = abs(bid_price - market_price) / market_price
                is_outdated = price_deviation > price_threshold
                
                if is_outdated:
                    outdated_orders += 1
                
                buy_orders.append({
                    "price": bid_price,
                    "deviation": price_deviation,
                    "outdated": is_outdated
                })
    
    # Check sell orders (offers)
    sell_orders = []
    for offer in order_book.get("offers", []):
        if offer.get("account") == account:
            total_orders += 1
            offer_price = Decimal(str(offer.get("price", 0)))
            
            # Calculate how far this order is from market price
            if market_price > 0:
                price_deviation = abs(offer_price - market_price) / market_price
                is_outdated = price_deviation > price_threshold
                
                if is_outdated:
                    outdated_orders += 1
                
                sell_orders.append({
                    "price": offer_price,
                    "deviation": price_deviation,
                    "outdated": is_outdated
                })
    
    # Print summary
    print(f"\n===== Orderbook Analysis for {account} on {base_symbol}/{quote_symbol} =====")
    print(f"Market price: {market_price} {quote_symbol}")
    print(f"Total orders: {total_orders} ({len(buy_orders)} buy, {len(sell_orders)} sell)")
    print(f"Outdated orders: {outdated_orders}")
    print(f"Price threshold: {float(price_threshold)*100:.1f}%")
    
    return total_orders, outdated_orders, market_price

def main():
    """Main function to check the orderbook."""
    parser = argparse.ArgumentParser(description='Check the orderbook for outdated orders')
    
    # Required arguments
    parser.add_argument('--base', required=True, help='Base symbol (e.g., BTC)')
    parser.add_argument('--quote', required=True, help='Quote symbol (e.g., USDT)')
    parser.add_argument('--account', required=True, help='Account to check orders for')
    
    # Optional arguments
    parser.add_argument('--config', default='config/strategies.yaml', help='Path to config file')
    parser.add_argument('--endpoint', help='API endpoint (overrides config)')
    parser.add_argument('--threshold', type=float, default=0.15, 
                        help='Percentage threshold for considering an order outdated (default: 15%)')
    parser.add_argument('--price', type=float, help='Market price to use (overrides automatic detection)')
    parser.add_argument('--log-level', default='INFO', 
                        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                        help='Set logging level (default: INFO)')
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = getattr(logging, args.log_level)
    logger = setup_logging(log_level=log_level)
    
    # Load configuration
    try:
        with open(args.config, 'r') as f:
            config = yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Error loading config from {args.config}: {e}")
        return
    
    # Get API endpoint
    api_endpoint = args.endpoint or config.get('api_endpoint')
    if not api_endpoint:
        logger.error("No API endpoint specified")
        return
    
    # Initialize client
    client = LibreClient(api_url=api_endpoint, verbose=False)
    
    # Set market price if provided
    market_price = Decimal(str(args.price)) if args.price else None
    
    # Check orderbook
    total_orders, outdated_orders, detected_price = check_orderbook(
        client=client,
        account=args.account,
        base_symbol=args.base,
        quote_symbol=args.quote,
        price_threshold=args.threshold,
        market_price=market_price
    )

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting due to keyboard interrupt")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc() 