from pylibre import LibreClient
from pylibre.strategies.random_walk import RandomWalkStrategy
from pylibre.strategies.market_rate import MarketRateStrategy
from pylibre.strategies.orderbook_maker import OrderBookMakerStrategy
from pylibre.utils.logger import StrategyLogger, LogLevel
from decimal import Decimal, ROUND_DOWN
import argparse
import sys
import signal

def get_strategy_class(strategy_name: str):
    """Get the strategy class based on the strategy name."""
    strategies = {
        'RandomWalkStrategy': RandomWalkStrategy,
        'MarketRateStrategy': MarketRateStrategy,
        'OrderBookMakerStrategy': OrderBookMakerStrategy
    }
    return strategies.get(strategy_name)

def main():
    parser = argparse.ArgumentParser(description='Run a trading strategy')
    parser.add_argument('--account', required=True, help='Trading account name')
    parser.add_argument('--strategy', required=True, help='Strategy name')
    parser.add_argument('--base', default='LIBRE', help='Base asset symbol')
    parser.add_argument('--quote', default='BTC', help='Quote asset symbol')
    args = parser.parse_args()

    # Create unique logger for this strategy instance
    strategy_id = f"{args.strategy}_{args.account}"
    try:
        logger = StrategyLogger(strategy_id, LogLevel.INFO)
        
        # Initialize client with verbose=False
        client = LibreClient(verbose=False)
        
        # Get strategy class
        strategy_class = get_strategy_class(args.strategy)
        if not strategy_class:
            logger.error(f"Strategy class not found: {args.strategy}")
            sys.exit(1)
            
        strategy = strategy_class(
            client=client,
            account=args.account,
            base_symbol=args.base,
            quote_symbol=args.quote,
            config={},
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