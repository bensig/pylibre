#!/usr/bin/env python3
"""
OrderBookMakerStrategy implementation for LIBRE/BTC trading pair.
This script implements a market making strategy that creates a spread of orders
around a center price, respecting minimum and maximum values from the config.
"""

import sys
import os
import time
import random
import yaml
import argparse
import logging
from decimal import Decimal, ROUND_DOWN

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from pylibre.client import LibreClient
from pylibre.dex import DexClient

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("OrderBookMakerStrategy")

class OrderBookMakerStrategy:
    """
    OrderBookMakerStrategy creates a spread of orders around a center price.
    It respects minimum and maximum values from the config.
    """
    
    def __init__(self, client, config, account, base_symbol, quote_symbol):
        """
        Initialize the OrderBookMakerStrategy.
        
        Args:
            client (LibreClient): The LibreClient instance
            config (dict): The configuration dictionary
            account (str): The account to use for trading
            base_symbol (str): The base currency symbol (e.g., "LIBRE")
            quote_symbol (str): The quote currency symbol (e.g., "BTC")
        """
        self.client = client
        self.config = config
        self.account = account
        self.base_symbol = base_symbol
        self.quote_symbol = quote_symbol
        self.dex = DexClient(client)
        self.dex_contract = "dex.libre"
        
        # Load pair-specific config
        pair_key = f"{base_symbol}/{quote_symbol}"
        self.pair_config = self.config.get("strategies", {}).get(pair_key, {})
        
        # Set default values if not in config
        self.min_base_value = Decimal(str(self.pair_config.get(f"min_order_value_{base_symbol.lower()}", 100.0)))
        self.max_base_value = Decimal(str(self.pair_config.get(f"max_order_value_{base_symbol.lower()}", 1000.0)))
        self.min_quote_value = Decimal(str(self.pair_config.get(f"min_order_value_{quote_symbol.lower()}", 0.00001)))
        self.max_quote_value = Decimal(str(self.pair_config.get(f"max_order_value_{quote_symbol.lower()}", 0.001)))
        
        # Strategy parameters
        self.total_orders = 30  # Default: 30 total orders (15 buy, 15 sell)
        self.min_spread = Decimal("0.06")  # Default: 6%
        self.max_spread = Decimal("0.20")  # Default: 20%
        self.order_spacing = "linear"  # Default: linear spacing
        
        # Load strategy-specific config
        strategy_config = self.config.get("strategies", {}).get("defaults", {}).get("OrderBookMakerStrategy", {})
        self.update_interval_ms = strategy_config.get("update_interval_ms", 500)
        self.min_spread = Decimal(str(strategy_config.get("min_spread_percentage", 0.06)))
        self.max_spread = Decimal(str(strategy_config.get("max_spread_percentage", 0.20)))
        self.total_orders = strategy_config.get("num_orders", 30)
        self.quantity_distribution = strategy_config.get("quantity_distribution", "equal")
        self.order_spacing = strategy_config.get("order_spacing", "linear")
        
        # Calculate orders per side (half of total, rounded down)
        self.orders_per_side = self.total_orders // 2
        
        # Price source config
        price_source_config = strategy_config.get("price_source_config", {})
        self.price_source = price_source_config.get("source", "fixed")
        self.reference_symbol = price_source_config.get("reference_symbol", "BTCUSDT")
        
        # Override with pair-specific price source if available
        pair_price_sources = self.config.get("strategy_groups", {}).get("libre_market_making", {}).get("price_sources", {})
        if pair_key in pair_price_sources:
            pair_price_source = pair_price_sources[pair_key]
            self.price_source = pair_price_source.get("source", self.price_source)
            self.center_price = Decimal(str(pair_price_source.get("price", self.center_price)))
        
        logger.info(f"Initialized OrderBookMakerStrategy for {base_symbol}/{quote_symbol}")
        logger.info(f"Account: {account}")
        logger.info(f"Center Price: {self.center_price} {quote_symbol}")
        logger.info(f"Total Orders: {self.total_orders} ({self.orders_per_side} on each side)")
        logger.info(f"Spread Range: {self.min_spread*100}% to {self.max_spread*100}%")
        logger.info(f"Min {base_symbol} Value: {self.min_base_value}")
        logger.info(f"Max {base_symbol} Value: {self.max_base_value}")
        logger.info(f"Min {quote_symbol} Value: {self.min_quote_value}")
        logger.info(f"Max {quote_symbol} Value: {self.max_quote_value}")
    
    def check_balances(self):
        """Check account balances."""
        logger.info("Checking balances...")
        base_balance = self.client.get_currency_balance(self.account, self.base_symbol)
        quote_balance = self.client.get_currency_balance(self.account, self.quote_symbol)
        
        logger.info(f"{self.account} {self.base_symbol} balance: {base_balance}")
        logger.info(f"{self.account} {self.quote_symbol} balance: {quote_balance}")
        
        return base_balance, quote_balance
    
    def cancel_existing_orders(self):
        """Cancel existing orders for the trading pair."""
        logger.info(f"Cancelling existing orders for {self.base_symbol}/{self.quote_symbol}...")
        
        try:
            result = self.dex.cancel_all_orders(
                account=self.account,
                quote_symbol=self.quote_symbol,
                base_symbol=self.base_symbol
            )
            
            logger.info(f"Cancelled {result.get('successful', 0)} orders")
            return True
        except Exception as e:
            logger.error(f"Error cancelling orders: {str(e)}")
            return False
    
    def generate_order_prices(self):
        """Generate order prices based on center price and spread."""
        logger.info("Generating order prices...")
        
        center_price = self.center_price
        min_price = center_price * (Decimal('1') - self.max_spread)
        max_price = center_price * (Decimal('1') + self.max_spread)
        
        logger.info(f"Price Range: {min_price:.10f} - {max_price:.10f} {self.quote_symbol}")
        
        # Generate sell prices (above center price)
        sell_prices = []
        if self.order_spacing == "linear":
            price_step = (max_price - center_price) / Decimal(str(self.orders_per_side))
            for i in range(self.orders_per_side):
                price = center_price + (price_step * Decimal(str(i + 1)))
                sell_prices.append(price)
        else:  # exponential spacing
            ratio = (max_price / center_price) ** (Decimal('1') / Decimal(str(self.orders_per_side)))
            for i in range(self.orders_per_side):
                price = center_price * (ratio ** Decimal(str(i + 1)))
                sell_prices.append(price)
        
        # Generate buy prices (below center price)
        buy_prices = []
        if self.order_spacing == "linear":
            price_step = (center_price - min_price) / Decimal(str(self.orders_per_side))
            for i in range(self.orders_per_side):
                price = center_price - (price_step * Decimal(str(i + 1)))
                buy_prices.append(price)
        else:  # exponential spacing
            ratio = (center_price / min_price) ** (Decimal('1') / Decimal(str(self.orders_per_side)))
            for i in range(self.orders_per_side):
                price = center_price / (ratio ** Decimal(str(i + 1)))
                buy_prices.append(price)
        
        # Ensure prices have enough precision for BTC
        if self.quote_symbol == 'BTC':
            sell_prices = [price.quantize(Decimal('0.0000000001')) for price in sell_prices]
            buy_prices = [price.quantize(Decimal('0.0000000001')) for price in buy_prices]
        
        return sell_prices, buy_prices
    
    def generate_order_quantities(self, prices, order_type):
        """
        Generate order quantities based on prices and constraints.
        
        Args:
            prices (list): List of prices
            order_type (str): 'buy' or 'sell'
            
        Returns:
            list: List of (price, quantity, quote_value) tuples
        """
        logger.info(f"Generating {order_type} order quantities...")
        
        orders = []
        
        for price in prices:
            # Calculate min and max quantities based on constraints
            if order_type == 'sell':
                # For sell orders, we're selling base_symbol (LIBRE)
                min_quantity = max(self.min_base_value, self.min_quote_value / price)
                max_quantity = min(self.max_base_value, self.max_quote_value / price)
            else:  # buy
                # For buy orders, we're buying base_symbol (LIBRE) with quote_symbol (BTC)
                # Use a lower minimum BTC value for buy orders to allow them at lower prices
                min_btc_value = self.min_quote_value * Decimal('0.5')  # Use half the minimum for buy orders
                min_quantity = max(self.min_base_value, min_btc_value / price)
                max_quantity = min(self.max_base_value, self.max_quote_value / price)
            
            if min_quantity > max_quantity:
                logger.warning(f"Cannot generate valid quantity for price {price:.10f} {self.quote_symbol}")
                logger.warning(f"Min quantity {min_quantity} > Max quantity {max_quantity}")
                continue
            
            # Generate quantity based on distribution
            if self.quantity_distribution == "equal":
                # Equal distribution - use average of min and max
                quantity = ((min_quantity + max_quantity) / Decimal('2')).quantize(Decimal('0.0001'), rounding=ROUND_DOWN)
            elif self.quantity_distribution == "random":
                # Random distribution between min and max
                quantity = Decimal(str(random.uniform(float(min_quantity), float(max_quantity)))).quantize(Decimal('0.0001'), rounding=ROUND_DOWN)
            else:  # proportional to distance from center
                # Further from center = smaller quantity
                center_price = self.center_price
                distance = abs(price - center_price) / center_price
                normalized_distance = distance / self.max_spread
                quantity_factor = Decimal('1') - (normalized_distance * Decimal('0.5'))  # 0.5 to 1.0
                quantity = (min_quantity + (max_quantity - min_quantity) * quantity_factor).quantize(Decimal('0.0001'), rounding=ROUND_DOWN)
            
            # Calculate quote value
            quote_value = quantity * price
            
            # Verify the order meets minimum requirements
            if order_type == 'sell' and quote_value < self.min_quote_value:
                logger.warning(f"Order value {quote_value:.8f} {self.quote_symbol} is below minimum {self.min_quote_value} {self.quote_symbol}")
                logger.warning(f"Adjusting quantity to meet minimum value...")
                quantity = (self.min_quote_value / price).quantize(Decimal('0.0001'), rounding=ROUND_DOWN)
                quote_value = quantity * price
            elif order_type == 'buy' and quote_value < min_btc_value:
                logger.warning(f"Order value {quote_value:.8f} {self.quote_symbol} is below minimum {min_btc_value} {self.quote_symbol}")
                logger.warning(f"Adjusting quantity to meet minimum value...")
                quantity = (min_btc_value / price).quantize(Decimal('0.0001'), rounding=ROUND_DOWN)
                quote_value = quantity * price
            
            if quantity < self.min_base_value:
                logger.warning(f"Order quantity {quantity:.4f} {self.base_symbol} is below minimum {self.min_base_value} {self.base_symbol}")
                logger.warning(f"Adjusting quantity to meet minimum value...")
                quantity = self.min_base_value.quantize(Decimal('0.0001'), rounding=ROUND_DOWN)
                quote_value = quantity * price
            
            orders.append((price, quantity, quote_value))
        
        return orders
    
    def place_orders(self, orders, order_type):
        """
        Place orders on the DEX.
        
        Args:
            orders (list): List of (price, quantity, quote_value) tuples
            order_type (str): 'buy' or 'sell'
            
        Returns:
            int: Number of successfully placed orders
        """
        logger.info(f"Placing {len(orders)} {order_type} orders...")
        
        success_count = 0
        
        for i, (price, quantity, quote_value) in enumerate(orders):
            # Format price with correct precision for BTC
            if self.quote_symbol == 'BTC':
                price_str = f"{price:.10f}"
            else:
                price_str = f"{price:.8f}"
                
            quantity_str = f"{quantity:.4f}"
            quote_value_str = f"{quote_value:.8f}"
            
            logger.info(f"{order_type.capitalize()} Order {i+1}/{len(orders)}:")
            logger.info(f"  Price: {price_str} {self.quote_symbol}")
            logger.info(f"  Quantity: {quantity_str} {self.base_symbol}")
            logger.info(f"  Value: {quote_value_str} {self.quote_symbol}")
            
            result = self.dex.place_order(
                account=self.account,
                order_type=order_type,
                quantity=quantity_str,
                price=price_str,
                quote_symbol=self.quote_symbol,
                base_symbol=self.base_symbol
            )
            
            if result:
                logger.info(f"  ✅ Order placed successfully")
                success_count += 1
            else:
                logger.error(f"  ❌ Failed to place order")
            
            # Small delay to avoid rate limiting
            time.sleep(0.5)
        
        return success_count
    
    def run(self, cancel_existing=True):
        """
        Run the OrderBookMakerStrategy.
        
        Args:
            cancel_existing (bool): Whether to cancel existing orders before placing new ones
            
        Returns:
            dict: Summary of the strategy run
        """
        logger.info(f"Running OrderBookMakerStrategy for {self.base_symbol}/{self.quote_symbol}...")
        
        # Check initial balances
        initial_base_balance, initial_quote_balance = self.check_balances()
        
        # Cancel existing orders if requested
        if cancel_existing:
            self.cancel_existing_orders()
        
        # Generate order prices
        sell_prices, buy_prices = self.generate_order_prices()
        
        # Generate order quantities
        sell_orders = self.generate_order_quantities(sell_prices, 'sell')
        buy_orders = self.generate_order_quantities(buy_prices, 'buy')
        
        # Place sell orders
        sell_success_count = self.place_orders(sell_orders, 'sell')
        
        # Place buy orders
        buy_success_count = self.place_orders(buy_orders, 'buy')
        
        # Check final balances
        final_base_balance, final_quote_balance = self.check_balances()
        
        # Calculate balance changes
        try:
            base_balance_change = float(initial_base_balance.split()[0]) - float(final_base_balance.split()[0])
            quote_balance_change = float(initial_quote_balance.split()[0]) - float(final_quote_balance.split()[0])
        except (ValueError, IndexError):
            base_balance_change = "Unable to calculate"
            quote_balance_change = "Unable to calculate"
        
        # Print summary
        logger.info(f"\nOrderBookMakerStrategy Summary:")
        logger.info(f"Sell Orders: {sell_success_count}/{len(sell_orders)} placed successfully")
        logger.info(f"Buy Orders: {buy_success_count}/{len(buy_orders)} placed successfully")
        logger.info(f"{self.base_symbol} Balance Change: {base_balance_change}")
        logger.info(f"{self.quote_symbol} Balance Change: {quote_balance_change}")
        
        return {
            "sell_success": sell_success_count,
            "buy_success": buy_success_count,
            "total_orders": len(sell_orders) + len(buy_orders),
            "base_balance_change": base_balance_change,
            "quote_balance_change": quote_balance_change
        }

