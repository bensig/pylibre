from abc import ABC, abstractmethod
from typing import Dict, Any
from pylibre import LibreClient
from pylibre.dex import DexClient
import random
import time
from decimal import Decimal

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
            while self.is_running:
                # Generate trading signal
                signal = self.generate_signal()
                
                # Cancel existing orders
                self.cancel_orders()
                
                # Place new orders
                self.place_orders(signal)
                
                # Wait for next iteration
                import time
                time.sleep(self.config.get('interval', 5))
                
        except KeyboardInterrupt:
            print("\n\n🛑 Strategy stopped by user")
        finally:
            self.cleanup()

    def cleanup(self) -> None:
        """
        Cleanup resources and cancel orders on shutdown.
        """
        print("🧹 Cleaning up...")
        self.cancel_orders()
        self.is_running = False 

    def place_distributed_orders(self, base_price: Decimal, spread: Decimal) -> bool:
        """
        Place multiple orders with configurable distribution and spacing.
        """
        try:
            num_orders = max(2, self.config.get('num_orders', 2))  # Ensure at least 2 orders
            if num_orders % 2 != 0:  # Make sure it's even
                num_orders += 1
            
            spacing = self.config.get('order_spacing', 'linear')
            
            # Calculate price ranges with some randomization
            max_spread = self.config.get('max_change_percentage', spread * Decimal('2'))
            min_price = base_price * (Decimal('1') - max_spread)
            max_price = base_price * (Decimal('1') + max_spread)
            
            # Calculate order quantities with randomization
            total_quantity = Decimal(self.config.get('quantity', '100.00000000'))
            # Ensure we don't exceed available balance
            total_quantity = min(
                total_quantity,
                Decimal(str(self._get_available_balance()))
            )
            
            if total_quantity <= 0:
                print("❌ Insufficient balance for trading")
                return False
                
            # Split total quantity between buys and sells
            orders_per_side = num_orders // 2  # This will now never be zero
            per_side_quantity = total_quantity / Decimal('2')
            buy_quantities = self._distribute_quantities(per_side_quantity, orders_per_side)
            sell_quantities = self._distribute_quantities(per_side_quantity, orders_per_side)
            
            # Track successful orders
            successful_orders = []
            
            # Place buy orders
            for i, quantity in enumerate(buy_quantities):
                time.sleep(random.uniform(0.5, 1.5))
                
                if spacing == 'linear':
                    price_step = (base_price - min_price) / (len(buy_quantities) + 1)
                    base_price_point = min_price + (price_step * (i + 1))
                    # Add smaller random variation (±0.1%)
                    variation = Decimal(str(random.uniform(-0.001, 0.001)))
                    price = base_price_point * (Decimal('1') + variation)
                
                # Ensure minimum quantity
                if quantity < Decimal('0.00000100'):
                    continue
                    
                quantity_str = f"{quantity:.8f}"
                success = self._place_single_order("buy", quantity_str, price, i)
                if success:
                    successful_orders.append(i)
            
            # Place sell orders
            for i, quantity in enumerate(sell_quantities):
                time.sleep(random.uniform(0.5, 1.5))
                
                if spacing == 'linear':
                    price_step = (max_price - base_price) / (len(sell_quantities) + 1)
                    base_price_point = base_price + (price_step * (i + 1))
                    # Add smaller random variation (±0.1%)
                    variation = Decimal(str(random.uniform(-0.001, 0.001)))
                    price = base_price_point * (Decimal('1') + variation)
                
                # Ensure minimum quantity
                if quantity < Decimal('0.00000100'):
                    continue
                    
                quantity_str = f"{quantity:.8f}"
                success = self._place_single_order("sell", quantity_str, price, i + len(buy_quantities))
                if success:
                    successful_orders.append(i + len(buy_quantities))
            
            return len(successful_orders) > 0
            
        except Exception as e:
            print(f"❌ Error placing distributed orders: {str(e)}")  # Added str() for better error messages
            return False

    def _get_available_balance(self) -> Decimal:
        """Get available balance for trading."""
        if self.base_symbol == "BTC":
            # For BTC/USDT pair, check BTC balance for sells and USDT/price for buys
            btc_balance = self.client.get_currency_balance(None, self.account, "BTC")
            usdt_balance = self.client.get_currency_balance(None, self.account, "USDT")
            
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