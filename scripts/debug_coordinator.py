#!/usr/bin/env python3
"""
Debug script to troubleshoot the StrategyCoordinator strategy loading and status monitoring.
"""

import sys
import os
import time
import logging
import yaml

# Add the parent directory to the path so we can import the pylibre module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.pylibre import LibreClient
from src.pylibre.strategies import StrategyCoordinator

def load_config(config_path='config/strategies.yaml'):
    """Load configuration from YAML file."""
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"Error loading config from {config_path}: {e}")
        return {}

def main():
    """Debug the StrategyCoordinator."""
    # Set up basic logging to console
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )
    
    logger = logging.getLogger("DebugCoordinator")
    logger.setLevel(logging.INFO)
    
    print("\n" + "=" * 80)
    print("STRATEGY COORDINATOR DEBUG")
    print("=" * 80 + "\n")
    
    # Initialize LibreClient
    logger.info("Initializing LibreClient...")
    client = LibreClient(api_url="https://testnet.libre.org", verbose=True)
    
    # Load configuration
    config = load_config()
    
    # Trading pair info
    base_symbol = "BTC"
    quote_symbol = "USDT"
    account = "dextester"
    pair_key = f"{base_symbol}{quote_symbol}"
    
    # Get trading pair specific configuration
    pair_config = config.get('trading_pairs', {}).get(pair_key, {})
    
    # Debug pair config
    logger.info(f"Trading pair config for {pair_key}:")
    for strategy_type, strategy_config in pair_config.items():
        logger.info(f"  {strategy_type}:")
        for key, value in strategy_config.items():
            logger.info(f"    {key}: {value}")
    
    # Create coordinator configuration
    coordinator_config = {
        'account': account,
        'base_symbol': base_symbol,
        'quote_symbol': quote_symbol,
        'strategies': {}
    }
    
    # Manually add strategies for debugging
    if 'price_tracker' in pair_config:
        logger.info("Adding MarketPriceTrackerStrategy")
        coordinator_config['strategies']['MarketPriceTrackerStrategy'] = pair_config['price_tracker']
        # Fix key name if needed
        if 'source' in coordinator_config['strategies']['MarketPriceTrackerStrategy']:
            coordinator_config['strategies']['MarketPriceTrackerStrategy']['price_source'] = \
                coordinator_config['strategies']['MarketPriceTrackerStrategy'].pop('source')
    
    # Debug coordinator config
    logger.info("Final coordinator config:")
    for key, value in coordinator_config.items():
        if key != 'strategies':
            logger.info(f"  {key}: {value}")
        else:
            logger.info("  strategies:")
            for strategy_name, strategy_config in value.items():
                logger.info(f"    {strategy_name}:")
                for config_key, config_value in strategy_config.items():
                    logger.info(f"      {config_key}: {config_value}")
    
    try:
        # Create coordinator
        logger.info("Creating StrategyCoordinator...")
        coordinator = StrategyCoordinator(client, coordinator_config)
        
        # Manually add a strategy for testing
        logger.info("Manually adding MarketPriceTrackerStrategy...")
        success = coordinator.add_strategy('MarketPriceTrackerStrategy', coordinator_config['strategies'].get('MarketPriceTrackerStrategy', {}))
        logger.info(f"Strategy add result: {'Success' if success else 'Failed'}")
        
        # Check strategies
        logger.info(f"Coordinator has {len(coordinator.strategies)} strategies:")
        for strategy_name, strategy in coordinator.strategies.items():
            logger.info(f"  {strategy_name}: {strategy}")
        
        # Start coordinator
        logger.info("Starting coordinator...")
        coordinator.start()
        logger.info("Coordinator started")
        
        # Check strategy statuses
        logger.info("Strategy statuses after start:")
        if hasattr(coordinator, 'strategy_statuses'):
            for strategy_name, status in coordinator.strategy_statuses.items():
                logger.info(f"  {strategy_name}: {status}")
        else:
            logger.info("  No strategy status information available")
        
        # Run for a short time
        logger.info("Running for 10 seconds...")
        for i in range(10):
            time.sleep(1)
            print(".", end="", flush=True)
        print()
        
        # Check strategy statuses again
        logger.info("Strategy statuses after running:")
        if hasattr(coordinator, 'strategy_statuses'):
            for strategy_name, status in coordinator.strategy_statuses.items():
                logger.info(f"  {strategy_name}: {status}")
        else:
            logger.info("  No strategy status information available")
        
        # Stop coordinator
        logger.info("Stopping coordinator...")
        coordinator.stop()
        logger.info("Coordinator stopped")
        
    except Exception as e:
        logger.error(f"Error during debug: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
    
    logger.info("Debug completed")

if __name__ == "__main__":
    main()
