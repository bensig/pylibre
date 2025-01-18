import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import asyncio
import logging
import argparse
from typing import Dict
from decimal import Decimal
import yaml

from src.pylibre.price_feed import PriceFeedFactory
from src.pylibre.utils.shared_data import write_price

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def load_price_sources(config_path="config/config.yaml"):
    """Load price source configurations from config file."""
    with open(config_path) as f:
        config = yaml.safe_load(f)
    
    price_sources = {}
    
    # Check for global price sources
    if "price_sources" in config:
        price_sources.update(config["price_sources"])
    
    # Also check strategy groups for additional price sources
    for group in config["strategy_groups"].values():
        if "price_sources" in group:
            for pair, source_config in group["price_sources"].items():
                if pair not in price_sources:
                    price_sources[pair] = source_config
    
    if not price_sources:
        logging.warning("No price sources found in config file")
        # Add default Binance BTC/USDT price source
        price_sources["BTC/USDT"] = {
            "source": "binance",
            "symbol": "BTCUSDT"
        }
    
    return price_sources

async def fetch_and_store_prices(config_path: str) -> None:
    """Continuously fetch and store prices for all configured pairs."""
    price_sources = load_price_sources(config_path)
    feed_instances = {}
    
    if not price_sources:
        logging.error("No price sources configured in config file")
        return
    
    # Initialize price feed instances
    for pair, config in price_sources.items():
        try:
            feed = PriceFeedFactory.create_price_source(config)
            await feed.start()
            feed_instances[pair] = feed
            logging.info(f"Initialized price feed for {pair} using {config['source']} source")
        except Exception as e:
            logging.error(f"Failed to initialize price feed for {pair}: {e}")
    
    try:
        while True:
            for pair, feed in feed_instances.items():
                try:
                    price = await feed.get_price()
                    if price is not None:
                        filename = f"shared_data/{pair.lower().replace('/', '')}_price.json"
                        write_price(filename, float(price))
                        # Format price based on quote currency
                        quote_currency = pair.split('/')[1]
                        if quote_currency == "BTC":
                            formatted_price = f"{price:.8f}"  # 8 decimal places for BTC pairs
                        else:
                            formatted_price = f"{price:.2f}"  # 2 decimal places for USDT pairs
                        logging.info(f"{pair} price: {formatted_price}")
                except Exception as e:
                    logging.error(f"Error fetching/storing {pair} price: {e}")
            
            await asyncio.sleep(2)
    finally:
        # Cleanup
        for feed in feed_instances.values():
            await feed.stop()

def main():
    parser = argparse.ArgumentParser(description='Fetch and store prices from configured sources')
    parser.add_argument('--config', default='config/config.yaml', help='Path to config file')
    parser.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                      help='Set the logging level')
    args = parser.parse_args()
    
    logging.getLogger().setLevel(args.log_level)
    
    try:
        asyncio.run(fetch_and_store_prices(args.config))
    except KeyboardInterrupt:
        logging.info("Shutting down price fetcher")
    except Exception as e:
        logging.error(f"Error running price fetcher: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