def load_config(config_path='config/config.yaml'):
    """Load configuration from YAML file."""
    try:
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)
        return config
    except Exception as e:
        logger.error(f"Error loading config: {str(e)}")
        # Use default values if config can't be loaded
        return {
            "strategies": {
                "LIBRE/BTC": {
                    "min_order_value_libre": 100.0000,
                    "max_order_value_libre": 1000.0000,
                    "min_order_value_btc": 0.00001000,
                    "max_order_value_btc": 0.00100000
                }
            }
        }

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Run OrderBookMakerStrategy')
    parser.add_argument('--account', type=str, default='bentest3', help='Account to use for trading')
    parser.add_argument('--base', type=str, default='LIBRE', help='Base currency symbol')
    parser.add_argument('--quote', type=str, default='BTC', help='Quote currency symbol')
    parser.add_argument('--config', type=str, default='config/config.yaml', help='Path to config file')
    parser.add_argument('--no-cancel', action='store_true', help='Do not cancel existing orders')
    args = parser.parse_args()
    
    # Load configuration
    config = load_config(args.config)
    
    # Initialize client
    logger.info("Initializing LibreClient...")
    client = LibreClient(network='testnet', verbose=True)
    
    # Initialize strategy
    strategy = OrderBookMakerStrategy(
        client=client,
        config=config,
        account=args.account,
        base_symbol=args.base,
        quote_symbol=args.quote
    )
    
    # Run strategy
    result = strategy.run(cancel_existing=not args.no_cancel)
    
    logger.info(f"\nStrategy completed with {result['sell_success'] + result['buy_success']}/{result['total_orders']} orders placed successfully")

if __name__ == "__main__":
    main() 