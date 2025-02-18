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
        market_price = self.get_market_price()
        if market_price is None:
            return None
            
        # Get spread parameters with larger default values
        min_spread = self.parameters.get('min_spread_percentage', Decimal('0.01'))  # Default 1%
        max_spread = self.parameters.get('max_spread_percentage', Decimal('0.05'))  # Default 5%
        
        self.logger.info(f"Market price: {market_price}, Spreads: {min_spread} to {max_spread}")
            
        return {
            'price': market_price,
            'min_spread': min_spread,
            'max_spread': max_spread
        }

    def check_balance(self):
        """Check and log the balance for both base and quote assets."""
        return super().check_balance()

    def run(self):
        """Run the strategy."""
        self.check_balance()
        signal = self.generate_signal()
        if signal is not None:
            self.place_orders(signal)

    def place_orders(self, signal: Dict[str, Any]) -> bool:
        """Place a pair of orders around the market price."""
        if signal is None:
            self.logger.error("No valid signal received")
            return False
            
        try:
            base_price = signal['price']
            min_spread = signal['min_spread']
            max_spread = signal['max_spread']
            
            # Calculate available balance
            total_balance = self._get_available_balance()
            per_order_quantity = (total_balance / Decimal('4')).quantize(
                Decimal('0.00000001'), rounding=ROUND_DOWN
            )
            
            # Calculate random spreads within our range for buy and sell
            buy_spread = Decimal(str(random.uniform(
                float(min_spread),
                float(max_spread)
            )))
            sell_spread = Decimal(str(random.uniform(
                float(min_spread),
                float(max_spread)
            )))
            
            # Calculate prices with spreads
            buy_price = base_price * (Decimal('1') - buy_spread)
            sell_price = base_price * (Decimal('1') + sell_spread)
            
            # Add small random variations to quantity
            quantity = per_order_quantity * Decimal(str(random.uniform(0.95, 1.05)))
            quantity_str = f"{quantity:.8f}"
            
            self.logger.info(f"Placing orders with base price: {base_price}, spreads: {min_spread}-{max_spread}")
            self.logger.info(
                f"Placing orders: Market={base_price}, "
                f"Buy={buy_price} (-{buy_spread:.2%}), "
                f"Sell={sell_price} (+{sell_spread:.2%})"
            )
            
            success_buy = self._place_single_order("buy", quantity_str, buy_price, 0)
            success_sell = self._place_single_order("sell", quantity_str, sell_price, 1)
            
            return success_buy and success_sell
            
        except Exception as e:
            self.logger.error(f"Error placing market rate orders: {e}")
            return False

    def _get_available_balance(self) -> Decimal:
        """Get available balance for trading."""
        return self.get_currency_balance(self.base_symbol)
