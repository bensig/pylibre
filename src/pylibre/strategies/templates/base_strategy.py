from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pylibre import LibreClient
from pylibre.dex import DexClient
from pylibre.utils.logger import StrategyLogger
import random
import time
from decimal import Decimal, ROUND_DOWN
from pylibre.utils.shared_data import read_price
from pylibre.utils.logger import LogLevel
import decimal

DEFAULT_COIN_LIMITS = {
    'USDT': {
        'min_order_value': 10.0,
        'max_order_value': 100.0,
    },
    'BTC': {
        'min_order_value': 0.0001,
        'max_order_value': 0.001,
    },
    'LIBRE': {
        'min_order_value': 100.0,
        'max_order_value': 1000.0,
    }
}

DEFAULT_STRATEGY_PARAMS = {
    'min_spread_percentage': 0.006,
    'max_spread_percentage': 0.01,
    'num_orders': 20,
    'order_spacing': 'linear',
    'quantity_distribution': 'random'
}

class BaseStrategy(ABC):
    """Base class for all trading strategies."""
    
    def __init__(
        self,
        client: LibreClient,
        account: str,
        base_symbol: str,
        quote_symbol: str,
        parameters: Dict[str, Any],
        logger: Optional[StrategyLogger] = None
    ):
        """Initialize the strategy."""
        self.client = client
        self.account = account
        self.base_symbol = base_symbol
        self.quote_symbol = quote_symbol
        self.parameters = parameters
        self.logger = logger or StrategyLogger(f"Strategy_{account}", level=LogLevel.DEBUG)
        self.dex = DexClient(client)
        self.running = True

        # Log initial configuration
        self.logger.debug(
            f"Strategy initialized with:"
            f"\n - Account: {account}"
            f"\n - Base Symbol: {base_symbol}"
            f"\n - Quote Symbol: {quote_symbol}"
            f"\n - Parameters: {parameters}"
        )

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
            # Get all orders first
            order_book = self.dex.fetch_order_book(
                quote_symbol=self.quote_symbol,
                base_symbol=self.base_symbol
            )
            
            our_orders = (
                [order for order in order_book["bids"] if order["account"] == self.account] +
                [order for order in order_book["offers"] if order["account"] == self.account]
            )
            
            if not our_orders:
                self.logger.info(f"✨ No orders found for {self.account}")
                return True
                
            self.logger.info(f"Found {len(our_orders)} orders to cancel")
            
            # Cancel orders one by one
            successful = 0
            failed = 0
            
            for order in our_orders:
                if not self.running:  # Check if we should stop
                    break
                    
                result = self.dex.cancel_order(
                    account=self.account,
                    order_id=order['identifier'],
                    quote_symbol=self.quote_symbol,
                    base_symbol=self.base_symbol
                )
                
                if result.get("success"):
                    successful += 1
                    self.logger.info(f"✅ Cancelled order {order['identifier']}")
                else:
                    failed += 1
                    self.logger.error(f"❌ Failed to cancel order {order['identifier']}: {result.get('error')}")
                
                time.sleep(1)  # Same delay as cancel_all_orders.py
            
            self.logger.info(f"\n📊 Summary:")
            self.logger.info(f"✅ Successfully cancelled: {successful}")
            self.logger.info(f"❌ Failed to cancel: {failed}")
            
            return successful > 0 or len(our_orders) == 0
            
        except Exception as e:
            self.logger.error(f"Error cancelling orders: {e}")
            return False

    def run(self) -> None:
        """Main strategy execution loop."""
        self.running = True
        self.logger.info(f"Starting {self.__class__.__name__} for {self.base_symbol}/{self.quote_symbol}")
        
        try:
            while self.running:
                # Generate trading signal
                signal = self.generate_signal()
                if signal:
                    # Place orders based on signal
                    self.place_orders(signal)
                
                # Wait for next iteration using update_interval_ms from parameters
                time.sleep(self.parameters.get('update_interval_ms', 500) / 1000)
                
        except KeyboardInterrupt:
            self.logger.info("Strategy stopped by user")
        except Exception as e:
            self.logger.error(f"Strategy error: {e}")
        finally:
            self.cleanup()

    def cleanup(self):
        """Clean up any open orders when the strategy stops."""
        try:
            self.running = False  # Set this first to stop any ongoing operations
            self.logger.info(f"Cleaning up strategy for {self.account}...")
            self.cancel_orders()  # Use our improved cancel_orders method
        except Exception as e:
            self.logger.error(f"❌ {self.account}: Error during cleanup: {e}")
        finally:
            self.running = False
    def _get_order_limits(self) -> tuple[Decimal, Decimal]:
        """Get minimum and maximum order sizes for the current symbol."""
        # Get default limits for the symbol
        default_limits = DEFAULT_COIN_LIMITS.get(self.base_symbol, {
            'min_order_value': 10.0,
            'max_order_value': 100.0,
        })
        
        # Get limits from parameters, falling back to defaults
        min_order = Decimal(str(self.parameters.get(
            'min_order_value',
            default_limits['min_order_value']
        )))
        max_order = Decimal(str(self.parameters.get(
            'max_order_value',
            default_limits['max_order_value']
        )))
        
        self.logger.debug(
            f"Order limits for {self.base_symbol}: "
            f"min={min_order}, max={max_order}"
        )
        
        return min_order, max_order

    def _get_available_balance(self) -> Decimal:
        """Get available balance for trading."""
        try:
            balances = self.client.get_currency_balance(self.account, self.base_symbol)
            self.logger.debug(f"Raw balance response for {self.account} {self.base_symbol}: {balances}")
            
            if not balances:
                self.logger.error(f"No balance found for {self.account} {self.base_symbol}")
                return Decimal('0')
            
            if not isinstance(balances, list):
                self.logger.error(f"Expected list response, got {type(balances)}: {balances}")
                return Decimal('0')
            
            # get_currency_balance returns a list of strings like ["123.4567 SYMBOL"]
            if not balances[0]:
                self.logger.error(f"Empty balance string for {self.account}")
                return Decimal('0')
                
            balance_str = balances[0]
            self.logger.debug(f"Processing balance string: '{balance_str}'")
            
            parts = balance_str.split()
            if len(parts) != 2:
                self.logger.error(f"Invalid balance format: '{balance_str}'")
                return Decimal('0')
                
            amount = parts[0]
            symbol = parts[1]
            
            if symbol != self.base_symbol:
                self.logger.error(f"Symbol mismatch: expected {self.base_symbol}, got {symbol}")
                return Decimal('0')
                
            try:
                balance = Decimal(amount)
                self.logger.info(f"{self.account} balance: {balance} {symbol}")
                return balance
            except decimal.InvalidOperation as e:
                self.logger.error(f"Failed to convert '{amount}' to Decimal: {e}")
                return Decimal('0')
            
        except Exception as e:
            self.logger.error(f"Error getting balance for {self.account}: {str(e)}")
            import traceback
            self.logger.debug(f"Balance error traceback: {traceback.format_exc()}")
            return Decimal('0')

    def place_distributed_orders(self, base_price: Decimal, min_spread: Decimal, max_spread: Decimal) -> bool:
        """Place multiple orders with configurable distribution and spacing."""
        try:
            print("\n=== Starting place_distributed_orders ===")
            min_order, max_order = self._get_order_limits()
            total_balance = self._get_available_balance()
            
            print(f"\nInitial values:")
            print(f"Base price: {base_price}")
            print(f"Total Balance: {total_balance} {self.base_symbol}")
            print(f"Min Order: {min_order} {self.base_symbol}")
            print(f"Max Order: {max_order} {self.base_symbol}")
            
            # Calculate number of orders based on minimum order size
            max_possible_orders = int((total_balance / min_order).to_integral_value(rounding=ROUND_DOWN))
            num_orders = min(20, max_possible_orders)  # Cap at 20 orders
            
            print(f"\nOrder count calculations:")
            print(f"Max Possible Orders: {max_possible_orders}")
            print(f"Num Orders: {num_orders}")
            
            if num_orders == 0:
                print(f"❌ Insufficient balance for minimum orders")
                self.logger.error(
                    f"❌ Available balance {total_balance} {self.base_symbol} insufficient "
                    f"for minimum order size {min_order} {self.base_symbol}"
                )
                return False
            
            # Calculate per-order quantity - ensure it's at least the minimum
            per_order_quantity = max(
                min_order,
                (total_balance / Decimal(str(num_orders))).quantize(
                    Decimal('0.00000001'), rounding=ROUND_DOWN
                )
            )
            
            print(f"\nQuantity calculations:")
            print(f"Per Order Quantity: {per_order_quantity} {self.base_symbol}")
            
            # Split orders evenly between buys and sells
            orders_per_side = num_orders // 2
            spread_step = (max_spread - min_spread) / Decimal(str(orders_per_side))
            
            print(f"Orders Per Side: {orders_per_side}")
            print(f"Spread Step: {spread_step}")
            
            successful_orders = []
            
            # Place buy orders
            for i in range(orders_per_side):
                spread = min_spread + (spread_step * Decimal(str(i)))
                price = base_price * (Decimal('1') - spread)
                
                # Use exact per_order_quantity - no random variation
                quantity_str = f"{per_order_quantity:.8f}"
                print(f"\nPlacing buy order #{i+1}:")
                print(f"Quantity: {quantity_str} {self.base_symbol}")
                print(f"Price: {price}")
                
                success = self._place_single_order("buy", quantity_str, price, i)
                if success:
                    successful_orders.append(i)
            
            # Place sell orders
            for i in range(orders_per_side):
                spread = min_spread + (spread_step * Decimal(str(i)))
                price = base_price * (Decimal('1') + spread)
                
                # Use exact per_order_quantity - no random variation
                quantity_str = f"{per_order_quantity:.8f}"
                print(f"\nPlacing sell order #{i+1}:")
                print(f"Quantity: {quantity_str} {self.base_symbol}")
                print(f"Price: {price}")
                
                success = self._place_single_order("sell", quantity_str, price, i + orders_per_side)
                if success:
                    successful_orders.append(i + orders_per_side)
            
            return len(successful_orders) > 0
            
        except Exception as e:
            self.logger.error(f"❌ Error placing distributed orders: {str(e)}")
            return False

    def _get_precision(self, symbol: str) -> int:
        """Get decimal precision for a token."""
        precision_map = {
            "LIBRE": 4,
            "BTC": 8,
            "USDT": 8
        }
        return precision_map.get(symbol, 8)

    def _format_quantity(self, quantity: Decimal, symbol: str) -> str:
        """Format quantity with correct precision."""
        precision = self._get_precision(symbol)
        return f"{quantity:.{precision}f}"

    def _place_single_order(self, order_type: str, quantity: str, price: Decimal, order_num: int) -> bool:
        """Place a single order with proper logging."""
        try:
            # Validate quantity and price
            qty_decimal = Decimal(quantity)
            if qty_decimal <= Decimal('0'):
                self.logger.error(f"❌ {self.account}: Invalid quantity: {quantity}")
                return False
                
            if price <= Decimal('0'):
                self.logger.error(f"❌ {self.account}: Invalid price: {price}")
                return False

            # Format price based on quote currency
            if self.quote_symbol == 'BTC':
                price_str = f"{price:.8f}"
            else:
                price_str = f"{price:.2f}"
                
            self.logger.info(
                f"Placing {order_type} order: {quantity} {self.base_symbol} @ {price_str} {self.quote_symbol}"
            )

            result = self.dex.place_order(
                account=self.account,
                order_type=order_type,
                quantity=quantity,
                price=price_str,
                quote_symbol=self.quote_symbol,
                base_symbol=self.base_symbol
            )
            
            if result.get("success"):
                emoji = '💰' if order_type == 'sell' else '💸'
                self.logger.info(f"{emoji} {self.account}: {order_type.upper()} {quantity} @ {price_str}")
                return True
            else:
                error = result.get('error', 'Unknown error')
                self.logger.error(f"❌ {self.account}: {order_type.title()} order failed: {error}")
                return False
                
        except Exception as e:
            self.logger.error(f"❌ {self.account}: Error placing {order_type} order: {e}")
            return False

    def _distribute_quantities(self, total: Decimal, count: int) -> list:
        """Distribute total quantity across orders with randomization."""
        distribution = self.parameters.get('quantity_distribution', 'equal')
        
        if distribution == 'equal':
            base_qty = total / count
            # Add random variation (±10%)
            return [base_qty * Decimal(str(random.uniform(0.9, 1.1))) for _ in range(count)]
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
            if signal is None:
                self.logger.error("No valid signal to place replacement orders")
                return False
            
            base_price = signal.get('price')
            min_spread = signal.get('min_spread')
            max_spread = signal.get('max_spread')
            
            if not all([base_price, min_spread, max_spread]):
                self.logger.error("Missing required signal data")
                return False
            
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
            quantity_str = self._format_quantity(quantity, self.base_symbol)
            
            return self._place_single_order(order_type, quantity_str, price, 0)
            
        except Exception as e:
            self.logger.error(f"Error placing replacement order: {e}")
            return False

    def get_market_price(self) -> Optional[Decimal]:
        """Get market price from price feed."""
        try:
            # Get price source from parameters if available
            pair = f"{self.base_symbol}/{self.quote_symbol}"
            price_source = self.parameters.get('price_source', {})
            
            # If there's a specific config with a fixed price, use that
            if price_source and price_source.get('type') == 'fixed':
                price = price_source.get('price')
                if price:
                    return Decimal(str(price))
            
            # Otherwise try to read from the default price file
            price_file = f"shared_data/{self.base_symbol.lower()}{self.quote_symbol.lower()}_price.json"
            price = read_price(price_file)
            if price:
                return Decimal(str(price))
            
            self.logger.error(f"Could not read price from {price_file}")
            return None
            
        except Exception as e:
            self.logger.error(f"Error getting market price: {e}")
            return None

    def generate_signal(self) -> Dict[str, Any]:
        """Generate signal based on market price feed."""
        market_price = self.get_market_price()
        if market_price is None:
            return None
        
        # Get min and max spreads from parameters
        min_spread = Decimal(str(self.parameters['min_spread_percentage']))
        max_spread = Decimal(str(self.parameters['max_spread_percentage']))
        
        self.logger.debug(
            f"Generating signal with spreads: {min_spread} to {max_spread}"
        )
        
        return {
            'price': market_price,
            'min_spread': min_spread,
            'max_spread': max_spread
        }
