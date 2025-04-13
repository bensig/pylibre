#!/usr/bin/env python3
"""
Script to run the MarketPriceTrackerStrategy for a specified trading pair.
This strategy monitors external market prices and updates the center price of orderbooks.
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
from pylibre.strategies import MarketPriceTrackerStrategy

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("run_market_price_tracker")

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
    parser = argparse.ArgumentParser(description='Run MarketPriceTrackerStrategy')
    parser.add_argument('--account', required=True, help='Account to use for tracking')
    parser.add_argument('--base', required=True, help='Base symbol (e.g., LIBRE)')
    parser.add_argument('--quote', required=True, help='Quote symbol (e.g., BTC)')
    parser.add_argument('--config', default='config/config.yaml', help='Path to config file')
    parser.add_argument('--source', default='fixed', help='Price source (fixed, binance, etc.)')
    parser.add_argument('--interval', type=int, default=30000, help='Update interval in milliseconds')
    parser.add_argument('--threshold', type=float, default=0.005, help='Price change threshold (e.g., 0.005 for 0.5%)')
    parser.add_argument('--fixed-price', type=float, help='Fixed price to use (default: 0.00000001 for LIBRE/BTC, 0 otherwise)')
    args = parser.parse_args()

    # Load configuration
    config = load_config(args.config)
    
    # Initialize client
    client = LibreClient(config.get('api_endpoint', 'https://testnet.libre.org'))
    
    # Get strategy parameters
    strategy_params = config.get('strategies', {}).get('MarketPriceTrackerStrategy', {})
    
    # Override with command line arguments
    strategy_params['source'] = args.source
    strategy_params['update_interval_ms'] = args.interval
    strategy_params['price_change_threshold'] = args.threshold
    
    # Set fixed price if provided or use default for LIBRE/BTC
    if args.fixed_price is not None:
        strategy_params['fixed_price'] = args.fixed_price
    elif args.base.upper() == 'LIBRE' and args.quote.upper() == 'BTC':
        strategy_params['fixed_price'] = 0.00000001  # 1 SAT for LIBRE/BTC
    
    # Create strategy
    strategy = MarketPriceTrackerStrategy(
        client=client,
        account=args.account,
        base_symbol=args.base,
        quote_symbol=args.quote,
        parameters=strategy_params
    )
    
    # Run the strategy
    try:
        logger.info(f"Starting MarketPriceTrackerStrategy for {args.base}/{args.quote}")
        strategy.run()
    except KeyboardInterrupt:
        logger.info("Strategy stopped by user")
    except Exception as e:
        logger.error(f"Error running strategy: {e}")
    finally:
        logger.info("Strategy execution completed")

if __name__ == "__main__":
    main() 