#!/usr/bin/env python3
"""
Script to run the StrategyCoordinator, which manages multiple trading strategies
for a specific trading pair.
"""

import sys
import os
import argparse
import yaml
import logging.handlers
from datetime import datetime
import time
import signal
import threading
from decimal import Decimal

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
        print("Error loading config from {}: {}".format(config_path, e))
        return {}

def signal_handler(sig, frame):
    """Handle Ctrl+C and other signals to gracefully stop the coordinator."""
    global running
    print("\nStopping coordinator (this may take a moment)...")
    print("Please wait while strategies are being stopped...")
    running = False
    
    # Log termination signal
    logger = logging.getLogger("StrategyCoordinator")
    logger.warning(f"Received termination signal {sig}, shutting down gracefully")
    
    # Give the coordinator time to clean up
    for i in range(5, 0, -1):
        print(f"Shutting down in {i} seconds...")
        time.sleep(1)
    
    # Force exit if still running after timeout
    print("Coordinator shutdown complete")
    sys.exit(0)


class DryRunClient:
    """Mock client for dry run mode that logs actions instead of executing them."""
    
    def __init__(self, real_client):
        """Initialize with the real client to get account info."""
        self.real_client = real_client
        self.logger = logging.getLogger('DryRunClient')
        self.orders = []
        self.logger.info("DRY RUN MODE ENABLED - No orders will be placed")
    
    def __getattr__(self, name):
        """For any method not explicitly defined, log the call and return a mock result."""
        def method(*args, **kwargs):
            self.logger.info(f"DRY RUN: Would call {name} with args: {args} kwargs: {kwargs}")
            
            # For methods that would fetch data, pass through to the real client
            read_only_methods = [
                'get_account_balance', 'fetch_order_book', 'get_market_price',
                'get_ticker', 'get_trades', 'get_orders'
            ]
            
            if name in read_only_methods:
                return getattr(self.real_client, name)(*args, **kwargs)
            
            # For methods that would modify state, return mock results
            if name == 'place_order':
                order_id = f"dry_run_order_{len(self.orders) + 1}"
                account = args[0] if args else kwargs.get('account')
                base_symbol = args[1] if len(args) > 1 else kwargs.get('base_symbol')
                quote_symbol = args[2] if len(args) > 2 else kwargs.get('quote_symbol')
                price = args[3] if len(args) > 3 else kwargs.get('price')
                quantity = args[4] if len(args) > 4 else kwargs.get('quantity')
                order_type = args[5] if len(args) > 5 else kwargs.get('order_type')
                
                order = {
                    'order_id': order_id,
                    'account': account,
                    'base_symbol': base_symbol,
                    'quote_symbol': quote_symbol,
                    'price': float(price) if price else None,
                    'quantity': float(quantity) if quantity else None,
                    'order_type': order_type,
                    'status': 'simulated'
                }
                
                self.orders.append(order)
                self.logger.info(f"DRY RUN: Would place {order_type} order: {quantity} {base_symbol} at {price} {quote_symbol}")
                return {'order_id': order_id}
            
            elif name == 'cancel_order':
                order_id = args[0] if args else kwargs.get('order_id')
                self.logger.info(f"DRY RUN: Would cancel order {order_id}")
                return {'success': True}
            
            # Default mock response
            return {'success': True, 'dry_run': True}
        
        return method

def setup_logging(log_level=logging.INFO):
    """Configure logging with rotation to prevent large log files."""
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    
    # Get the root logger
    root_logger = logging.getLogger()
    # Clear any existing handlers to prevent duplicates
    root_logger.handlers = []
    root_logger.setLevel(logging.DEBUG)  # Capture all logs
    
    # Console handler - use provided log level
    console = logging.StreamHandler()
    console.setLevel(log_level)
    console_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console.setFormatter(console_format)
    root_logger.addHandler(console)
    
    # File handler with rotation - DEBUG level (detailed logs)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = f"{log_dir}/coordinator_{timestamp}.log"
    file_handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=10*1024*1024, backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    file_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_format)
    root_logger.addHandler(file_handler)
    
    # Configure library loggers to reduce noise
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    
    # Disable propagation for certain loggers to prevent duplicate logs
    strategy_logger = logging.getLogger('pylibre')
    strategy_logger.propagate = False
    
    # Add signal handlers
    signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # kill command
    
    return root_logger

