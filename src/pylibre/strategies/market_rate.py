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
        Place multiple bid and ask orders around the market price.
        """
        if signal is None:
            return False
            
        try:
            current_price = signal['price']
            spread = signal['spread_percentage']
            num_orders = self.config.get('num_orders', 1)
            spacing = self.config.get('order_spacing', 'linear')
            
            # Calculate base spread range
            base_spread = spread / Decimal('2')
            max_spread = self.config.get('max_change_percentage', spread * Decimal('2'))
            
            # Calculate order quantities
            total_quantity = Decimal(self.config.get('quantity', '1.00000000'))
            if self.config.get('quantity_distribution', 'equal') == 'equal':
                quantities = [total_quantity / num_orders] * num_orders
            
            # Calculate spread step for multiple orders
            spread_step = (max_spread - base_spread) / num_orders
            
            print(f"\n📊 Market Price: {current_price:.10f}")
            
            # Place multiple orders with increasing spreads
            for i in range(num_orders):
                if spacing == 'linear':
                    current_spread = base_spread + (spread_step * i)
                    bid_price = current_price * (Decimal('1') - current_spread)
                    ask_price = current_price * (Decimal('1') + current_spread)
                
                quantity = str(quantities[i])
                
                print(f"🔽 Placing bid #{i+1} at {bid_price:.10f}")
                bid_result = self.dex.place_order(
                    account=self.account,
                    order_type="buy",
                    quote_symbol=self.quote_symbol,
                    base_symbol=self.base_symbol,
                    price=f"{bid_price:.10f}",
                    quantity=quantity
                )
                
                if not bid_result.get("success"):
                    print(f"❌ Bid order #{i+1} failed: {bid_result.get('error', 'Unknown error')}")
                    continue
                    
                print(f"🔼 Placing ask #{i+1} at {ask_price:.10f}")
                ask_result = self.dex.place_order(
                    account=self.account,
                    order_type="sell",
                    quote_symbol=self.quote_symbol,
                    base_symbol=self.base_symbol,
                    price=f"{ask_price:.10f}",
                    quantity=quantity
                )
                
                if not ask_result.get("success"):
                    print(f"❌ Ask order #{i+1} failed: {ask_result.get('error', 'Unknown error')}")
                    continue
                
            return True
            
        except Exception as e:
            print(f"❌ Error placing orders: {str(e)}")
            return False

