#!/usr/bin/env python3
"""
Script to run the OrderBookAnimatorStrategy for a specified trading pair.
This strategy creates the appearance of market activity by periodically canceling
and replacing orders with slight variations.
"""

import sys
import os
import argparse
import yaml
import logging
import time
from decimal import Decimal

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from pylibre.client import LibreClient
from pylibre.strategies import OrderBookAnimatorStrategy

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("run_orderbook_animator")

def load_config(config_path='config/config.yaml'):
    """Load configuration from YAML file"""
    try:
        with open(config_path, 'r') as file:
            return yaml.safe_load(file)
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        return {}

def main():
    """Main function to run the strategy"""
    parser = argparse.ArgumentParser(description='Run OrderBookAnimatorStrategy')
    parser.add_argument('--account', required=True, help='Account to use for animation')
    parser.add_argument('--base', required=True, help='Base symbol (e.g., LIBRE)')
    parser.add_argument('--quote', required=True, help='Quote symbol (e.g., BTC)')
    parser.add_argument('--config', default='config/config.yaml', help='Path to config file')
    parser.add_argument('--activity', default='medium', choices=['low', 'medium', 'high'], help='Activity level')
    parser.add_argument('--orders', type=int, default=3, help='Orders per cycle')
    parser.add_argument('--interval', type=int, default=5000, help='Cycle interval in milliseconds')
    parser.add_argument('--price-variation', type=float, help='Price variation percentage (e.g., 0.003 for 0.3%)')
    parser.add_argument('--quantity-variation', type=float, help='Quantity variation percentage (e.g., 0.1 for 10%)')
    args = parser.parse_args()

    # Load configuration
    config = load_config(args.config)
    
    # Initialize client
    client = LibreClient(config.get('api_endpoint', 'https://testnet.libre.org'))
    
    # Get strategy parameters
    strategy_params = config.get('strategies', {}).get('OrderBookAnimatorStrategy', {})
    
    # Override with command line arguments
    strategy_params['activity_level'] = args.activity
    strategy_params['orders_per_cycle'] = args.orders
    strategy_params['cycle_interval_ms'] = args.interval
    
    if args.price_variation is not None:
        strategy_params['price_variation_percentage'] = args.price_variation
        
    if args.quantity_variation is not None:
        strategy_params['quantity_variation_percentage'] = args.quantity_variation
    
    # Create strategy
    strategy = OrderBookAnimatorStrategy(
        client=client,
        account=args.account,
        base_symbol=args.base,
        quote_symbol=args.quote,
        parameters=strategy_params
    )
    
    # Run the strategy
    try:
        logger.info(f"Starting OrderBookAnimatorStrategy for {args.base}/{args.quote}")
        strategy.run()
    except KeyboardInterrupt:
        logger.info("Strategy stopped by user")
    except Exception as e:
        logger.error(f"Error running strategy: {e}")
    finally:
        logger.info("Strategy execution completed")

if __name__ == "__main__":
    main() 