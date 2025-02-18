from pylibre.strategies import get_strategy_class
from pylibre.strategies.orderbook_filler import OrderBookFillerStrategy
from pylibre.utils.logger import StrategyLogger, LogLevel
from pylibre.manager.config_manager import ConfigManager
from pylibre.client import LibreClient
import argparse
import sys
import signal

def main():
    parser = argparse.ArgumentParser(description='Run a trading strategy')
    parser.add_argument('--account', required=True, help='Trading account name')
    parser.add_argument('--strategy', required=True, help='Strategy name')
    parser.add_argument('--base', default='LIBRE', help='Base asset symbol')
    parser.add_argument('--quote', default='BTC', help='Quote asset symbol')
    parser.add_argument('--config', default='config/config.yaml', help='Path to config file')
    args = parser.parse_args()

    # Create unique logger for this strategy instance
    strategy_id = f"{args.strategy}_{args.account}"
    try:
        logger = StrategyLogger(strategy_id, LogLevel.INFO)
        
        # Load config and check for private key
        config_manager = ConfigManager(args.config)
        network_config = config_manager.get_network_config('testnet')
        
        if args.account not in network_config.get('private_keys', {}):
            logger.error(f"No private key found for account {args.account} in network config")
            sys.exit(1)
            
        private_key = network_config['private_keys'][args.account]
        logger.info(f"Found private key for account {args.account}")
        
        # Initialize client with config
        client = LibreClient(
            network='testnet',
            config_path=args.config,
            verbose=True  # Enable verbose for debugging
        )
        
        # Get strategy class
        strategy_class = get_strategy_class(args.strategy)
        if not strategy_class:
            logger.error(f"Strategy class not found: {args.strategy}")
            sys.exit(1)
            
        # Get strategy parameters from config manager
        pair = f"{args.base}/{args.quote}"
        strategy_params = config_manager.get_strategy_parameters(args.strategy, pair)
        if not strategy_params:
            logger.error(f"No parameters found for strategy {args.strategy} and pair {pair}")
            sys.exit(1)
        
        # Create and run strategy
        if args.strategy == "OrderBookFillerStrategy":
            strategy = OrderBookFillerStrategy(
                client=client,
                account=args.account,
                base_symbol=args.base,
                quote_symbol=args.quote,
                logger=logger,
                min_spread_percentage=strategy_params.get('min_spread_percentage', 0.006),
                max_spread_percentage=strategy_params.get('max_spread_percentage', 0.01),
                num_orders=strategy_params.get('num_orders', 20)
            )
        else:
            strategy = strategy_class(
                client=client,
                account=args.account,
                base_symbol=args.base,
                quote_symbol=args.quote,
                parameters=strategy_params,
                logger=logger
            )
        
        def handle_interrupt(signum, frame):
            logger.info("Received interrupt signal, cleaning up...")
            strategy.cleanup()
            sys.exit(0)
            
        signal.signal(signal.SIGINT, handle_interrupt)
        strategy.run()
        
    except Exception as e:
        logger.error(f"Error running strategy: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()