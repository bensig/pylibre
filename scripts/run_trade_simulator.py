#!/usr/bin/env python3
"""
Script to run the TradeSimulatorStrategy, which creates the appearance of market activity
by simulating trades between accounts.
"""

import sys
import os
import argparse
import yaml
import logging
import time
import signal

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from pylibre.client import LibreClient
from pylibre.strategies import TradeSimulatorStrategy
from pylibre.utils.logger import StrategyLogger, LogLevel

# Global variable to track if the strategy is running
running = True

def load_config(config_path='config/strategies.yaml'):
    """Load configuration from YAML file."""
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"Error loading config from {config_path}: {e}")
        return {}

def signal_handler(sig, frame):
    """Handle Ctrl+C to gracefully stop the strategy."""
    global running
    print("\nStopping strategy (this may take a moment)...")
    running = False

def main():
    """Main function to run the TradeSimulatorStrategy."""
    parser = argparse.ArgumentParser(description='Run the TradeSimulatorStrategy')
    
    # Required arguments
    parser.add_argument('--account', required=True, help='Primary account for trading')
    parser.add_argument('--base', required=True, help='Base symbol (e.g., LIBRE)')
    parser.add_argument('--quote', required=True, help='Quote symbol (e.g., BTC)')
    
    # Optional arguments
    parser.add_argument('--secondary-account', help='Secondary account for the other side of trades')
    parser.add_argument('--config', default='config/strategies.yaml', help='Path to config file')
    parser.add_argument('--frequency', choices=['low', 'medium', 'high'], help='Trade frequency')
    parser.add_argument('--size-variation', choices=['low', 'medium', 'high'], help='Trade size variation')
    parser.add_argument('--price-range', type=float, help='Price range percentage (e.g., 0.01 for 1%%)')
    parser.add_argument('--interval', type=int, help='Cycle interval in milliseconds')
    parser.add_argument('--trades-per-cycle', type=int, help='Number of trades per cycle')
    parser.add_argument('--min-trade-size', type=float, help='Minimum trade size')
    parser.add_argument('--max-trade-size', type=float, help='Maximum trade size')
    parser.add_argument('--pattern', choices=['random', 'trend', 'reversion'], help='Trade pattern')
    parser.add_argument('--trend-direction', choices=['up', 'down', 'neutral'], help='Trend direction')
    parser.add_argument('--trend-strength', type=float, help='Trend strength (0.0 to 1.0)')
    
    args = parser.parse_args()
    
    # Set up logging
    logger = StrategyLogger(f"TradeSimulator_{args.account}", level=LogLevel.INFO)
    logger.info(f"Starting TradeSimulatorStrategy for {args.base}/{args.quote}")
    
    # Load configuration
    config = load_config(args.config)
    
    # Get API endpoint from config
    api_endpoint = config.get('api_endpoint', 'https://testnet.libre.org')
    
    # Initialize LibreClient
    client = LibreClient(api_url=api_endpoint, verbose=True)
    
    # Get trading pair specific configuration
    pair_key = f"{args.base}{args.quote}"
    pair_config = config.get('trading_pairs', {}).get(pair_key, {})
    
    # Get simulator configuration
    simulator_config = pair_config.get('simulator', {})
    
    # Get default strategy parameters
    default_params = config.get('strategies', {}).get('TradeSimulatorStrategy', {})
    
    # Combine configurations with command line arguments taking precedence
    parameters = {**default_params, **simulator_config}
    
    # Override with command line arguments if provided
    if args.secondary_account:
        parameters['secondary_account'] = args.secondary_account
    if args.frequency:
        parameters['trade_frequency'] = args.frequency
    if args.size_variation:
        parameters['trade_size_variation'] = args.size_variation
    if args.price_range is not None:
        parameters['price_range_percentage'] = args.price_range
    if args.interval:
        parameters['cycle_interval_ms'] = args.interval
    if args.trades_per_cycle:
        parameters['trades_per_cycle'] = args.trades_per_cycle
    if args.min_trade_size is not None:
        parameters['min_trade_size'] = args.min_trade_size
    if args.max_trade_size is not None:
        parameters['max_trade_size'] = args.max_trade_size
    if args.pattern:
        parameters['trade_pattern'] = args.pattern
    if args.trend_direction:
        parameters['trend_direction'] = args.trend_direction
    if args.trend_strength is not None:
        parameters['trend_strength'] = args.trend_strength
    
    # Log the parameters
    logger.info("Strategy parameters:")
    for key, value in parameters.items():
        logger.info(f"  {key}: {value}")
    
    # Create and run the strategy
    try:
        # Register signal handler for Ctrl+C
        signal.signal(signal.SIGINT, signal_handler)
        
        # Create strategy instance
        strategy = TradeSimulatorStrategy(
            client=client,
            account=args.account,
            base_symbol=args.base,
            quote_symbol=args.quote,
            parameters=parameters,
            logger=logger
        )
        
        # Run the strategy
        logger.info("Starting strategy...")
        
        # Use our own loop to handle graceful shutdown
        strategy.running = True
        
        while strategy.running and running:
            # Simulate trades
            trades_executed = strategy.simulate_trades()
            logger.info(f"Executed {trades_executed} trades this cycle")
            
            # Wait for next cycle
            time.sleep(strategy.cycle_interval_ms / 1000)
            
    except Exception as e:
        logger.error(f"Error running strategy: {e}")
    finally:
        # Clean up
        if 'strategy' in locals():
            logger.info("Cleaning up...")
            strategy.cleanup()
        
        logger.info("Strategy stopped")

if __name__ == "__main__":
    main() 