def run_coordinator(args, config):
    """Run the strategy coordinator with the specified arguments."""
    # Get the trading pair key
    pair_key = f"{args.base}{args.quote}"
    
    # Get account based on role and trading pair
    account = args.account
    if account is None and pair_key in config.get('accounts', {}):
        account = config['accounts'][pair_key].get(args.role)
    
    # If still no account, use legacy account configuration
    if account is None:
        if args.role == 'liquidity_provider':
            account = config.get('accounts', {}).get('main')
        elif args.role == 'trade_simulator_1':
            account = config.get('accounts', {}).get('simulator_primary')
        elif args.role == 'trade_simulator_2':
            account = config.get('accounts', {}).get('simulator_secondary')
    
    # If still no account, use a default
    if account is None:
        print("Warning: No account specified in config, using 'default'")
        account = 'default'
    
    # Print configuration
    print("=" * 80)
    print(f"Strategy Coordinator for {args.base}/{args.quote} using account {account} as {args.role}")
    print("=" * 80 + "\n")
    
    # Load config.yaml for API endpoint and private keys
    config_file = os.path.join(os.path.dirname(args.config), 'config.yaml')
    try:
        with open(config_file, 'r') as f:
            api_config = yaml.safe_load(f)
    except Exception as e:
        print(f"Error loading config from {config_file}: {e}")
        return
    
    logger = logging.getLogger("run_coordinator")
    logger.debug(f"Loading config from: {config_file}")
    
    # Determine if we're using mainnet or testnet
    network = 'mainnet' if 'mainnet' in args.config else 'testnet'
    
    # Get API endpoint
    api_endpoint = config.get('api_endpoint')
    if api_endpoint is None:
        api_endpoint = api_config.get('networks', {}).get(network, {}).get('api_url')
    
    if api_endpoint is None:
        logger.error("Error: No API endpoint specified in config")
        return
    
    # Get private keys
    private_keys = api_config.get('networks', {}).get(network, {}).get('private_keys', {})
    if not private_keys:
        if args.dry_run:
            logger.warning("No private keys found in config, but continuing in dry run mode")
            # Create dummy private keys for dry run mode
            private_keys = {
                'jecashking': 'dummy_key_for_dry_run',
                'arb24': 'dummy_key_for_dry_run'
            }
        else:
            # Ask for private keys interactively
            print("No private keys found in config. Please enter them interactively:")
            private_keys = {}
            
            # Ask for the account private key that we need
            if account:
                print(f"Enter private key for account '{account}':")
                private_key = input("> ")
                if private_key:
                    private_keys[account] = private_key
                else:
                    logger.error("Error: No private key provided")
                    return
            else:
                logger.error("Error: No account specified")
                return
    
    logger.debug(f"Loaded private keys for accounts: {list(private_keys.keys())}")
    
    # Initialize client
    client = LibreClient(
        api_url=api_endpoint,
        verbose=True,
        network=network
    )
    
    # If dry run mode is enabled, wrap the client with the DryRunClient
    if args.dry_run:
        # For dry run mode, we need to manually set the private keys since we're bypassing the config loading
        if args.dry_run and not client.private_keys:
            client.private_keys = private_keys
        client = DryRunClient(client)
    
    logger.info(f"Initialized LibreClient with {len(private_keys)} accounts")
    logger.debug(f"Using API endpoint: {api_endpoint}")
    
    # Get trading pair configuration
    if pair_key not in config.get('trading_pairs', {}):
        logger.error(f"Error: Trading pair {pair_key} not found in config")
        logger.error(f"Available trading pairs: {list(config.get('trading_pairs', {}).keys())}")
        return
    
    pair_config = config['trading_pairs'][pair_key]
    logger.debug(f"Found pair config for {pair_key}: {pair_config.keys()}")
    
    # Create coordinator config
    coordinator_config = {
        'account': account,
        'base_symbol': args.base,
        'quote_symbol': args.quote,
        'strategies': []
    }
    
    # Add the dry_run parameter to all strategies
    if args.dry_run:
        logger.info("Adding dry_run flag to all strategy parameters")
    
    # Set the cancel behavior based on command line flag
    cancel_existing = args.cancel_all
    logger.info(f"Order cancellation mode: {'Cancel all existing orders' if cancel_existing else 'Only cancel outdated orders'}")
    
    # Add appropriate strategies based on role
    if args.role == 'liquidity_provider':
        # For liquidity provider, add MarketPriceTrackerStrategy, OrderBookMakerStrategy, and OrderBookAnimatorStrategy
        logger.debug(f"Checking price tracker: enabled={pair_config.get('price_tracker', {}).get('enabled', True)}")
        if pair_config.get('price_tracker', {}).get('enabled', True):
            price_tracker_params = pair_config.get('price_tracker', {}).copy()
            # Add dry_run flag if enabled
            if args.dry_run:
                price_tracker_params['dry_run'] = True
            coordinator_config['strategies'].append({
                'name': 'MarketPriceTrackerStrategy',
                'parameters': price_tracker_params
            })
            logger.debug(f"Added MarketPriceTrackerStrategy with parameters: {price_tracker_params}")
        
        logger.debug(f"Checking orderbook maker: enabled={pair_config.get('orderbook_maker', {}).get('enabled', True)}")
        if pair_config.get('orderbook_maker', {}).get('enabled', True):
            orderbook_maker_params = pair_config.get('orderbook_maker', {}).copy()
            # Add dry_run flag if enabled
            if args.dry_run:
                orderbook_maker_params['dry_run'] = True
            # Add cancel_existing flag
            orderbook_maker_params['cancel_existing'] = cancel_existing
            coordinator_config['strategies'].append({
                'name': 'OrderBookMakerStrategy',
                'parameters': orderbook_maker_params
            })
            logger.debug(f"Added OrderBookMakerStrategy with parameters: {orderbook_maker_params}")
        
        logger.debug(f"Checking animator: enabled={pair_config.get('animator', {}).get('enabled', True)}")
        if pair_config.get('animator', {}).get('enabled', True):
            animator_params = pair_config.get('animator', {}).copy()
            # Add dry_run flag if enabled
            if args.dry_run:
                animator_params['dry_run'] = True
            coordinator_config['strategies'].append({
                'name': 'OrderBookAnimatorStrategy',
                'parameters': animator_params
            })
            logger.debug(f"Added OrderBookAnimatorStrategy with parameters: {animator_params}")
    
    elif args.role.startswith('trade_simulator'):
        # For trade simulators, only add TradeSimulatorStrategy
        logger.debug(f"Checking simulator: enabled={pair_config.get('simulator', {}).get('enabled', True)}")
        if pair_config.get('simulator', {}).get('enabled', True):
            # Get the counterparty account (liquidity provider)
            counterparty_account = None
            if pair_key in config.get('accounts', {}):
                counterparty_account = config['accounts'][pair_key].get('liquidity_provider')
            
            # Create simulator parameters
            simulator_params = pair_config.get('simulator', {}).copy()
            
            # Add counterparty account if available
            if counterparty_account:
                simulator_params['counterparty_account'] = counterparty_account
            
            coordinator_config['strategies'].append({
                'name': 'TradeSimulatorStrategy',
                'parameters': simulator_params
            })
            logger.debug(f"Added TradeSimulatorStrategy with parameters: {simulator_params}")
    
    # Create coordinator
    coordinator = StrategyCoordinator(client, coordinator_config)
    
    # Add strategies to the coordinator
    for strategy_config in coordinator_config['strategies']:
        strategy_name = strategy_config['name']
        strategy_params = strategy_config['parameters']
        logger.info(f"Adding strategy {strategy_name} to coordinator")
        coordinator.add_strategy(strategy_name, strategy_params)
    
    # Start dashboard if requested
    if args.dashboard:
        from src.pylibre.monitoring.dashboard import start_dashboard
        dashboard_thread = threading.Thread(
            target=start_dashboard,
            args=(coordinator, args.dashboard_port),
            daemon=True
        )
        dashboard_thread.start()
        logger.info(f"Started dashboard on port {args.dashboard_port}")
    
    # Start the price tracker first if it exists
    if 'MarketPriceTrackerStrategy' in coordinator.strategies:
        logger.info("Starting MarketPriceTrackerStrategy first to establish price")
        price_tracker = coordinator.strategies['MarketPriceTrackerStrategy']
        price_tracker.running = True
        
        # Run the price tracker for a short time to establish the price
        price_fetch_success = False
        max_attempts = 3
        
        for attempt in range(1, max_attempts + 1):
            logger.info(f"Attempt {attempt}/{max_attempts} to fetch initial price")
            initial_price = price_tracker.fetch_current_price()
            
            if initial_price is not None and initial_price > Decimal('0'):
                price_fetch_success = True
                price_tracker.update_price(initial_price)
                logger.info(f"Initial price set to {initial_price} {args.quote}")
                break
            else:
                logger.error(f"Failed to fetch initial price on attempt {attempt}")
                if attempt < max_attempts:
                    logger.info(f"Waiting before retry...")
                    time.sleep(2)  # Wait 2 seconds before retrying
        
        if not price_fetch_success:
            # Use fallback price if fetch failed
            fallback_price = price_tracker.fixed_price
            logger.warning(f"Using fallback price after {max_attempts} failed attempts: {fallback_price} {args.quote}")
            initial_price = fallback_price
            price_tracker.update_price(initial_price)
        
        # Force update the price in all other strategies
        for strategy_type, strategy in coordinator.strategies.items():
            if strategy_type != 'MarketPriceTrackerStrategy' and hasattr(strategy, 'on_price_update'):
                logger.debug(f"Updating price for {strategy_type}")
                strategy.on_price_update(initial_price)
    
    # Start the coordinator and strategies in threads
    coordinator.start()
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # kill command
    
    # Keep the main thread running
    logger.info("Coordinator is running. Press Ctrl+C to exit.")
    try:
        # Main loop - keep running until interrupted
        global running
        while running:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    finally:
        # Stop the coordinator gracefully
        logger.info("Stopping coordinator...")
        coordinator.stop()
        logger.info("Coordinator stopped successfully")

