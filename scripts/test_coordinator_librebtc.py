#!/usr/bin/env python3
"""
Test script to verify the StrategyCoordinator functionality with LIBRE/BTC trading pair.
This version uses all available strategies from the strategies.yaml configuration.
"""

import sys
import os
import time
import logging
import warnings

# Suppress LibreSSL warnings from urllib3
warnings.filterwarnings("ignore", category=Warning, message=".*OpenSSL 1.1.1.*LibreSSL.*")

# Add the parent directory to the path so we can import the pylibre module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.pylibre import LibreClient
from src.pylibre.strategies import StrategyCoordinator
from src.pylibre.utils.logger import StrategyLogger, LogLevel

def main():
    """Test the StrategyCoordinator with LIBRE/BTC trading pair using all strategies."""
    # Set up basic logging to console
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )
    
    logger = logging.getLogger("LibreBtcCoordinatorTest")
    logger.setLevel(logging.INFO)
    
    print("\n" + "=" * 80)
    print("LIBRE/BTC FULL STRATEGY COORDINATOR TEST")
    print("=" * 80 + "\n")
    
    # Initialize LibreClient
    logger.info("Initializing LibreClient...")
    client = LibreClient(api_url="https://testnet.libre.org", verbose=True)
    
    # Create a coordinator configuration for LIBRE/BTC with all strategies
    coordinator_config = {
        'account': 'bentester',
        'base_symbol': 'LIBRE',
        'quote_symbol': 'BTC',
        'strategies': [
            {
                'type': 'MarketPriceTrackerStrategy',
                'enabled': True,
                'parameters': {
                    'update_interval_ms': 60000,  # 1 minute
                    'price_source': 'fixed',
                    'fixed_price': 0.0000002,  # Default price for LIBRE/BTC
                    'price_change_threshold': 0.01  # 1%
                }
            },
            {
                'type': 'OrderBookMakerStrategy',
                'enabled': True,
                'parameters': {
                    'num_orders': 30,
                    'min_spread_percentage': 0.01,
                    'max_spread_percentage': 0.15,
                    'quantity_distribution': 'random',
                    'update_interval_ms': 120000,  # 2 minutes
                    'max_order_size_base': 1000,  # Limit order size to avoid balance issues
                    'min_order_size_base': 100    # Minimum order size
                }
            },
            {
                'type': 'OrderBookAnimatorStrategy',
                'enabled': True,
                'parameters': {
                    'activity_level': 'high',
                    'orders_per_cycle': 5,
                    'cycle_interval_ms': 3000,  # 3 seconds
                    'max_order_size_base': 500,  # Limit order size to avoid balance issues
                    'min_order_size_base': 50    # Minimum order size
                }
            },
            {
                'type': 'TradeSimulatorStrategy',
                'enabled': True,
                'parameters': {
                    'trade_frequency': 'high',
                    'trade_size_variation': 'high',
                    'price_range_percentage': 0.01,  # 1%
                    'cycle_interval_ms': 15000,  # 15 seconds
                    'trades_per_cycle': 2,
                    'trade_pattern': 'trend',
                    'trend_direction': 'up',
                    'trend_strength': 0.7,
                    'max_trade_size_base': 200,  # Limit trade size to avoid balance issues
                    'min_trade_size_base': 20    # Minimum trade size
                }
            }
        ]
    }
    
    # Display configuration
    logger.info("Test configuration:")
    logger.info(f"  Trading Pair: {coordinator_config['base_symbol']}/{coordinator_config['quote_symbol']}")
    logger.info(f"  Account: {coordinator_config['account']}")
    logger.info("  Strategies:")
    for strategy in coordinator_config['strategies']:
        logger.info(f"    - {strategy['type']}: {strategy}")
    
    try:
        # Create coordinator
        logger.info("Creating StrategyCoordinator...")
        coordinator = StrategyCoordinator(client, coordinator_config)
        
        # Manually add enabled strategies
        logger.info("Adding strategies to coordinator...")
        for strategy_config in coordinator_config['strategies']:
            if strategy_config['enabled']:
                strategy_type = strategy_config['type']
                logger.info(f"Adding {strategy_type} to coordinator...")
                coordinator.add_strategy(strategy_type, strategy_config['parameters'])
        
        # Start coordinator
        logger.info("Starting coordinator...")
        coordinator.start()
        
        # Wait a moment for threads to start
        time.sleep(1)
        
        # Check initial status
        logger.info("\nInitial Strategy Status:")
        for strategy_type, status in coordinator.strategy_statuses.items():
            logger.info(f"  {strategy_type}: {status}")
        
        # Run for a while to observe status updates
        logger.info("\nRunning for 120 seconds to observe status updates...")
        
        # Check status every 20 seconds for 2 minutes
        for i in range(1, 7):
            time.sleep(20)
            logger.info(f"\nStatus update {i}/6:")
            for strategy_type, status in coordinator.strategy_statuses.items():
                logger.info(f"  {strategy_type}: {status}")
        
        # Test status monitor
        logger.info("\nTesting status monitor...")
        coordinator.start_status_monitor(interval_seconds=30)
        
        # Run for another 60 seconds
        logger.info("Running for 60 more seconds with status monitor...")
        time.sleep(60)
        
        # Stop coordinator
        logger.info("\nStopping coordinator...")
        coordinator.stop()
        
        # Wait for threads to stop
        time.sleep(2)
        
        # Final status
        logger.info("\nFinal Strategy Status:")
        for strategy_type, status in coordinator.strategy_statuses.items():
            logger.info(f"  {strategy_type}: {status}")
        
        logger.info("\nTest completed successfully!")
        
    except Exception as e:
        logger.error(f"Error in test: {e}")
        import traceback
        logger.error(traceback.format_exc())
        
        # Try to stop coordinator if it exists
        try:
            if 'coordinator' in locals():
                coordinator.stop()
        except:
            pass

if __name__ == "__main__":
    main()
