#!/usr/bin/env python3

import os
import sys
import yaml
import ccxt
import time
import datetime  # Add datetime module for order age calculation
from datetime import datetime, timedelta  # Add timedelta for age calculation
from typing import Dict, List, Tuple
from decimal import Decimal

# Add the parent directory to Python path to import pylibre
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.pylibre import LibreClient
from src.pylibre.dex import DexClient

class StrategyMonitor:
    def __init__(self):
        # Load strategies config
        with open('config/strategies.mainnet.yaml', 'r') as f:
            self.config = yaml.safe_load(f)
        
        # Get account from config
        self.account = self.config['accounts']['BTCUSDT']['liquidity_provider']
        
        # Initialize clients
        self.client = LibreClient(
            api_url=self.config['api_endpoint'],
            network='mainnet',
            config_path='config/config.yaml',
            verbose=True
        )
        self.dex = DexClient(self.client)
        self.binance = ccxt.binance()
        
        # Cleanup parameters
        self.batch_size = 5  # Reduced from 10 to 5 orders per batch
        self.delay_ms = 1000  # Increased from 200ms to 1000ms between batches
        self.max_retries = 3  # Maximum number of retries for failed cancellations
        self.retry_delay_ms = 2000  # Delay between retries in milliseconds
        
        # Price alignment settings
        self.price_alignment_threshold = 1.0  # 1% threshold for price alignment
        self.use_oracle_price = True  # Use oracle price as reference if available
        
    def get_binance_price(self, symbol: str) -> float:
        """Get current price from Binance"""
        ticker = self.binance.fetch_ticker(symbol)
        return float(ticker['last'])
    
    def get_oracle_price(self, symbol: str) -> float:
        """Get oracle price from Chainlink on Libre"""
        try:
            # Extract base and quote symbols
            base_symbol = symbol[:3].lower()  # btc
            quote_symbol = symbol[3:].lower()  # usdt
            
            # Get oracle price from Chainlink
            try:
                response = self.client.get_table_rows(
                    code="chainlink",
                    scope="chainlink",
                    table="feed",
                    limit=100
                )
                
                if not response.get('success', False):
                    print(f"Oracle data retrieval failed: {response.get('error', 'Unknown error')}")
                    print("Falling back to Binance price")
                    return self.get_binance_price(symbol)
                
                # Find the relevant price feed
                target_pair = f"{base_symbol}usd"  # btcusd
                
                for feed in response.get('rows', []):
                    pair = feed.get('pair', '')
                    if pair == target_pair:
                        # Extract price from the feed
                        price_value = float(feed.get('price', 0))
                        if price_value > 0:
                            print(f"Using Chainlink oracle price for {pair}: ${price_value:.2f}")
                            return price_value
                
                # If we couldn't find a matching price feed
                print(f"No matching Chainlink oracle price feed found for {target_pair}")
                print("Falling back to Binance price")
                return self.get_binance_price(symbol)
                
            except Exception as e:
                print(f"Error accessing oracle data: {e}")
                print("Falling back to Binance price")
                return self.get_binance_price(symbol)
                
        except Exception as e:
            print(f"Error fetching oracle price: {e}")
            print("Falling back to Binance price")
            return self.get_binance_price(symbol)
    
    def get_libre_orders(self, symbol: str) -> Tuple[List[Dict], float]:
        """Get current orders and market price from Libre"""
        # Split symbol into base and quote (e.g. BTCUSDT -> BTC, USDT)
        base_symbol = symbol[:3]  # BTC
        quote_symbol = symbol[3:]  # USDT
        
        # Get orderbook from DEX
        orderbook = self.dex.fetch_order_book(quote_symbol=quote_symbol, base_symbol=base_symbol)
        
        # Parse orders into bids and asks
        bids = []
        asks = []
        
        # Process bids
        for bid in orderbook.get('bids', []):
            price = float(bid['price'])
            amount = float(bid['quantity'])
            account = bid.get('account', 'unknown')
            bids.append({'price': price, 'amount': amount, 'account': account, 'type': 'bid'})
            
        # Process asks
        for ask in orderbook.get('offers', []):
            price = float(ask['price'])
            amount = float(ask['quantity'])
            account = ask.get('account', 'unknown')
            asks.append({'price': price, 'amount': -amount, 'account': account, 'type': 'offer'})  # Negative amount for asks
        
        # Sort bids (descending) and asks (ascending)
        bids.sort(key=lambda x: x['price'], reverse=True)
        asks.sort(key=lambda x: x['price'])
        
        # Calculate market price as mid-point
        if bids and asks:
            market_price = (bids[0]['price'] + asks[0]['price']) / 2
        else:
            market_price = 0
            
        return bids + asks, market_price
    
    def fast_cancel_orders(self, symbol: str) -> Dict:
        """Cancel all orders for the account using the optimized DexClient method"""
        # Split symbol into base and quote
        base_symbol = symbol[:3]
        quote_symbol = symbol[3:]
        
        print(f"🚀 Fast cancelling ALL orders for {self.account} ({base_symbol}/{quote_symbol})...")
        
        # Fetch all orders first
        order_book = self.dex.fetch_order_book(
            quote_symbol=quote_symbol,
            base_symbol=base_symbol
        )
        
        # Build a list of our orders
        orders_to_cancel = []
        
        # Add bids
        for bid in order_book.get("bids", []):
            if bid["account"] == self.account:
                orders_to_cancel.append({
                    "type": "bid",
                    "price": float(bid["price"]),
                    "identifier": bid["identifier"]
                })
        
        # Add offers
        for offer in order_book.get("offers", []):
            if offer["account"] == self.account:
                orders_to_cancel.append({
                    "type": "offer",
                    "price": float(offer["price"]),
                    "identifier": offer["identifier"]
                })
        
        total_orders = len(orders_to_cancel)
        if total_orders == 0:
            print("No orders found to cancel")
            return {"success": True, "successful": 0, "failed": 0, "total_orders": 0}
        
        print(f"Found {total_orders} orders to cancel")
        
        # Optimized batch parameters to reduce rejections
        batch_size = 3  # Smaller batch size to avoid overwhelming the API
        delay_ms = 500  # Longer delay between batches
        
        # Track results
        cancelled_orders = 0
        failed_orders = 0
        start_time = time.time()
        
        # Process in batches with delay between batches
        for i in range(0, total_orders, batch_size):
            batch = orders_to_cancel[i:i+batch_size]
            
            # Log batch progress
            batch_num = (i // batch_size) + 1
            total_batches = (total_orders + batch_size - 1) // batch_size
            print(f"Processing batch {batch_num}/{total_batches} ({len(batch)} orders)")
            
            # Process each order in the batch
            for order in batch:
                try:
                    # Cancel with retry logic for robustness
                    for retry in range(2):  # Try up to 2 times
                        try:
                            result = self.dex.cancel_order(
                                account=self.account,
                                order_id=order["identifier"],
                                quote_symbol=quote_symbol,
                                base_symbol=base_symbol
                            )
                            
                            if result.get("success", False):
                                cancelled_orders += 1
                                print(f"✓ Cancelled {order['type']} order at price {order['price']}")
                                break  # Exit retry loop on success
                            else:
                                error = result.get("error", "Unknown error")
                                print(f"✗ Attempt {retry+1}: Failed to cancel {order['type']} order: {error}")
                                if retry < 1:  # Only wait if we're going to retry
                                    time.sleep(0.5)  # Short delay before retry
                        except Exception as e:
                            print(f"✗ Attempt {retry+1}: Error cancelling {order['type']} order: {e}")
                            if retry < 1:  # Only wait if we're going to retry
                                time.sleep(0.5)  # Short delay before retry
                    
                    # If we got here and didn't break out of the retry loop, count as failed
                    if retry == 1:  # Means we exhausted retries without success
                        failed_orders += 1
                except Exception as e:
                    failed_orders += 1
                    print(f"✗ Error in retry logic: {e}")
            
            # Add delay between batches to avoid rate limiting
            if i + batch_size < total_orders:
                time.sleep(delay_ms / 1000)
        
        duration = time.time() - start_time
        
        # Print summary statistics
        print(f"✅ Cancelled {cancelled_orders} orders in {duration:.2f} seconds")
        if failed_orders > 0:
            print(f"⚠️ {failed_orders} orders failed to cancel")
            
        return {
            "success": True,
            "successful": cancelled_orders,
            "failed": failed_orders,
            "total_orders": total_orders
        }
    
    def check_order_age_limits(self, symbol: str) -> int:
        """Check for and cancel orders older than the configured age limit
        
        Args:
            symbol: Trading pair symbol (e.g., BTCUSDT)
            
        Returns:
            int: Number of orders cancelled due to age
        """
        # Split symbol into base and quote
        base_symbol = symbol[:3]
        quote_symbol = symbol[3:]
        
        # Get age limit from config
        strategy_group = symbol[:3] + symbol[3:]  # e.g., BTCUSDT
        max_age_hours = self.config.get('strategy_groups', {}).get(strategy_group, {}).get('max_order_age_hours', 24)
        
        print(f"Checking for orders older than {max_age_hours} hours for {self.account}...")
        
        # Get detailed order history to check age
        try:
            # First try the most commonly used scope format
            orders_response = self.client.get_table_rows(
                code="dex.libre",
                scope=f"{quote_symbol}:{base_symbol}",
                table="orders",
                limit=1000
            )
            
            # If that fails, try alternative scope formats
            if not orders_response.get('success', False):
                print(f"First scope format failed, trying alternative format...")
                orders_response = self.client.get_table_rows(
                    code="dex.libre",
                    scope=f"{base_symbol}{quote_symbol}",
                    table="orders",
                    limit=1000
                )
                
            # If that still fails, try yet another alternative
            if not orders_response.get('success', False):
                print(f"Second scope format failed, trying last alternative...")
                orders_response = self.client.get_table_rows(
                    code="dex.libre",
                    scope="dex.libre",
                    table="orders",
                    limit=1000
                )
            
            # If we still can't get the order history, fall back to using active orders
            if not orders_response.get('success', False):
                print(f"Could not retrieve order history. Falling back to active orders...")
                # Use the current order book to check for old orders (less accurate but better than nothing)
                orders, dex_price = self.get_libre_orders(symbol)
                our_orders = [order for order in orders if order['account'] == self.account]
                
                print(f"Found {len(our_orders)} active orders, but cannot determine their age")
                print(f"To maintain system health, will cancel up to 10% oldest-looking orders")
                
                # Without timestamp info, we'll estimate age based on how far they are from current price
                if our_orders and dex_price:
                    # Sort orders by distance from current price (potential proxy for age)
                    our_orders.sort(key=lambda x: abs(x['price'] - dex_price), reverse=True)
                    
                    # Select up to 10% of orders that seem oldest (furthest from current price)
                    oldest_count = max(1, int(len(our_orders) * 0.1))
                    potential_old_orders = our_orders[:oldest_count]
                    
                    # Cancel these orders
                    cancelled_count = 0
                    for order in potential_old_orders:
                        try:
                            order_type = 'bid' if order['amount'] > 0 else 'offer'
                            identifier = order.get('identifier', order.get('order_id', None))
                            if not identifier:
                                continue
                                
                            result = self.dex.cancel_order(
                                account=self.account,
                                order_id=identifier,
                                quote_symbol=quote_symbol,
                                base_symbol=base_symbol
                            )
                            
                            if result.get("success", False):
                                cancelled_count += 1
                                print(f"✓ Cancelled {order_type} order at price {order['price']} (estimated old)")
                        except Exception as e:
                            print(f"Error cancelling potentially old order: {e}")
                    
                    print(f"✅ Cancelled {cancelled_count} potentially old orders")
                    return cancelled_count
                else:
                    print("No active orders found or cannot determine DEX price")
                    return 0
                
            # Process actual order history if we successfully retrieved it
            print(f"Successfully retrieved order history with {len(orders_response.get('rows', []))} orders")
            
            # Filter to our account's orders
            our_orders = []
            now = datetime.now()
            cutoff_time = now - timedelta(hours=max_age_hours)
            
            for order in orders_response.get('rows', []):
                if order.get('account') == self.account:
                    # Convert blockchain timestamp to datetime
                    # Format is typically like "2025-04-12T15:30:45"
                    try:
                        # Extract timestamp from different possible fields
                        timestamp = order.get('timestamp') or order.get('created_at') or order.get('time')
                        if timestamp:
                            # Sometimes the format includes microseconds, sometimes not
                            try:
                                order_time = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S")
                            except ValueError:
                                try:
                                    order_time = datetime.strptime(timestamp.split('.')[0], "%Y-%m-%dT%H:%M:%S")
                                except (ValueError, IndexError):
                                    # Fallback: if we can't parse the time, assume it's old
                                    print(f"Couldn't parse timestamp: {timestamp}, assuming old order")
                                    order_time = cutoff_time - timedelta(hours=1)
                            
                            # Check if order is older than cutoff
                            if order_time < cutoff_time:
                                order_age = now - order_time
                                print(f"Found old {order.get('type', 'unknown')} order at price {order.get('price')}: {order_age.total_seconds() / 3600:.1f} hours old")
                                our_orders.append({
                                    "type": order.get('type', 'unknown'),
                                    "identifier": order.get('id'),
                                    "price": float(order.get('price', 0)),
                                    "age_hours": order_age.total_seconds() / 3600
                                })
                    except Exception as e:
                        print(f"Error parsing order timestamp: {e}")
                        continue
            
            # If no old orders found, return
            if not our_orders:
                print("No orders found older than the age limit")
                return 0
                
            print(f"Found {len(our_orders)} orders older than {max_age_hours} hours")
            
            # Sort orders by age (oldest first)
            our_orders.sort(key=lambda x: x.get('age_hours', 0), reverse=True)
            
            # Process in optimal batch size with delay between batches
            batch_size = 3  # Same as fast_cancel_orders 
            delay_ms = 500
            
            # Track results
            cancelled_count = 0
            failed_count = 0
            
            # Cancel orders in batches
            for i in range(0, len(our_orders), batch_size):
                batch = our_orders[i:i+batch_size]
                
                # Log batch progress
                batch_num = (i // batch_size) + 1
                total_batches = (len(our_orders) + batch_size - 1) // batch_size
                print(f"Processing age limit batch {batch_num}/{total_batches} ({len(batch)} orders)")
                
                # Process each order in the batch
                for order in batch:
                    try:
                        # Use the same robust cancellation logic with retries
                        for retry in range(2):
                            try:
                                result = self.dex.cancel_order(
                                    account=self.account,
                                    order_id=order["identifier"],
                                    quote_symbol=quote_symbol,
                                    base_symbol=base_symbol
                                )
                                
                                if result.get("success", False):
                                    cancelled_count += 1
                                    age_str = f"{order.get('age_hours', 0):.1f} hours old"
                                    print(f"✓ Cancelled {order.get('type')} order at price {order.get('price')} ({age_str})")
                                    break
                                else:
                                    error = result.get("error", "Unknown error")
                                    print(f"✗ Attempt {retry+1}: Failed to cancel old order: {error}")
                                    if retry < 1:
                                        time.sleep(0.5)
                            except Exception as e:
                                print(f"✗ Attempt {retry+1}: Error cancelling old order: {e}")
                                if retry < 1:
                                    time.sleep(0.5)
                                    
                        # Count as failed if we exhausted retries
                        if retry == 1:
                            failed_count += 1
                    except Exception as e:
                        failed_count += 1
                        print(f"✗ Error in retry logic: {e}")
                
                # Add delay between batches
                if i + batch_size < len(our_orders):
                    time.sleep(delay_ms / 1000)
            
            # Print summary
            print(f"✅ Cancelled {cancelled_count} old orders ({failed_count} failed)")
            return cancelled_count
            
        except Exception as e:
            print(f"Error checking order age limits: {e}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            return 0

    def cleanup_excess_orders(self, symbol: str, max_orders: int) -> int:
        """Clean up excess orders if we have more than max_orders, focusing on aligning price with oracle"""
        # Split symbol into base and quote
        base_symbol = symbol[:3]
        quote_symbol = symbol[3:]
        
        def get_order_book_details():
            """Get detailed order book information and our orders"""
            # Get current orderbook
            orderbook = self.dex.fetch_order_book(quote_symbol=quote_symbol, base_symbol=base_symbol)
            
            # Count our orders and analyze the order book
            our_orders = []
            all_bids = []
            all_asks = []
            
            # Process bids
            for bid in orderbook.get('bids', []):
                bid_price = float(bid['price'])
                bid_quantity = float(bid['quantity'])
                all_bids.append({'price': bid_price, 'quantity': bid_quantity, 'account': bid.get('account')})
                
                if bid['account'] == self.account:
                    our_orders.append({
                        'type': 'bid',
                        'identifier': bid['identifier'],
                        'price': bid_price,
                        'quantity': bid_quantity
                    })
            
            # Process asks
            for ask in orderbook.get('offers', []):
                ask_price = float(ask['price'])
                ask_quantity = float(ask['quantity'])
                all_asks.append({'price': ask_price, 'quantity': ask_quantity, 'account': ask.get('account')})
                
                if ask['account'] == self.account:
                    our_orders.append({
                        'type': 'offer',
                        'identifier': ask['identifier'],
                        'price': ask_price,
                        'quantity': ask_quantity
                    })
            
            # Sort for analysis
            all_bids.sort(key=lambda x: x['price'], reverse=True)  # Highest bids first
            all_asks.sort(key=lambda x: x['price'])                # Lowest asks first
            
            # Calculate current DEX price
            dex_price = None
            if all_bids and all_asks:
                best_bid = all_bids[0]['price']
                best_ask = all_asks[0]['price']
                dex_price = (best_bid + best_ask) / 2
            
            return our_orders, all_bids, all_asks, dex_price, orderbook
        
        # Get oracle price as our reference
        oracle_price = self.get_oracle_price(symbol)
        print(f"Using Chainlink oracle price as reference: ${oracle_price:.2f}")
        
        # Get initial orders and order book details
        our_orders, all_bids, all_asks, dex_price, orderbook = get_order_book_details()
        
        # If we don't have excess orders, nothing to do
        if len(our_orders) <= max_orders:
            print(f"Account has {len(our_orders)} orders, within limit of {max_orders}")
            return 0
            
        # Calculate how many orders we need to cancel
        excess_count = len(our_orders) - max_orders
        print(f"Need to cancel {excess_count} orders to reach max of {max_orders}")
        
        # Determine the price alignment direction
        if dex_price and oracle_price:
            price_gap = oracle_price - dex_price
            price_gap_percent = price_gap / oracle_price * 100
            
            if price_gap > 0:
                print(f"DEX price (${dex_price:.2f}) is LOWER than oracle (${oracle_price:.2f}) by ${price_gap:.2f} ({price_gap_percent:.2f}%)")
                print(f"Direction: MOVE PRICE UP - prioritize cancelling low bids and high asks")
                # Calculate the ratio of bids vs asks to cancel based on the gap size
                # The bigger the gap, the more we focus on moving price in that direction
                ratio_factor = min(abs(price_gap_percent) / 10, 0.8)  # Cap at 80/20 ratio
                bids_ratio = 0.5 + ratio_factor / 2
                asks_ratio = 1 - bids_ratio
            else:
                print(f"DEX price (${dex_price:.2f}) is HIGHER than oracle (${oracle_price:.2f}) by ${-price_gap:.2f} ({-price_gap_percent:.2f}%)")
                print(f"Direction: MOVE PRICE DOWN - prioritize cancelling high asks and low bids")
                # Calculate the ratio of asks vs bids to cancel based on the gap size
                ratio_factor = min(abs(price_gap_percent) / 10, 0.8)  # Cap at 80/20 ratio
                asks_ratio = 0.5 + ratio_factor / 2
                bids_ratio = 1 - asks_ratio
                
            # Calculate actual numbers to cancel from each side
            bids_to_cancel = round(excess_count * bids_ratio)
            asks_to_cancel = excess_count - bids_to_cancel
            
            print(f"Cancellation ratio: {bids_to_cancel}/{asks_to_cancel} ({bids_ratio*100:.1f}%/{asks_ratio*100:.1f}%)")
        else:
            # If we can't determine direction, cancel evenly from both sides
            bids_to_cancel = excess_count // 2
            asks_to_cancel = excess_count - bids_to_cancel
            print(f"No price direction - cancelling equally from both sides: {bids_to_cancel} bids, {asks_to_cancel} asks")
            
        # Separate our orders into bids and asks
        our_bids = [order for order in our_orders if order['type'] == 'bid']
        our_asks = [order for order in our_orders if order['type'] == 'offer']
        
        # Sort our bids and asks by how much they're helping/hurting the alignment
        # For moving price UP: Cancel lowest bids first
        # For moving price DOWN: Cancel highest asks first
        if price_gap > 0:  # Move price UP
            our_bids.sort(key=lambda x: x['price'])  # Sort bids by price, lowest first
            our_asks.sort(key=lambda x: x['price'], reverse=True)  # Sort asks by price, highest first
        else:  # Move price DOWN
            our_asks.sort(key=lambda x: x['price'])  # Sort asks by price, lowest first
            our_bids.sort(key=lambda x: x['price'], reverse=True)  # Sort bids by price, highest first
            
        # Build list of orders to cancel
        orders_to_cancel = []
        
        # Add bids to cancel
        for i, bid in enumerate(our_bids):
            if i < bids_to_cancel:
                # Calculate distance from DEX and oracle prices for context
                distance_from_dex = dex_price - bid['price']
                distance_from_oracle = oracle_price - bid['price']
                direction_help = "to help move price UP" if price_gap > 0 else "to help move price DOWN"
                print(f"Marking BID at ${bid['price']:.2f} for cancellation - ${distance_from_dex:.2f} from DEX price, ${distance_from_oracle:.2f} from oracle {direction_help}")
                orders_to_cancel.append(bid)
        
        # Add asks to cancel  
        for i, ask in enumerate(our_asks):
            if i < asks_to_cancel:
                # Calculate distance from DEX and oracle prices for context
                distance_from_dex = ask['price'] - dex_price
                distance_from_oracle = ask['price'] - oracle_price
                direction_help = "to help move price UP" if price_gap > 0 else "to help move price DOWN"
                print(f"Marking ASK at ${ask['price']:.2f} for cancellation - ${distance_from_dex:.2f} from DEX price, ${distance_from_oracle:.2f} from oracle {direction_help}")
                orders_to_cancel.append(ask)
                
        # Optimized batch parameters to reduce rejections
        batch_size = 3  # Smaller batch size to avoid overwhelming the API
        delay_ms = 500  # Longer delay between batches
        
        # Track results
        cancelled_count = 0
        failed_count = 0
        
        # Process in batches with delay between batches
        for i in range(0, len(orders_to_cancel), batch_size):
            batch = orders_to_cancel[i:i+batch_size]
            
            # Log batch progress
            batch_num = (i // batch_size) + 1
            total_batches = (len(orders_to_cancel) + batch_size - 1) // batch_size
            print(f"Processing batch {batch_num}/{total_batches} ({len(batch)} orders)")
            
            # Process each order in the batch
            for order in batch:
                try:
                    # Cancel with retry logic for robustness
                    for retry in range(2):  # Try up to 2 times
                        try:
                            result = self.dex.cancel_order(
                                account=self.account,
                                order_id=order["identifier"],
                                quote_symbol=quote_symbol,
                                base_symbol=base_symbol
                            )
                            
                            if result.get("success", False):
                                cancelled_count += 1
                                print(f"✓ Cancelled {order['type']} order at price {order['price']}")
                                break  # Exit retry loop on success
                            else:
                                error = result.get("error", "Unknown error")
                                print(f"✗ Attempt {retry+1}: Failed to cancel {order['type']} order: {error}")
                                if retry < 1:  # Only wait if we're going to retry
                                    time.sleep(0.5)  # Short delay before retry
                        except Exception as e:
                            print(f"✗ Attempt {retry+1}: Error cancelling {order['type']} order: {e}")
                            if retry < 1:  # Only wait if we're going to retry
                                time.sleep(0.5)  # Short delay before retry
                    
                    # If we got here and didn't break out of the retry loop, count as failed
                    if retry == 1:  # Means we exhausted retries without success
                        failed_count += 1
                except Exception as e:
                    failed_count += 1
                    print(f"✗ Error in retry logic: {e}")
            
            # Add delay between batches to avoid rate limiting
            if i + batch_size < len(orders_to_cancel):
                time.sleep(delay_ms / 1000)
                
            # Refresh order book after each batch to adapt to changing conditions
            if i + batch_size < len(orders_to_cancel):
                print("Refreshing order book to adapt to changes...")
                our_orders, all_bids, all_asks, dex_price, orderbook = get_order_book_details()
                if dex_price:
                    print(f"Updated DEX price: ${dex_price:.2f} (gap: ${abs(oracle_price - dex_price):.2f})")
        
        # Print summary
        print(f"✅ Cancelled {cancelled_count} orders ({failed_count} failed)")
        
        # Return number of cancelled orders
        return cancelled_count
    
    def analyze_market(self, symbol: str) -> Dict:
        """Analyze the market and perform necessary actions"""
        # First check for and cancel orders that exceed the age limit
        age_cancelled = self.check_order_age_limits(symbol)
        
        # Get oracle price as reference
        oracle_price = self.get_oracle_price(symbol)
        
        # Get DEX orders and market price
        orders, dex_price = self.get_libre_orders(symbol)
        
        # Filter orders to get only our account's orders
        our_orders = [order for order in orders if order['account'] == self.account]
        
        # Get configured maximum orders for this symbol
        strategy_group = symbol[:3] + symbol[3:]  # e.g., BTCUSDT
        max_orders = self.config.get('strategy_groups', {}).get(strategy_group, {}).get('num_orders', 100)
        
        # Count our orders and check against maximum
        order_count = len(our_orders)
        excess_orders = max(0, order_count - max_orders)
        
        # Determine market stats
        bids = [order for order in orders if order['amount'] > 0]  # Positive amount for bids
        asks = [order for order in orders if order['amount'] < 0]  # Negative amount for asks
        
        # Prepare report
        report = {
            'symbol': symbol,
            'oracle_price': oracle_price,
            'dex_price': dex_price,
            'price_gap': oracle_price - dex_price if oracle_price and dex_price else None,
            'price_gap_percent': ((oracle_price / dex_price) - 1) * 100 if oracle_price and dex_price and dex_price > 0 else None,
            'order_count': order_count,
            'max_orders': max_orders,
            'excess_orders': excess_orders,
            'bid_count': len(bids),
            'ask_count': len(asks),
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'age_cancelled': age_cancelled
        }
        
        # If we cancelled a significant number of old orders, skip excess cleanup this cycle
        if age_cancelled > max_orders * 0.1:  # If we cancelled more than 10% of max allowed
            print(f"Skipping excess order cleanup this cycle after cancelling {age_cancelled} old orders")
            report['cancelled_orders'] = age_cancelled
            report['cancellation_method'] = 'age_limit'
            return report
        
        # Clean up excess orders if needed
        if excess_orders > 0:
            print(f"🧹 Account has {order_count} orders, exceeding max {max_orders} by {excess_orders}")
            
            # Check if the excess is severe (more than 20% over limit)
            if excess_orders > max_orders * 0.2:
                print(f"⚠️ Severe excess detected ({excess_orders} orders over limit)")
                print(f"🚫 Performing fast cancellation of ALL orders to reset")
                
                # Use fast cancellation for severe excess
                cancel_result = self.fast_cancel_orders(symbol)
                cancelled_count = cancel_result.get('successful', 0)
                report['cancelled_orders'] = cancelled_count
                report['cancellation_method'] = 'fast_cancel_all'
                
                print(f"✅ Fast cancelled {cancelled_count} orders")
                return report
            else:
                # Use normal cleanup for moderate excess
                cancelled_count = self.cleanup_excess_orders(symbol, max_orders)
                report['cancelled_orders'] = cancelled_count
                report['cancellation_method'] = 'prioritized_cleanup'
                
                print(f"✅ Strategically cancelled {cancelled_count} excess orders")
        else:
            print(f"✅ Account has {order_count} orders, within max {max_orders}")
            report['cancelled_orders'] = 0
            report['cancellation_method'] = 'none_needed'
            
        return report

    def print_report(self, analysis: Dict):
        """Print formatted analysis report"""
        print("\n=== Strategy Monitor Report ===")
        print(f"Time: {analysis['timestamp']}")
        print(f"Symbol: {analysis['symbol']}")
        print(f"\nPrices:")
        print(f"  Oracle: ${analysis['oracle_price']:.2f}")
        print(f"  DEX:    ${analysis['dex_price']:.2f}")
        
        if analysis.get('price_gap') is not None:
            price_gap = analysis['price_gap']
            price_gap_percent = analysis['price_gap_percent']
            direction = "HIGHER" if price_gap < 0 else "LOWER"
            print(f"  Gap:    ${abs(price_gap):.2f} ({abs(price_gap_percent):.2f}%)")
            print(f"  Status: DEX price is {direction} than oracle price")
        
        print(f"\nOrders:")
        print(f"  Our Orders: {analysis['order_count']}")
        print(f"  Max Allowed: {analysis['max_orders']}")
        print(f"  Bids: {analysis['bid_count']}")
        print(f"  Asks: {analysis['ask_count']}")
        
        if analysis.get('age_cancelled', 0) > 0:
            print(f"  Age Cancelled: {analysis['age_cancelled']} (older than limit)")
            
        if analysis.get('cancelled_orders', 0) > 0:
            print(f"\nCancellations:")
            print(f"  Method: {analysis.get('cancellation_method', 'unknown')}")
            print(f"  Count: {analysis['cancelled_orders']}")

def main():
    """Main function to run strategy monitor"""
    try:
        monitor = StrategyMonitor()
        symbol = 'BTCUSDT'  # Hardcoded for now, could make configurable
        
        # Sleep interval in seconds
        interval = 30
        
        # Always run at least once
        analysis = monitor.analyze_market(symbol)
        monitor.print_report(analysis)
        
        # Continue running in a loop
        print(f"\nMonitor will check again in {interval} seconds. Press Ctrl+C to exit.")
        
        try:
            while True:
                # Wait for next check
                time.sleep(interval)
                
                # Analyze and report
                analysis = monitor.analyze_market(symbol)
                monitor.print_report(analysis)
                
                print(f"\nMonitor will check again in {interval} seconds. Press Ctrl+C to exit.")
        except KeyboardInterrupt:
            print("\nMonitor stopped by user.")
    except Exception as e:
        print(f"Error in monitor: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 