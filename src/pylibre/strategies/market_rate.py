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
        """
        Place bid and ask orders around the market price.
        """
        if signal is None:
            return False
            
        try:
            current_price = signal['price']
            spread = signal['spread_percentage']
            
            # Calculate bid and ask prices
            bid_price = current_price * (Decimal('1') - spread/Decimal('2'))
            ask_price = current_price * (Decimal('1') + spread/Decimal('2'))
            
            print(f"\n📊 Market Price: {current_price:.10f}")
            print(f"🔽 Bid Price: {bid_price:.10f}")
            print(f"🔼 Ask Price: {ask_price:.10f}")

            # Place bid
            quantity = self.config.get('quantity', '1.00000000')
            bid_result = self.dex.place_order(
                account=self.account,
                order_type="buy",
                quote_symbol=self.quote_symbol,
                base_symbol=self.base_symbol,
                price=f"{bid_price:.10f}",
                quantity=quantity
            )
            
            if not bid_result.get("success"):
                print(f"❌ Bid order failed: {bid_result.get('error', 'Unknown error')}")
                return False
                
            # Place ask
            ask_result = self.dex.place_order(
                account=self.account,
                order_type="sell",
                quote_symbol=self.quote_symbol,
                base_symbol=self.base_symbol,
                price=f"{ask_price:.10f}",
                quantity=quantity
            )
            
            if not ask_result.get("success"):
                print(f"❌ Ask order failed: {ask_result.get('error', 'Unknown error')}")
                return False
                
            return True
            
        except Exception as e:
            print(f"❌ Error placing orders: {str(e)}")
            return False

