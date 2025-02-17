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
            self.logger.info(f"Cleaning up strategy for {self.account}...")
            
            # Cancel all orders for this trading pair
            result = self.dex.cancel_all_orders(
                self.account,
                self.quote_symbol,
                self.base_symbol
            )
            
            if result.get("success"):
                self.logger.info("Successfully cancelled all orders")
            else:
                self.logger.error(f"Failed to cancel orders: {result.get('error')}")
                
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
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
        min_order, max_order = self._get_order_limits()
        
        balance = self.client.get_currency_balance(self.account, self.base_symbol)
        print(f"\nBalance check:")
        print(f"Raw balance response: {balance}")
        
        if isinstance(balance, str):
            amount = Decimal(balance.split()[0])
            print(f"Parsed balance: {amount} {self.base_symbol}")
            return max(min_order, min(max_order, amount))
        
        print("No balance found!")
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

    def _place_single_order(self, order_type: str, quantity: str, 
                           price: Decimal, order_num: int) -> bool:
        """Place a single order with error handling."""
        try:
            min_order, _ = self._get_order_limits()
            
            # Convert quantity and price to Decimal for calculations
            quantity_decimal = Decimal(str(quantity))
            price_decimal = Decimal(str(price))
            
            # Check minimum order size
            if quantity_decimal < min_order:
                self.logger.error(
                    f"❌ Order quantity {quantity_decimal} {self.base_symbol} "
                    f"below minimum {min_order} {self.base_symbol}"
                )
                return False
            
            # Calculate total value in BTC
            total_value = quantity_decimal * price_decimal
            
            # Check if total value is at least 1 satoshi (0.00000001 BTC)
            if self.quote_symbol == 'BTC' and total_value < Decimal('0.00000001'):
                self.logger.error(
                    f"❌ Total order value {total_value:.10f} BTC "
                    f"({quantity_decimal} {self.base_symbol} * {price_decimal:.10f} BTC) "
                    f"is below minimum of 0.00000001 BTC (1 satoshi)"
                )
                return False

            # Format price with 10 decimal places for BTC
            if self.quote_symbol == 'BTC':
                price_str = f"{price_decimal:.10f}"
            else:
                price_str = f"{price_decimal:.8f}"

            result = self.dex.place_order(
                account=self.account,
                order_type=order_type,
                quantity=str(quantity),
                price=price_str,
                quote_symbol=self.quote_symbol,
                base_symbol=self.base_symbol
            )
            
            if result.get("success"):
                emoji = '💰' if order_type == 'sell' else '💸'
                log_msg = (
                    f"{self.account}: {order_type.upper()} {quantity} {self.base_symbol} "
                    f"at {price_str} {self.quote_symbol} "
                    f"(Total: {total_value:.8f} {self.quote_symbol})"
                )
                self.logger.info(f"{emoji} {log_msg}")
                return True
            else:
                error = result.get('error', 'Unknown error')
                self.logger.error(f"❌ {self.account}: {order_type.title()} order #{order_num+1} failed: {error}")
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
