from typing import Dict, Any
from decimal import Decimal
from pathlib import Path
from pylibre.strategies.templates.base_strategy import BaseStrategy
from pylibre.utils.shared_data import read_price

PRICE_FILE = "shared_data/btcusdt_price.json"

class MarketRateStrategy(BaseStrategy):
    def generate_signal(self) -> Dict[str, Any]:
        """
        Generate signal based on market price feed.
        """
        market_price = read_price(PRICE_FILE)
        if market_price is None:
            print("❌ Could not read market price")
            return None
            
        return {
            'price': Decimal(str(market_price)),
            'spread_percentage': self.config['spread_percentage']
        }

    def place_orders(self, signal: Dict[str, Any]) -> bool:
        """Place orders using base class distributed order placement."""
        if signal is None:
            return False
        
        return self.place_distributed_orders(
            base_price=signal['price'],
            spread=signal['spread_percentage']
        )

