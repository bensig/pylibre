from typing import Dict, Any
from decimal import Decimal
import random
import time
from pylibre.strategies.templates.base_strategy import BaseStrategy
from pylibre.utils.shared_data import read_price

PRICE_FILE = "shared_data/btcusdt_price.json"

class OrderBookMakerStrategy(BaseStrategy):
    """Strategy responsible for maintaining the order book depth."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.orderbook_filled = False
    
    def generate_signal(self) -> Dict[str, Any]:
        """Generate signal based on market price feed."""
        market_price = read_price(PRICE_FILE)
        if market_price is None:
            print("❌ Could not read market price")
            return None
        
        # Get min and max spreads from config and convert to Decimal
        min_spread = Decimal(str(self.config.get('min_spread_percentage', '0.006')))
        max_spread = Decimal(str(self.config.get('max_spread_percentage', '0.01')))
            
        return {
            'price': Decimal(str(market_price)),
            'min_spread': min_spread,
            'max_spread': max_spread
        }

    def place_orders(self, signal: Dict[str, Any]) -> bool:
        """Place orders using distributed order placement."""
        if signal is None:
            return False
        
        if not self.orderbook_filled:
            # Initial filling of the order book
            success = self.place_distributed_orders(
                base_price=signal['price'],
                min_spread=signal['min_spread'],
                max_spread=signal['max_spread']
            )
            if success:
                self.orderbook_filled = True
                print("📚 Order book initially filled")
            return success
        else:
            # Maintain order book with random cancellations and new orders
            return self.maintain_orderbook(signal)

    def maintain_orderbook(self, signal: Dict[str, Any]) -> bool:
        """Randomly cancel orders and place new ones."""
        try:
            # Cancel 1-2 random orders
            order_book = self.dex.fetch_order_book(
                quote_symbol=self.quote_symbol,
                base_symbol=self.base_symbol
            )
            
            our_orders = (
                [order for order in order_book["bids"] if order["account"] == self.account] +
                [order for order in order_book["offers"] if order["account"] == self.account]
            )
            
            if our_orders:
                # Randomly cancel 1-2 orders
                num_to_cancel = random.randint(1, 2)
                orders_to_cancel = random.sample(our_orders, min(num_to_cancel, len(our_orders)))
                
                for order in orders_to_cancel:
                    self.dex.cancel_order(
                        account=self.account,
                        order_id=order['identifier'],
                        quote_symbol=self.quote_symbol,
                        base_symbol=self.base_symbol
                    )
                    print(f"🗑️  Cancelled order at price {order['price']}")
                    time.sleep(random.uniform(0.5, 1.0))
                
                # Place replacement orders
                for _ in range(len(orders_to_cancel)):
                    # Calculate random spread within our range
                    spread = Decimal(str(random.uniform(
                        float(signal['min_spread']),
                        float(signal['max_spread'])
                    )))
                    
                    # Randomly choose buy or sell
                    order_type = random.choice(['buy', 'sell'])
                    direction = Decimal('-1') if order_type == 'buy' else Decimal('1')
                    
                    # Calculate price
                    price = signal['price'] * (Decimal('1') + (direction * spread))
                    
                    # Calculate quantity
                    total_balance = self._get_available_balance()
                    quantity = (total_balance / Decimal('20')).quantize(
                        Decimal('0.00000001'), rounding=ROUND_DOWN
                    )
                    # Add small random variation to quantity (±5%)
                    quantity = quantity * Decimal(str(random.uniform(0.95, 1.05)))
                    quantity_str = f"{quantity:.8f}"
                    
                    success = self._place_single_order(order_type, quantity_str, price, 0)
                    if success:
                        print(f"📝 Placed new {order_type} order at {price:.8f}")
                    
                    time.sleep(random.uniform(0.5, 1.0))
            
            return True
            
        except Exception as e:
            print(f"❌ Error maintaining order book: {e}")
            return False