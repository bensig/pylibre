#!/usr/bin/env python3
"""
Simple test script to verify the StrategyCoordinator status monitoring functionality.
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
from src.pylibre.strategies.marketpricetracker import MarketPriceTrackerStrategy
from src.pylibre.utils.logger import StrategyLogger, LogLevel

def main():
    """Test the StrategyCoordinator status monitoring."""
    # Set up basic logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger = logging.getLogger("StatusMonitorTest")
    
    print("\n" + "=" * 80)
    print("STRATEGY COORDINATOR STATUS MONITOR TEST")
    print("=" * 80 + "\n")
    
    # Initialize LibreClient
    print("Initializing LibreClient...")
    client = LibreClient(api_url="https://testnet.libre.org", verbose=True)
    
    # Load strategies from config file
    try:
        with open('config/strategies.yaml', 'r') as f:
            strategies_config = yaml.safe_load(f)
            print(f"Loaded strategies config from file: {len(strategies_config)} strategies defined")
    except Exception as e:
        print(f"Error loading strategies config: {e}")
        strategies_config = {}
    
    # Create a coordinator configuration
    coordinator_config = {
        'account': 'dextester',
        'base_symbol': 'BTC',
        'quote_symbol': 'USDT',
        'strategies': {
            'MarketPriceTrackerStrategy': {
                'enabled': True,
                'update_interval_ms': 30000,
                'price_source': 'binance',
                'price_change_threshold': 0.005
            },
            'TradeSimulatorStrategy': {
                'enabled': True,
                'trades_per_cycle': 1,
                'cycle_interval_ms': 60000,
                'secondary_account': 'dextrader',
                'min_trade_amount': 0.001,
                'max_trade_amount': 0.01
            }
        }
    }
    
    # Display configuration
    print("\nTest configuration:")
    print(f"  Trading Pair: {coordinator_config['base_symbol']}/{coordinator_config['quote_symbol']}")
    print(f"  Account: {coordinator_config['account']}")
    print("  Strategies:")
    for strategy_name, config in coordinator_config['strategies'].items():
        print(f"    - {strategy_name}: {config}")
    
    try:
        # Create coordinator
        print("\nCreating StrategyCoordinator...")
        coordinator = StrategyCoordinator(client, coordinator_config)
        
        # Manually load strategies
        print("Manually loading strategies...")
        for strategy_name, strategy_config in coordinator_config['strategies'].items():
            if strategy_config.get('enabled', True):
                print(f"Loading {strategy_name}...")
                # Add the trading pair to the strategy config
                strategy_config['trading_pair'] = f"{coordinator_config['base_symbol']}/{coordinator_config['quote_symbol']}"
                strategy_config['account'] = coordinator_config['account']
                
                # Create and add the strategy
                coordinator.add_strategy(strategy_name, strategy_config)
        
        # Start coordinator
        print("Starting coordinator...")
        coordinator.start()
        print("Coordinator started successfully!")
        
        # Print status report
        print("\nInitial Status Report:")
        if hasattr(coordinator, 'print_status_report'):
            coordinator.print_status_report()
        else:
            print("Status report method not available")
        
        # Start status monitor with short interval
        if hasattr(coordinator, 'start_status_monitor'):
            print("\nStarting status monitor (5 second interval)...")
            coordinator.start_status_monitor(interval_seconds=5)
            print("Status monitor started. Running for 20 seconds...")
            
            # Run for a short time
            for i in range(4):
                time.sleep(5)
                print(f"\nStatus update {i+1}/4:")
                
            # Stop the status monitor
            coordinator.stop_status_monitor()
            print("Status monitor stopped.")
        else:
            print("Status monitor method not available")
        
        # Stop coordinator
        print("\nStopping coordinator...")
        coordinator.stop()
        print("Coordinator stopped successfully!")
        
        # Print final status report
        print("\nFinal Status Report:")
        if hasattr(coordinator, 'print_status_report'):
            coordinator.print_status_report()
        
    except Exception as e:
        print(f"Error during test: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
    
    print("\nTest completed.")

if __name__ == "__main__":
    main()
