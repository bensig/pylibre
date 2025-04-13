#!/usr/bin/env python3
"""
Script to run the OrderBookMakerStrategy for a specified trading pair.
"""

import sys
import os
import argparse
import yaml
import logging
from decimal import Decimal

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from pylibre.client import LibreClient
from pylibre.strategies import OrderBookMakerStrategy

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("run_orderbook_maker")

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
    parser = argparse.ArgumentParser(description='Run OrderBookMakerStrategy')
    parser.add_argument('--account', required=True, help='Account to use for trading')
    parser.add_argument('--base', required=True, help='Base symbol (e.g., LIBRE)')
    parser.add_argument('--quote', required=True, help='Quote symbol (e.g., BTC)')
    parser.add_argument('--config', default='config/config.yaml', help='Path to config file')
    parser.add_argument('--no-cancel', action='store_true', help='Skip cancelling existing orders')
    parser.add_argument('--min-spread', type=float, help='Minimum spread percentage (e.g., 0.01 for 1%)')
    parser.add_argument('--max-spread', type=float, help='Maximum spread percentage (e.g., 0.05 for 5%)')
    parser.add_argument('--orders', type=int, help='Number of orders to place (half on each side)')
    parser.add_argument('--distribution', choices=['equal', 'random'], help='Quantity distribution method')
    args = parser.parse_args()

    # Load configuration
    config = load_config(args.config)
    
    # Initialize client
    client = LibreClient(config.get('api_endpoint', 'https://testnet.libre.org'))
    
    # Get strategy parameters
    strategy_params = config.get('strategies', {}).get('OrderBookMakerStrategy', {})
    
    # Override parameters from command line if provided
    if args.min_spread is not None:
        strategy_params['min_spread_percentage'] = args.min_spread
    if args.max_spread is not None:
        strategy_params['max_spread_percentage'] = args.max_spread
    if args.orders is not None:
        strategy_params['num_orders'] = args.orders
    if args.distribution is not None:
        strategy_params['quantity_distribution'] = args.distribution
    
    # Create strategy
    strategy = OrderBookMakerStrategy(
        client=client,
        account=args.account,
        base_symbol=args.base,
        quote_symbol=args.quote,
        parameters=strategy_params
    )
    
    # Run the strategy
    if args.no_cancel:
        # Skip cancellation step
        logger.info("Skipping cancellation of existing orders")
        strategy.run(cancel_existing=False)
    else:
        # Run with cancellation
        strategy.run(cancel_existing=True)
    
    # Log summary
    logger.info("Strategy execution completed")

if __name__ == "__main__":
    main() 