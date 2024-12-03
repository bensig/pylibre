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
        """
        Place bid and ask orders around the signal price.
        """
        try:
            current_price = signal['price']
            spread = signal['spread_percentage']
            
            # Calculate bid and ask prices
            bid_price = current_price * (Decimal('1') - spread/Decimal('2'))
            ask_price = current_price * (Decimal('1') + spread/Decimal('2'))
            
            print(f"\n📊 New price: {current_price:.10f} {self.quote_symbol}")
            print(f"Movement: {signal['movement_percentage']:+.3f}%")
            print(f"Bid: {bid_price:.10f} {self.quote_symbol}")
            print(f"Ask: {ask_price:.10f} {self.quote_symbol}")

            # Place bid
            quantity = self.config.get('quantity', '100.00000000')
            print(f"\n💸 Placing bid for {quantity} {self.base_symbol}")
            bid_result = self.dex.place_order(
                account=self.account,
                order_type="buy",
                quantity=quantity,
                price=f"{bid_price:.10f}",
                quote_symbol=self.quote_symbol,
                base_symbol=self.base_symbol
            )
            
            if not bid_result.get("success"):
                print(f"❌ Bid order failed: {bid_result.get('error', 'Unknown error')}")
                return False
            
            print(f"✅ Bid placed successfully: {bid_result['data']['transaction_id']}")
            
            # Place ask
            print(f"💰 Placing ask for {quantity} {self.base_symbol}")
            ask_result = self.dex.place_order(
                account=self.account,
                order_type="sell",
                quantity=quantity,
                price=f"{ask_price:.10f}",
                quote_symbol=self.quote_symbol,
                base_symbol=self.base_symbol
            )
            
            if not ask_result.get("success"):
                print(f"❌ Ask order failed: {ask_result.get('error', 'Unknown error')}")
                return False
            
            print(f"✅ Ask placed successfully: {ask_result['data']['transaction_id']}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error placing orders: {e}")
            return False

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
