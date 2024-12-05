import sys
from pathlib import Path
# Add the project root directory to Python path
sys.path.append(str(Path(__file__).parent.parent))

import time
from src.pylibre.utils.binance_api import fetch_btc_usdt_price
from src.pylibre.utils.shared_data import write_price
import logging
from typing import Optional

PRICE_FILE = "shared_data/btcusdt_price.json"  # Path to the shared file

def fetch_and_store_prices(api_key: Optional[str] = None) -> None:
    """Continuously fetch and store the BTC/USDT price."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    while True:
        try:
            price = fetch_btc_usdt_price()
            if price is not None:
                logging.info(f"Fetched BTC/USDT price: {price}")
                write_price(PRICE_FILE, price)
            else:
                logging.warning("Received None price from API")
        except Exception as e:
            logging.error(f"Error fetching/storing price: {str(e)}")
        
        time.sleep(2)

if __name__ == "__main__":
    fetch_and_store_prices()
