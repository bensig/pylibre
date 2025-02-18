from pylibre import LibreClient
from pylibre.strategies import get_strategy_class
from pylibre.utils.logger import StrategyLogger, LogLevel
from pylibre.manager.config_manager import ConfigManager
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
            verbose=False
        )
        
        # Get strategy class
        strategy_class = get_strategy_class(args.strategy)
        if not strategy_class:
            logger.error(f"Strategy class not found: {args.strategy}")
            sys.exit(1)
            
        # Get strategy parameters from config manager
        pair = f"{args.base}/{args.quote}"
        parameters = config_manager.get_strategy_parameters(args.strategy, pair)
        if not parameters:
            logger.error(f"No parameters found for strategy {args.strategy} and pair {pair}")
            sys.exit(1)
            
        strategy = strategy_class(
            client=client,
            account=args.account,
            base_symbol=args.base,
            quote_symbol=args.quote,
            parameters=parameters,  # Pass the combined parameters here
            logger=logger
        )
        
        def handle_shutdown(signum, frame):
            logger.info("Received shutdown signal")
            strategy.cleanup()
            sys.exit(0)
            
        signal.signal(signal.SIGINT, handle_shutdown)
        signal.signal(signal.SIGTERM, handle_shutdown)
        
        logger.info(f"Starting {strategy_id}")
        strategy.run()
        
    except Exception as e:
        import traceback
        logger.error(f"Strategy error: {e}")
        logger.error(traceback.format_exc())
        if 'strategy' in locals():
            try:
                strategy.cleanup()
            except Exception as cleanup_error:
                logger.error(f"Cleanup error: {cleanup_error}")
        sys.exit(1)

if __name__ == "__main__":
    main() 