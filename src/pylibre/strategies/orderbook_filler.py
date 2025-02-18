from decimal import Decimal
import time
import random
from pylibre.utils.shared_data import read_price
from .templates.base_strategy import BaseStrategy
from typing import Dict, Any

class OrderBookFillerStrategy(BaseStrategy):
    """Strategy for filling the order book with buy and sell orders."""
    
    def __init__(self, client, account, base_symbol, quote_symbol, logger, min_spread_percentage, max_spread_percentage, num_orders):
        parameters = {
            'min_spread_percentage': min_spread_percentage,
            'max_spread_percentage': max_spread_percentage,
            'num_orders': num_orders
        }
        super().__init__(client, account, base_symbol, quote_symbol, parameters, logger)
        self.min_spread_percentage = Decimal(str(min_spread_percentage))
        self.max_spread_percentage = Decimal(str(max_spread_percentage))
        self.num_orders = num_orders

    def generate_signal(self) -> Dict[str, Any]:
        """Generate trading signals based on current market conditions."""
        current_price = Decimal(str(read_price(f"shared_data/{self.base_symbol.lower()}{self.quote_symbol.lower()}_price.json")))
        return {
            'price': current_price,
            'min_spread': self.min_spread_percentage,
            'max_spread': self.max_spread_percentage,
            'num_orders': self.num_orders
        }

    def place_orders(self, signal: Dict[str, Any]) -> bool:
        """Place orders based on the generated signal."""
        try:
            self.cancel_out_of_range_orders()
            self.fill_orderbook()
            return True
        except Exception as e:
            self.logger.error(f"Error placing orders: {e}")
            return False

    def check_balance(self):
        """Check and log the balance for both base and quote assets."""
        base_balance = self.get_currency_balance(self.base_symbol)
        quote_balance = self.get_currency_balance(self.quote_symbol)
        self.logger.info(f"{self.account} balances - {self.base_symbol}: {base_balance}, {self.quote_symbol}: {quote_balance}")

    def get_orderbook_status(self) -> tuple[int, int]:
        """Get number of our orders on each side of the book."""
        try:
            order_book = self.dex.fetch_order_book(
                quote_symbol=self.quote_symbol,
                base_symbol=self.base_symbol
            )
            
            our_bids = len([order for order in order_book["bids"] if order["account"] == self.account])
            our_asks = len([order for order in order_book["offers"] if order["account"] == self.account])
            
            self.logger.info(f"Found {our_bids} bids and {our_asks} offers for {self.account}")
            return our_bids, our_asks
            
        except Exception as e:
            self.logger.error(f"Error getting orderbook status: {e}")
            return 0, 0

    def cancel_out_of_range_orders(self):
        """Cancel orders that are outside the specified spread range."""
        try:
            order_book = self.dex.fetch_order_book(
                quote_symbol=self.quote_symbol,
                base_symbol=self.base_symbol
            )
            
            current_price = Decimal(str(read_price(f"shared_data/{self.base_symbol.lower()}{self.quote_symbol.lower()}_price.json")))
            
            # Combine bids and offers
            our_orders = (
                [order for order in order_book["bids"] if order["account"] == self.account] +
                [order for order in order_book["offers"] if order["account"] == self.account]
            )
            
            if not our_orders:
                self.logger.info(f"No orders found for {self.account}")
                return
                
            self.logger.info(f"Checking {len(our_orders)} orders for out-of-range spreads")
            
            # Cancel orders one by one if outside spread range
            for order in our_orders:
                try:
                    price = Decimal(str(order["price"]))
                    spread = abs((price - current_price) / current_price)
                    
                    if not (self.min_spread_percentage <= spread <= self.max_spread_percentage):
                        self.logger.info(f"Cancelling order {order['identifier']} at price {price} (spread: {spread:.2%})")
                        
                        result = self.dex.cancel_order(
                            account=self.account,
                            order_id=int(order['identifier']),  # Convert back to int for cancel_order
                            quote_symbol=self.quote_symbol,
                            base_symbol=self.base_symbol
                        )
                        
                        if result.get("success"):
                            self.logger.info(f"✅ Cancelled order {order['identifier']}")
                        else:
                            self.logger.error(f"❌ Failed to cancel order {order['identifier']}: {result.get('error')}")
                            
                except (ValueError, KeyError, Decimal.InvalidOperation) as e:
                    self.logger.error(f"Error processing order {order.get('identifier')}: {e}")
                    continue
                    
        except Exception as e:
            self.logger.error(f"Error cancelling out-of-range orders: {e}")

    def fill_orderbook(self):
        """Place new buy and sell orders to fill the order book."""
        try:
            current_price = Decimal(str(read_price(f"shared_data/{self.base_symbol.lower()}{self.quote_symbol.lower()}_price.json")))
            if current_price <= Decimal('0'):
                self.logger.error(f"Invalid current price: {current_price}")
                return
            
            # Get both balances
            base_balance = self.get_currency_balance(self.base_symbol)  # BTC
            quote_balance = self.get_currency_balance(self.quote_symbol)  # USDT
            
            if base_balance <= Decimal('0') and quote_balance <= Decimal('0'):
                self.logger.error(f"No available balance - {self.base_symbol}: {base_balance}, {self.quote_symbol}: {quote_balance}")
                return
            
            num_orders_per_side = self.num_orders // 2
            
            # Calculate order sizes
            base_quantities = []  # For sell orders in BTC
            quote_quantities = []  # For buy orders in USDT
            
            if base_balance > Decimal('0'):
                # Distribute BTC for sell orders
                base_quantities = self.distribute_balance_into_orders(base_balance, num_orders_per_side)
                if not base_quantities:
                    self.logger.warning(f"Insufficient {self.base_symbol} balance ({base_balance}) for sell orders")
                    
            if quote_balance > Decimal('0'):
                # Convert USDT to equivalent BTC quantities for buy orders using current price
                usdt_per_order = quote_balance / Decimal(str(num_orders_per_side))
                for _ in range(num_orders_per_side):
                    try:
                        # Add some randomness to the USDT amount (±20%)
                        variation = Decimal(str(random.uniform(0.8, 1.2)))
                        usdt_amount = usdt_per_order * variation
                        btc_amount = (usdt_amount / current_price).quantize(Decimal('0.00000001'))
                        if btc_amount >= Decimal('0.00000001'):  # Minimum BTC order size
                            quote_quantities.append(btc_amount)
                    except (decimal.InvalidOperation, decimal.DivisionByZero) as e:
                        self.logger.error(f"Error calculating buy order quantity: {e}")
                        continue
                
                if not quote_quantities:
                    self.logger.warning(f"Insufficient {self.quote_symbol} balance ({quote_balance}) for buy orders")

            # Place sell orders above market price
            for i, quantity in enumerate(base_quantities):
                try:
                    spread = Decimal(str(random.uniform(
                        float(self.min_spread_percentage), 
                        float(self.max_spread_percentage)
                    )))
                    price = current_price * (Decimal('1') + spread)
                    
                    result = self.dex.place_order(
                        account=self.account,
                        order_type='sell',
                        quantity=f"{quantity:.8f}",
                        price=price,
                        quote_symbol=self.quote_symbol,
                        base_symbol=self.base_symbol
                    )
                    
                    if result.get("success"):
                        self.logger.info(f"✅ Placed sell order: {quantity:.8f} {self.base_symbol} @ {price:.2f}")
                    else:
                        self.logger.error(f"❌ Failed to place sell order: {result.get('error')}")
                        
                except Exception as e:
                    self.logger.error(f"Error placing sell order {i+1}: {e}")
                    continue

            # Place buy orders below market price
            for i, quantity in enumerate(quote_quantities):
                try:
                    spread = Decimal(str(random.uniform(
                        float(self.min_spread_percentage),
                        float(self.max_spread_percentage)
                    )))
                    price = current_price * (Decimal('1') - spread)
                    
                    result = self.dex.place_order(
                        account=self.account,
                        order_type='buy',
                        quantity=f"{quantity:.8f}",
                        price=price,
                        quote_symbol=self.quote_symbol,
                        base_symbol=self.base_symbol
                    )
                    
                    if result.get("success"):
                        self.logger.info(f"✅ Placed buy order: {quantity:.8f} {self.base_symbol} @ {price:.2f}")
                    else:
                        self.logger.error(f"❌ Failed to place buy order: {result.get('error')}")
                        
                except Exception as e:
                    self.logger.error(f"Error placing buy order {i+1}: {e}")
                    continue
                    
        except Exception as e:
            self.logger.error(f"Error in fill_orderbook: {e}")

    def distribute_balance_into_orders(self, total_balance: Decimal, num_orders: int) -> list:
        """Distribute the total balance into a specified number of orders with random quantities."""
        min_order_size = Decimal('0.00000001')  # Minimum BTC order size
        
        if total_balance < min_order_size * num_orders:
            self.logger.error(f"Insufficient balance ({total_balance}) to place {num_orders} orders of minimum size {min_order_size}")
            return []

        quantities = []
        remaining_balance = total_balance

        for _ in range(num_orders - 1):
            # Calculate maximum possible order size while ensuring we have enough for remaining orders
            max_possible = remaining_balance - (min_order_size * (num_orders - len(quantities) - 1))
            
            # Generate a random quantity between min_order_size and max_possible
            quantity = Decimal(str(random.uniform(
                float(min_order_size), 
                float(max_possible)
            ))).quantize(Decimal('0.00000001'))
            
            quantities.append(quantity)
            remaining_balance -= quantity

        # Add the remaining balance as the last order
        if remaining_balance >= min_order_size:
            quantities.append(remaining_balance.quantize(Decimal('0.00000001')))
            random.shuffle(quantities)
            
        return quantities
