#!/usr/bin/env python3
"""
Simple test script to verify the StrategyCoordinator status monitoring functionality.
"""

import sys
import os
import time
import logging

# Add the parent directory to the path so we can import the pylibre module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.pylibre import LibreClient
from src.pylibre.strategies import StrategyCoordinator
from src.pylibre.utils.logger import StrategyLogger, LogLevel

def main():
    """Test the StrategyCoordinator status monitoring."""
    # Set up basic logging to console
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler()]
    )
    
    logger = logging.getLogger("CoordinatorTest")
    logger.setLevel(logging.INFO)
    
    print("\n" + "=" * 80)
    print("STRATEGY COORDINATOR TEST")
    print("=" * 80 + "\n")
    
    # Initialize LibreClient
    logger.info("Initializing LibreClient...")
    client = LibreClient(api_url="https://testnet.libre.org", verbose=True)
    
    # Create a coordinator configuration that matches strategies.yaml
    coordinator_config = {
        'account': 'dextester',
        'base_symbol': 'BTC',
        'quote_symbol': 'USDT',
        'strategies': [
            {
                'type': 'MarketPriceTrackerStrategy',
                'enabled': True,
                'parameters': {
                    'update_interval_ms': 30000,
                    'price_source': 'binance',
                    'price_change_threshold': 0.005
                }
            },
            {
                'type': 'OrderBookMakerStrategy',
                'enabled': True,
                'parameters': {
                    'num_orders': 10,  # 5 per side
                    'min_spread_percentage': 0.01,
                    'max_spread_percentage': 0.05,
                    'quantity_distribution': 'random',
                    'update_interval_ms': 60000  # 1 minute
                }
            },
            {
                'type': 'OrderBookAnimatorStrategy',
                'enabled': True,
                'parameters': {
                    'activity_level': 'low',  # low, medium, high
                    'orders_per_cycle': 2,  # number of orders to update each cycle
                    'cycle_interval_ms': 10000  # 10 seconds
                }
            },
            {
                'type': 'TradeSimulatorStrategy',
                'enabled': True,
                'parameters': {
                    'trade_frequency': 'low',  # low, medium, high
                    'trade_size_variation': 'low',  # low, medium, high
                    'price_range_percentage': 0.005,  # 0.5%
                    'cycle_interval_ms': 30000,  # 30 seconds
                    'trades_per_cycle': 1,
                    'trade_pattern': 'random'  # random, trend, reversion
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
        
        # Manually add all strategies
        logger.info("Adding strategies to coordinator...")
        for strategy_config in coordinator_config['strategies']:
            if strategy_config['enabled']:
                strategy_type = strategy_config['type']
                logger.info(f"Adding {strategy_type} to coordinator...")
                coordinator.add_strategy(strategy_type, strategy_config['parameters'])
        
        # Start coordinator
        logger.info("Starting coordinator...")
        coordinator.start()
        logger.info("Coordinator started successfully!")
        
        # Wait for a moment to let strategies initialize
        time.sleep(5)
        
        # Print status
        logger.info("\nInitial Strategy Status:")
        if hasattr(coordinator, 'strategy_statuses'):
            for strategy_name, status in coordinator.strategy_statuses.items():
                logger.info(f"  {strategy_name}: {status}")
        else:
            logger.info("  No strategy status information available")
        
        # Run for a short time to see updates
        logger.info("\nRunning for 30 seconds to observe status updates...")
        for i in range(6):
            time.sleep(5)
            logger.info(f"\nStatus update {i+1}/6:")
            if hasattr(coordinator, 'strategy_statuses'):
                for strategy_name, status in coordinator.strategy_statuses.items():
                    logger.info(f"  {strategy_name}: {status}")
            else:
                logger.info("  No strategy status information available")
        
        # Test status monitor
        logger.info("\nTesting status monitor...")
        if hasattr(coordinator, 'start_status_monitor'):
            coordinator.start_status_monitor(interval_seconds=5)  # Update every 5 seconds
            logger.info("Status monitor started. Running for 15 seconds...")
            time.sleep(15)
            coordinator.stop_status_monitor()
            logger.info("Status monitor stopped.")
        else:
            logger.info("Status monitor method not available in this version of StrategyCoordinator")
        
        # Stop coordinator
        logger.info("\nStopping coordinator...")
        coordinator.stop()
        logger.info("Coordinator stopped successfully!")
        
        # Final status
        logger.info("\nFinal Strategy Status:")
        if hasattr(coordinator, 'strategy_statuses'):
            for strategy_name, status in coordinator.strategy_statuses.items():
                logger.info(f"  {strategy_name}: {status}")
        else:
            logger.info("  No strategy status information available")
            
    except Exception as e:
        logger.error(f"Error during test: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
    
    logger.info("\nTest completed.")

if __name__ == "__main__":
    main()
