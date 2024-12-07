from typing import Dict, Any
from decimal import Decimal, ROUND_DOWN
import random
from pylibre.strategies.templates.base_strategy import BaseStrategy
from pylibre.utils.shared_data import read_price

PRICE_FILE = "shared_data/btcusdt_price.json"

class MarketRateStrategy(BaseStrategy):
    """Strategy for placing orders close to market price."""
    
    def generate_signal(self) -> Dict[str, Any]:
        """Generate signal based on market price feed."""
        market_price = read_price(PRICE_FILE)
        if market_price is None:
            print("❌ Could not read market price")
            return None
            
        return {
            'price': Decimal(str(market_price)),
            'min_spread': self.config.get('min_spread_percentage', Decimal('0.001')),
            'max_spread': self.config.get('max_spread_percentage', Decimal('0.005'))
        }

    def place_orders(self, signal: Dict[str, Any]) -> bool:
        """Place a pair of orders around the market price."""
        if signal is None:
            return False
            
        try:
            base_price = signal['price']
            
            # Calculate available balance
            total_balance = self._get_available_balance()
            per_order_quantity = (total_balance / Decimal('4')).quantize(
                Decimal('0.00000001'), rounding=ROUND_DOWN
            )
            
            # Try up to 3 times to place both orders successfully
            max_attempts = 3
            for attempt in range(max_attempts):
                # Calculate random spreads within our range for buy and sell
                buy_spread = Decimal(str(random.uniform(
                    float(signal['min_spread']),
                    float(signal['max_spread'])
                )))
                sell_spread = Decimal(str(random.uniform(
                    float(signal['min_spread']),
                    float(signal['max_spread'])
                )))
                
                # Place one buy and one sell order
                buy_price = base_price * (Decimal('1') - buy_spread)
                sell_price = base_price * (Decimal('1') + sell_spread)
                
                # Add small random variations to quantity
                quantity = per_order_quantity * Decimal(str(random.uniform(0.95, 1.05)))
                quantity_str = f"{quantity:.8f}"
                
                success_buy = self._place_single_order("buy", quantity_str, buy_price, 0)
                success_sell = self._place_single_order("sell", quantity_str, sell_price, 1)
                
                if success_buy and success_sell:
                    return True
                    
                if attempt < max_attempts - 1:
                    print(f"⚠️ Retry attempt {attempt + 1}: Buy success: {success_buy}, Sell success: {success_sell}")
                    
            print("❌ Failed to place both orders after maximum attempts")
            return False
            
        except Exception as e:
            print(f"❌ Error placing market rate orders: {e}")
            return False

