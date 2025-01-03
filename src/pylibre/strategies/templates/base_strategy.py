from abc import ABC, abstractmethod
from typing import Dict, Any
from pylibre import LibreClient
from pylibre.dex import DexClient
import random
import time
from decimal import Decimal, ROUND_DOWN

class BaseStrategy(ABC):
    def __init__(self, 
                 client: LibreClient,
                 account: str,
                 quote_symbol: str,
                 base_symbol: str,
                 config: Dict[str, Any]):
        """
        Initialize the base strategy.
        
        Args:
            client: LibreClient instance for blockchain interaction
            account: Trading account name
            quote_symbol: Base asset symbol (e.g., 'BTC')
            base_symbol: Quote asset symbol (e.g., 'LIBRE')
            config: Strategy-specific configuration parameters
        """
        self.client = client
        self.dex = DexClient(client)
        self.account = account
        self.quote_symbol = quote_symbol
        self.base_symbol = base_symbol
        self.config = config
        self.is_running = False

    @abstractmethod
    def generate_signal(self) -> Dict[str, Any]:
        """
        Generate trading signals based on strategy logic.
        
        Returns:
            Dict containing signal information (e.g., price, direction, size)
        """
        pass

    @abstractmethod
    def place_orders(self, signal: Dict[str, Any]) -> bool:
        """
        Place orders based on the generated signal.
        
        Args:
            signal: The trading signal from generate_signal()
            
        Returns:
            bool: Success status of order placement
        """
        pass

    def cancel_orders(self) -> bool:
        """
        Cancel all existing orders for the account.
        
        Returns:
            bool: Success status of cancellation
        """
        try:
            order_book = self.dex.fetch_order_book(
                quote_symbol=self.quote_symbol,
                base_symbol=self.base_symbol
            )
            
            # Cancel bids
            for bid in order_book["bids"]:
                if bid["account"] == self.account:
                    self.dex.cancel_order(
                        account=self.account,
                        order_id=bid['identifier'],
                        quote_symbol=self.quote_symbol,
                        base_symbol=self.base_symbol
                    )
            
            # Cancel offers
            for offer in order_book["offers"]:
                if offer["account"] == self.account:
                    self.dex.cancel_order(
                        account=self.account,
                        order_id=offer['identifier'],
                        quote_symbol=self.quote_symbol,
                        base_symbol=self.base_symbol
                    )
            
            return True
        except Exception as e:
            print(f"Error cancelling orders: {e}")
            return False

    def run(self) -> None:
        """
        Main strategy execution loop.
        """
        self.is_running = True
        print(f"🚀 Starting {self.__class__.__name__} for {self.base_symbol}/{self.quote_symbol}")
        
        try:
            # Initial order placement to fill the book
            signal = self.generate_signal()
            self.place_orders(signal)
            
            while self.is_running:
                # Generate trading signal
                signal = self.generate_signal()
                
                # Randomly select and cancel 1-2 orders
                self.cancel_random_orders()
                
                # Place new orders to replace cancelled ones
                self.place_replacement_orders(signal)
                
                # Wait for next iteration
                time.sleep(self.config.get('interval', 5))
                
        except KeyboardInterrupt:
            print("\n\n🛑 Strategy stopped by user")
        finally:
            self.cleanup()

    def cleanup(self) -> None:
        """Clean up by cancelling any open orders."""
        try:
            print("🧹 Cleaning up...")
            order_book = self.dex.fetch_order_book(
                quote_symbol=self.quote_symbol,
                base_symbol=self.base_symbol
            )
            
            if not order_book:
                return
            
            # Find our orders
            our_orders = (
                [order for order in order_book["bids"] if order["account"] == self.account] +
                [order for order in order_book["offers"] if order["account"] == self.account]
            )
            
            if our_orders:
                print(f"Cancelling {len(our_orders)} remaining orders...")
                
                for order in our_orders:
                    self.dex.cancel_order(
                        account=self.account,
                        order_id=order["identifier"],
                        quote_symbol=self.quote_symbol,
                        base_symbol=self.base_symbol
                    )
                
                print("✅ Cleanup complete")
            else:
                print("✨ No orders to clean up")
                
        except KeyboardInterrupt:
            print("\n⚠️ Cleanup interrupted")
        except Exception as e:
            print(f"⚠️ Cleanup error: {e}")

    def place_distributed_orders(self, base_price: Decimal, min_spread: Decimal, max_spread: Decimal) -> bool:
        """
        Place multiple orders with configurable distribution and spacing.
        """
        try:
            num_orders = 20  # Fixed at 20 orders (10 per side)
            
            # Calculate available balance and reserve 20% for ongoing trading
            total_balance = self._get_available_balance()
            trading_reserve = total_balance * Decimal('0.2')  # Keep 20% in reserve
            initial_order_balance = total_balance * Decimal('0.8')  # Use 80% for initial orders
            
            # Calculate per-order quantity
            per_order_quantity = (initial_order_balance / Decimal(str(num_orders))).quantize(
                Decimal('0.00000001'), rounding=ROUND_DOWN
            )
            
            if per_order_quantity < Decimal('0.00000100'):
                print("❌ Insufficient balance for minimum order size")
                return False
            
            # Calculate spread step size
            spread_range = max_spread - min_spread
            spread_step = spread_range / Decimal('10')  # 10 steps for each side
            
            successful_orders = []
            
            # Place buy orders (10 orders below base price)
            for i in range(10):
                time.sleep(random.uniform(0.5, 1.0))
                spread = min_spread + (spread_step * Decimal(str(i)))
                
                # Add small random variation to spread (±10% of step size)
                variation = Decimal(str(random.uniform(-0.1, 0.1))) * spread_step
                final_spread = spread + variation
                
                price = base_price * (Decimal('1') - final_spread)
                
                # Add small random variation to quantity (±5%)
                quantity = per_order_quantity * Decimal(str(random.uniform(0.95, 1.05)))
                quantity_str = f"{quantity:.8f}"
                
                success = self._place_single_order("buy", quantity_str, price, i)
                if success:
                    successful_orders.append(i)
            
            # Place sell orders (10 orders above base price)
            for i in range(10):
                time.sleep(random.uniform(0.5, 1.0))
                spread = min_spread + (spread_step * Decimal(str(i)))
                
                # Add small random variation to spread (±10% of step size)
                variation = Decimal(str(random.uniform(-0.1, 0.1))) * spread_step
                final_spread = spread + variation
                
                price = base_price * (Decimal('1') + final_spread)
                
                # Add small random variation to quantity (±5%)
                quantity = per_order_quantity * Decimal(str(random.uniform(0.95, 1.05)))
                quantity_str = f"{quantity:.8f}"
                
                success = self._place_single_order("sell", quantity_str, price, i + 10)
                if success:
                    successful_orders.append(i + 10)
            
            return len(successful_orders) > 0
            
        except Exception as e:
            print(f"❌ Error placing distributed orders: {str(e)}")
            return False

    def _get_available_balance(self) -> Decimal:
        """Get available balance for trading."""
        if self.base_symbol == "BTC":
            # For BTC/USDT pair, check BTC balance for sells and USDT/price for buys
            btc_balance = self.client.get_currency_balance(self.account, "BTC")
            usdt_balance = self.client.get_currency_balance(self.account, "USDT")
            
            if isinstance(btc_balance, str) and isinstance(usdt_balance, str):
                btc_amount = Decimal(btc_balance.split()[0])
                usdt_amount = Decimal(usdt_balance.split()[0])
                # Use current price from config or a default
                price = self.config.get('current_price', Decimal('100000.0'))
                return min(btc_amount, usdt_amount / price)
        
        return Decimal('0')

    def _place_single_order(self, order_type: str, quantity: str, 
                           price: Decimal, order_num: int) -> bool:
        """Place a single order with error handling."""
        try:
            print(f"\n{'💰' if order_type == 'sell' else '💸'} Placing {order_type} "
                  f"#{order_num+1} for {quantity} {self.base_symbol} "
                  f"at {price:.10f}")
            
            result = self.dex.place_order(
                account=self.account,
                order_type=order_type,
                quantity=quantity,
                price=f"{price:.10f}",
                quote_symbol=self.quote_symbol,
                base_symbol=self.base_symbol
            )
            
            if not result.get("success"):
                error = result.get('error', 'Unknown error')
                print(f"❌ {order_type.title()} order #{order_num+1} failed: {error}")
                return False
                
            return True
            
        except Exception as e:
            print(f"❌ Error placing {order_type} order: {e}")
            return False

    def _distribute_quantities(self, total: Decimal, count: int) -> list:
        """
        Distribute total quantity across orders with randomization.
        """
        distribution = self.config.get('quantity_distribution', 'equal')
        
        if distribution == 'equal':
            base_qty = total / count
            # Add random variation (±10%)
            return [base_qty * Decimal(str(random.uniform(0.9, 1.1))) for _ in range(count)]
        # Add other distribution methods here
        return [total / count] * count

    def _place_bid_ask_pair(self, bid_price: Decimal, ask_price: Decimal, 
                           quantity: str, order_num: int, ask_first: bool = False) -> None:
        """Place a pair of bid/ask orders with optional ordering."""
        orders = [
            ('bid', bid_price),
            ('ask', ask_price)
        ]
        
        if ask_first:
            orders.reverse()
            
        for order_type, price in orders:
            print(f"\n{'💰' if order_type == 'ask' else '💸'} Placing {order_type} "
                  f"#{order_num+1} for {quantity} {self.base_symbol} at {price:.10f}")
            
            result = self.dex.place_order(
                account=self.account,
                order_type="sell" if order_type == "ask" else "buy",
                quantity=quantity,
                price=f"{price:.10f}",
                quote_symbol=self.quote_symbol,
                base_symbol=self.base_symbol
            )
            
            if not result.get("success"):
                print(f"❌ {order_type.title()} order #{order_num+1} failed: "
                      f"{result.get('error', 'Unknown error')}") 

    def cancel_random_orders(self) -> None:
        """Cancel a random selection of existing orders."""
        try:
            order_book = self.dex.fetch_order_book(
                quote_symbol=self.quote_symbol,
                base_symbol=self.base_symbol
            )
            
            our_bids = [order for order in order_book["bids"] 
                       if order["account"] == self.account]
            our_offers = [order for order in order_book["offers"] 
                         if order["account"] == self.account]
            
            # Only cancel 1 order at a time for more gradual changes
            if our_bids + our_offers:
                order_to_cancel = random.choice(our_bids + our_offers)
                self.dex.cancel_order(
                    account=self.account,
                    order_id=order_to_cancel['identifier'],
                    quote_symbol=self.quote_symbol,
                    base_symbol=self.base_symbol
                )
                print(f"🗑️  Cancelled order at price {order_to_cancel['price']}")
                
        except Exception as e:
            print(f"Error cancelling random orders: {e}")

    def place_replacement_orders(self, signal: Dict[str, Any]) -> bool:
        """Place a single new order to replace the cancelled one."""
        try:
            base_price = signal['price']
            min_spread = signal['min_spread']
            max_spread = signal['max_spread']
            
            # Calculate available balance including reserve
            available_balance = self._get_available_balance()
            per_order_quantity = (available_balance / Decimal('20')).quantize(
                Decimal('0.00000001'), rounding=ROUND_DOWN
            )
            
            # Randomly choose buy or sell
            order_type = random.choice(['buy', 'sell'])
            
            # Calculate price with some randomization
            direction = 1 if order_type == 'sell' else -1
            spread = Decimal(str(random.uniform(
                float(min_spread),
                float(max_spread)
            )))
            price = base_price * (Decimal('1') + (direction * spread))
            
            # Calculate quantity with some randomization (±5%)
            quantity = per_order_quantity * Decimal(str(random.uniform(0.95, 1.05)))
            quantity_str = f"{quantity:.8f}"
            
            return self._place_single_order(order_type, quantity_str, price, 0)
            
        except Exception as e:
            print(f"Error placing replacement order: {e}")
            return False