def main():
    """Main function to run the strategy coordinator."""
    parser = argparse.ArgumentParser(description='Run the strategy coordinator')
    
    # Required arguments
    parser.add_argument('--base', required=True, help='Base symbol (e.g., LIBRE)')
    parser.add_argument('--quote', required=True, help='Quote symbol (e.g., BTC)')
    
    # Optional arguments
    parser.add_argument('--account', help='Account to use (overrides config)')
    parser.add_argument('--role', default='liquidity_provider', 
                        choices=['liquidity_provider', 'trade_simulator_1', 'trade_simulator_2'],
                        help='Role to run (liquidity_provider, trade_simulator_1, trade_simulator_2)')
    parser.add_argument('--config', default='config/strategies.yaml', help='Path to config file')
    parser.add_argument('--dashboard', action='store_true', help='Start the monitoring dashboard')
    parser.add_argument('--dashboard-port', type=int, default=5000, help='Port for the dashboard server')
    parser.add_argument('--dry-run', action='store_true', help='Simulate running without placing actual orders')
    parser.add_argument('--log-level', default='INFO', 
                        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                        help='Set logging level (default: INFO)')
    parser.add_argument('--cancel-all', action='store_true', 
                        help='Cancel all existing orders before placing new ones. If not set, only outdated orders will be cancelled.')
    
    args = parser.parse_args()
    
    # Setup enhanced logging with specified log level
    log_level = getattr(logging, args.log_level)
    logger = setup_logging(log_level=log_level)
    
    # Print banner
    print("\nStarting Strategy Coordinator Script - Enhanced Version\n")
    
    # Load configuration
    try:
        with open(args.config, 'r') as f:
            config = yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Error loading config from {args.config}: {e}")
        return
    
    # Run the coordinator
    run_coordinator(args, config)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting due to keyboard interrupt")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()