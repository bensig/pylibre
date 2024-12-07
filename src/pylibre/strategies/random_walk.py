import random
from typing import Dict, Any
from decimal import Decimal
from pylibre.strategies.templates.base_strategy import BaseStrategy

class RandomWalkStrategy(BaseStrategy):
    def generate_signal(self) -> Dict[str, Any]:
        """
        Generate a random walk price signal.
        """
        direction = Decimal(str(random.choice([-1, 1])))
        price_change_percentage = Decimal(str(random.uniform(
            float(self.config['min_change_percentage']),
            float(self.config['max_change_percentage'])
        )))
        
        current_price = self.config['current_price']
        new_price = current_price * (Decimal('1') + (direction * price_change_percentage))
        
        # Update the current price in config
        self.config['current_price'] = new_price
        
        return {
            'price': new_price,
            'movement_percentage': direction * price_change_percentage * Decimal('100'),
            'spread_percentage': self.config['spread_percentage']
        }

    def place_orders(self, signal: Dict[str, Any]) -> bool:
        """Place orders using base class distributed order placement."""
        spread = signal['spread_percentage']
        return self.place_distributed_orders(
            base_price=signal['price'],
            min_spread=spread,
            max_spread=spread
        )

    def cancel_orders(self) -> bool:
        """
        Cancel existing orders for this account.
        """
        try:
            # Fetch current orders
            order_book = self.dex.fetch_order_book(
                quote_symbol=self.quote_symbol,
                base_symbol=self.base_symbol
            )
            
            # Find our orders
            our_bids = [order for order in order_book["bids"] 
                       if order["account"] == self.account]
            our_offers = [order for order in order_book["offers"] 
                         if order["account"] == self.account]
            
            # Cancel bids
            for bid in our_bids:
                result = self.dex.cancel_order(
                    account=self.account,
                    order_id=bid["identifier"],
                    quote_symbol=self.quote_symbol,
                    base_symbol=self.base_symbol
                )
                if not result.get("success"):
                    print(f"❌ Failed to cancel bid {bid['identifier']}")
                    return False
            
            # Cancel offers
            for offer in our_offers:
                result = self.dex.cancel_order(
                    account=self.account,
                    order_id=offer["identifier"],
                    quote_symbol=self.quote_symbol,
                    base_symbol=self.base_symbol
                )
                if not result.get("success"):
                    print(f"❌ Failed to cancel offer {offer['identifier']}")
                    return False
            
            return True
            
        except Exception as e:
            print(f"Error cancelling orders: {e}")
            return False
