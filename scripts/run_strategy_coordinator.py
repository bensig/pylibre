#!/usr/bin/env python3
"""
Script to run the StrategyCoordinator, which manages multiple trading strategies
for a specific trading pair.
"""

import sys
import os
import argparse
import yaml
import logging
import time
import signal

# Add the parent directory to the path so we can import the pylibre module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.pylibre import LibreClient
from src.pylibre.strategies import StrategyCoordinator
from src.pylibre.monitoring import start_dashboard, stop_dashboard
from src.pylibre.utils.logger import StrategyLogger, LogLevel

# Global variable to track if the coordinator is running
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
    """Handle Ctrl+C to gracefully stop the coordinator."""
    global running
    print("\nStopping coordinator (this may take a moment)...")
    print("Please wait while strategies are being stopped...")
    running = False

def main():
    """Main function to run the StrategyCoordinator."""
    print("\nStarting Strategy Coordinator Script - Enhanced Version")
    parser = argparse.ArgumentParser(description='Run the StrategyCoordinator')
    
    # Required arguments
    parser.add_argument('--account', required=True, help='Account for trading')
    parser.add_argument('--base', required=True, help='Base symbol (e.g., LIBRE)')
    parser.add_argument('--quote', required=True, help='Quote symbol (e.g., BTC)')
    
    # Optional arguments
    parser.add_argument('--config', default='config/strategies.yaml', help='Path to config file')
    parser.add_argument('--dashboard', action='store_true', help='Start the monitoring dashboard')
    parser.add_argument('--dashboard-port', type=int, default=5000, help='Port for the dashboard server')
    
    args = parser.parse_args()
    
    # Set up logging - StrategyLogger already configures handlers internally
    logger = StrategyLogger(f"Coordinator_{args.account}", level=LogLevel.INFO)
    
    # Print banner
    print("\n" + "=" * 80)
    print(f"Strategy Coordinator for {args.base}/{args.quote} using account {args.account}")
    print("=" * 80 + "\n")
    logger.info(f"Starting StrategyCoordinator for {args.base}/{args.quote}")
    
    # Load configuration
    config = load_config(args.config)
    
    # Get API endpoint from config
    api_endpoint = config.get('api_endpoint', 'https://testnet.libre.org')
    
    # Initialize LibreClient
    client = LibreClient(api_url=api_endpoint, verbose=True)
    
    # Create coordinator configuration
    coordinator_config = {
        'account': args.account,
        'base_symbol': args.base,
        'quote_symbol': args.quote,
        'strategies': {}
    }
    
    # Get trading pair specific configuration
    pair_key = f"{args.base}{args.quote}"
    pair_config = config.get('trading_pairs', {}).get(pair_key, {})
    
    # Add strategies from pair config
    if pair_config:
        logger.info(f"Found configuration for trading pair {pair_key}")
        
        # Add MarketPriceTrackerStrategy if configured
        if 'price_tracker' in pair_config:
            logger.info("Adding MarketPriceTrackerStrategy")
            coordinator_config['strategies']['MarketPriceTrackerStrategy'] = pair_config['price_tracker']
            # Ensure the price_source is correctly set (not 'source')
            if 'source' in coordinator_config['strategies']['MarketPriceTrackerStrategy']:
                coordinator_config['strategies']['MarketPriceTrackerStrategy']['price_source'] = \
                    coordinator_config['strategies']['MarketPriceTrackerStrategy'].pop('source')
        
        # Add OrderBookMakerStrategy if configured
        if 'market_maker' in pair_config:
            logger.info("Adding OrderBookMakerStrategy")
            coordinator_config['strategies']['OrderBookMakerStrategy'] = pair_config['market_maker']
        
        # Add OrderBookAnimatorStrategy if configured
        if 'animator' in pair_config:
            logger.info("Adding OrderBookAnimatorStrategy")
            coordinator_config['strategies']['OrderBookAnimatorStrategy'] = pair_config['animator']
            
        # Add TradeSimulatorStrategy if configured
        if 'simulator' in pair_config:
            logger.info("Adding TradeSimulatorStrategy")
            coordinator_config['strategies']['TradeSimulatorStrategy'] = pair_config['simulator']
    else:
        logger.warning(f"No configuration found for trading pair {pair_key}")
        
        # Set default configurations
        coordinator_config['strategies']['MarketPriceTrackerStrategy'] = {
            'enabled': True,
            'update_interval_ms': 30000,
            'price_source': 'binance',
            'price_change_threshold': 0.005
        }
        
        coordinator_config['strategies']['OrderBookMakerStrategy'] = {
            'enabled': True,
            'num_orders': 30,
            'min_spread_percentage': 0.01,
            'max_spread_percentage': 0.05,
            'quantity_distribution': 'random',
            'update_interval_ms': 60000
        }
    
    # Start the dashboard if requested
    dashboard = None
    if args.dashboard:
        logger.info(f"Starting monitoring dashboard on port {args.dashboard_port}")
        dashboard = start_dashboard(port=args.dashboard_port)
    
    # Display configured strategies
    logger.info("Configured strategies:")
    for strategy_name, strategy_config in coordinator_config['strategies'].items():
        if strategy_config.get('enabled', True):
            logger.info(f"  - {strategy_name}: ENABLED")
            # Display key parameters for each strategy
            if strategy_name == 'MarketPriceTrackerStrategy':
                logger.info(f"    Price Source: {strategy_config.get('price_source', 'default')}")
                logger.info(f"    Update Interval: {strategy_config.get('update_interval_ms', 'default')}ms")
            elif strategy_name == 'OrderBookMakerStrategy':
                logger.info(f"    Orders: {strategy_config.get('num_orders', 'default')}")
                logger.info(f"    Spread: {strategy_config.get('min_spread_percentage', 'default')} - {strategy_config.get('max_spread_percentage', 'default')}")
            elif strategy_name == 'TradeSimulatorStrategy':
                logger.info(f"    Trades Per Cycle: {strategy_config.get('trades_per_cycle', 'default')}")
                logger.info(f"    Secondary Account: {strategy_config.get('secondary_account', args.account)}")
        else:
            logger.info(f"  - {strategy_name}: DISABLED")
    
    # Create and start the coordinator
    try:
        # Register signal handler for Ctrl+C
        signal.signal(signal.SIGINT, signal_handler)
        
        # Create coordinator
        logger.info(f"Creating StrategyCoordinator for {args.base}/{args.quote} using account {args.account}")
        coordinator = StrategyCoordinator(client, coordinator_config, logger)
        
        # Start coordinator
        logger.info("Starting coordinator and all enabled strategies...")
        coordinator.start()
        logger.info("Coordinator started successfully!")
        
        # Print detailed initial status report
        if hasattr(coordinator, 'print_status_report'):
            logger.info("\nInitial Status Report:")
            coordinator.print_status_report()
        else:
            # Fallback to basic status display
            logger.info("\nInitial Strategy Status:")
            logger.info("-" * 50)
            for strategy_name in coordinator_config['strategies']:
                if coordinator_config['strategies'][strategy_name].get('enabled', True):
                    if hasattr(coordinator, 'strategy_statuses') and strategy_name in coordinator.strategy_statuses:
                        status = coordinator.strategy_statuses[strategy_name].get('status', 'unknown')
                        logger.info(f"  {strategy_name}: {status.upper()}")
                    else:
                        logger.info(f"  {strategy_name}: UNKNOWN")
            logger.info("-" * 50)
        
        # Keep the main thread alive with periodic status updates
        status_interval = 60  # Print status every minute
        last_status_print = time.time()
        
        logger.info("Coordinator is running. Press Ctrl+C to stop.")
        while running and coordinator.is_running():
            current_time = time.time()
            
            # Print periodic status updates
            if current_time - last_status_print >= status_interval:
                logger.info("\nPeriodic Status Update:")
                
                # Use enhanced status reporting if available
                if hasattr(coordinator, 'print_status_report'):
                    coordinator.print_status_report()
                # Fallback to basic status display
                elif hasattr(coordinator, 'strategy_statuses'):
                    logger.info("-" * 50)
                    for strategy_name, status_data in coordinator.strategy_statuses.items():
                        status = status_data.get('status', 'unknown')
                        cycles = status_data.get('cycles_completed', 0)
                        errors = status_data.get('errors', 0)
                        logger.info(f"  {strategy_name}: {status.upper()}, Cycles: {cycles}, Errors: {errors}")
                    logger.info("-" * 50)
                else:
                    logger.info("  No status information available")
                
                last_status_print = current_time
                
            time.sleep(1)
            
    except Exception as e:
        logger.error(f"Error running coordinator: {e}")
    finally:
        # Stop the coordinator
        if 'coordinator' in locals():
            logger.info("Stopping coordinator and all strategies...")
            coordinator.stop()
            logger.info("All strategies have been stopped")
        
        # Stop the dashboard if it was started
        if dashboard:
            logger.info("Stopping dashboard...")
            stop_dashboard()
        
        # Print final status report
        logger.info("\nFinal Status Report:")
        if hasattr(coordinator, 'get_status_report'):
            # Get the status report data
            report = coordinator.get_status_report()
            
            # Print summary information
            logger.info("-" * 50)
            logger.info(f"Trading Pair: {args.base}/{args.quote}")
            logger.info(f"Account: {args.account}")
            
            # Calculate total runtime
            if 'coordinator' in report and 'runtime_seconds' in report['coordinator']:
                runtime = report['coordinator']['runtime_seconds']
                hours, remainder = divmod(runtime, 3600)
                minutes, seconds = divmod(remainder, 60)
                runtime_str = f"{int(hours)}h {int(minutes)}m {int(seconds)}s"
                logger.info(f"Total Runtime: {runtime_str}")
            
            # Print strategy summary
            if 'strategies' in report:
                strategies_list = list(report['strategies'].keys())
                logger.info(f"Strategies: {', '.join(strategies_list)}")
                
                # Print cycles and errors summary
                total_cycles = sum(s.get('cycles_completed', 0) for s in report['strategies'].values())
                total_errors = sum(s.get('errors', 0) for s in report['strategies'].values())
                logger.info(f"Total Cycles: {total_cycles}")
                logger.info(f"Total Errors: {total_errors}")
        else:
            # Fallback to basic summary
            logger.info("-" * 50)
            logger.info(f"Trading Pair: {args.base}/{args.quote}")
            logger.info(f"Account: {args.account}")
            enabled_strategies = [s for s, c in coordinator_config['strategies'].items() if c.get('enabled', True)]
            logger.info(f"Strategies: {', '.join(enabled_strategies)}")
            
        logger.info("-" * 50)
        logger.info("Coordinator stopped successfully")

if __name__ == "__main__":
    main() 