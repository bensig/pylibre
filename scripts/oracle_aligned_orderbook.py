#!/usr/bin/env python3
"""
Script to maintain an orderbook aligned with Chainlink oracle prices.
This script focuses on:
1. Maintaining exactly 15 bids and 15 offers (30 total orders)
2. Ensuring the DEX mid-price stays close to the Chainlink oracle price
3. Cancelling excess orders before creating new ones
4. Operating independently from the animator script
"""

import os
import sys
import yaml
import time
import random
from decimal import Decimal
from typing import Dict, List, Tuple, Any, Optional

# Add the src directory to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.pylibre import LibreClient
from src.pylibre.dex import DexClient

class OracleAlignedOrderbookManager:
    def __init__(self, run_once=False):
        """Initialize the orderbook manager with configuration."""
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
        
        # Get orderbook parameters from config or use defaults
        strategy_config = self.config.get('strategies', {}).get('BTCUSDT', {})
        self.orders_per_side = strategy_config.get('num_orders', 15) # Get from config or default to 15
        self.min_spread_percentage = Decimal(str(strategy_config.get('min_spread', 0.005)))  # 0.5% minimum spread
        self.max_spread_percentage = Decimal(str(strategy_config.get('max_spread', 0.03)))   # 3% maximum spread
        self.batch_size = 3  # Process 3 orders at a time
        self.batch_delay_ms = 500  # Delay between batches
        
        # Time between full orderbook refreshes (in seconds)
        self.refresh_interval = strategy_config.get('refresh_interval', 180)  # 3 minutes by default
        
        # Track the last known prices
        self.oracle_price = None
        self.dex_price = None
        
        # Option to run once instead of looping
        self.run_once = run_once
        
        print(f"Initialized OrderbookManager for account {self.account}")
        print(f"Maintaining {self.orders_per_side} orders per side ({self.orders_per_side * 2} total)")

    def get_oracle_price(self) -> Optional[Decimal]:
        """Get the current BTC/USD price from Chainlink oracle."""
        try:
            # Get oracle price from Chainlink
            response = self.client.get_table_rows(
                code="chainlink",
                scope="chainlink",
                table="feed",
                limit=100
            )
            
            if not response.get('success', False):
                print(f"Oracle data retrieval failed: {response.get('error', 'Unknown error')}")
                return None
            
            # Find the BTC/USD price feed
            target_pair = "btcusd"
            
            for feed in response.get('rows', []):
                pair = feed.get('pair', '')
                if pair == target_pair:
                    # Extract price from the feed
                    price_value = Decimal(str(feed.get('price', 0)))
                    if price_value > 0:
                        print(f"Chainlink oracle price for BTC/USD: ${price_value}")
                        self.oracle_price = price_value
                        return price_value
            
            # If we couldn't find a matching price feed
            print(f"No matching Chainlink oracle price feed found for {target_pair}")
            return None
            
        except Exception as e:
            print(f"Error fetching oracle price: {e}")
            return None

    def get_current_orderbook(self) -> Tuple[List[Dict], List[Dict], Optional[Decimal]]:
        """Get the current orderbook and calculate mid-market price."""
        try:
            # Get orderbook from DEX
            orderbook = self.dex.fetch_order_book(
                quote_symbol="USDT",
                base_symbol="BTC"
            )
            
            our_bids = []
            our_asks = []
            all_bids = []
            all_asks = []
            
            # Process bids
            for bid in orderbook.get('bids', []):
                bid_price = Decimal(str(bid['price']))
                bid_quantity = Decimal(str(bid['quantity']))
                all_bids.append({
                    'price': bid_price, 
                    'quantity': bid_quantity, 
                    'account': bid.get('account'),
                    'identifier': bid.get('identifier')
                })
                
                if bid['account'] == self.account:
                    our_bids.append({
                        'type': 'bid',
                        'identifier': bid['identifier'],
                        'price': bid_price,
                        'quantity': bid_quantity
                    })
            
            # Process asks
            for ask in orderbook.get('offers', []):
                ask_price = Decimal(str(ask['price']))
                ask_quantity = Decimal(str(ask['quantity']))
                all_asks.append({
                    'price': ask_price, 
                    'quantity': ask_quantity, 
                    'account': ask.get('account'),
                    'identifier': ask.get('identifier')
                })
                
                if ask['account'] == self.account:
                    our_asks.append({
                        'type': 'offer',
                        'identifier': ask['identifier'],
                        'price': ask_price,
                        'quantity': ask_quantity
                    })
            
            # Sort all orders by price
            all_bids.sort(key=lambda x: x['price'], reverse=True)  # Highest price first
            all_asks.sort(key=lambda x: x['price'])  # Lowest price first
            
            # Sort our orders by price
            our_bids.sort(key=lambda x: x['price'], reverse=True)  # Highest price first
            our_asks.sort(key=lambda x: x['price'])  # Lowest price first
            
            # Calculate current DEX price as mid-point
            dex_price = None
            
            if all_bids and all_asks:
                # Get best bid and ask (closest to the mid-market)
                best_bid = all_bids[0]['price'] if all_bids else None
                best_ask = all_asks[0]['price'] if all_asks else None
                
                # Log details about the best bid and ask
                if best_bid:
                    bid_info = all_bids[0]
                    print(f"Best bid: ${best_bid} (ID: {bid_info['identifier']}, Account: {bid_info['account']})")
                
                if best_ask:
                    ask_info = all_asks[0]
                    print(f"Best ask: ${best_ask} (ID: {ask_info['identifier']}, Account: {ask_info['account']})")
                
                if best_bid and best_ask:
                    # Calculate simple mid-market price
                    dex_price = (best_bid + best_ask) / 2
                    self.dex_price = dex_price
                    print(f"DEX mid-market price: ${dex_price}")
                    
                    # Calculate spread
                    spread_abs = best_ask - best_bid
                    spread_pct = (spread_abs / best_bid) * 100
                    print(f"Current spread: ${spread_abs} ({spread_pct:.2f}%)")
                    
                    # Calculate market without our own orders
                    market_bids = [b for b in all_bids if b['account'] != self.account]
                    market_asks = [a for a in all_asks if a['account'] != self.account]
                    
                    market_bid = market_bids[0]['price'] if market_bids else None
                    market_ask = market_asks[0]['price'] if market_asks else None
                    
                    if market_bid and market_ask:
                        market_price = (market_bid + market_ask) / 2
                        print(f"Market price (excluding our orders): ${market_price}")
                    elif market_bid:
                        print(f"Market best bid (excluding our orders): ${market_bid}")
                    elif market_ask:
                        print(f"Market best ask (excluding our orders): ${market_ask}")
                    else:
                        print("No market orders found excluding our own")
            
            return our_bids, our_asks, dex_price
            
        except Exception as e:
            print(f"Error fetching orderbook: {e}")
            return [], [], None

    def cancel_excess_orders(self, our_bids: List[Dict], our_asks: List[Dict]) -> int:
        """Cancel excess orders, keeping only the desired number per side."""
        orders_to_cancel = []
        
        # Calculate excess orders
        excess_bids = len(our_bids) - self.orders_per_side if len(our_bids) > self.orders_per_side else 0
        excess_asks = len(our_asks) - self.orders_per_side if len(our_asks) > self.orders_per_side else 0
        
        # If no excess orders, return early
        if excess_bids <= 0 and excess_asks <= 0:
            print("No excess orders to cancel")
            return 0
        
        print(f"Found excess orders: {excess_bids} bids, {excess_asks} asks")
        
        # If we have oracle price, prioritize cancelling orders furthest from it
        if self.oracle_price:
            print(f"Using oracle price ${self.oracle_price} as reference for prioritizing cancellations")
            
            # Sort orders by distance from oracle price (furthest first)
            if excess_bids > 0:
                print("Prioritizing bid cancellations by distance from oracle price")
                # Calculate distance from oracle price for each bid
                for bid in our_bids:
                    bid['distance'] = self.oracle_price - bid['price']
                    bid['distance_percent'] = (bid['distance'] / self.oracle_price) * 100
                
                # Sort bids by absolute distance (furthest first)
                our_bids.sort(key=lambda x: abs(x['distance']), reverse=True)
                
                # Select excess bids to cancel
                bids_to_cancel = our_bids[:excess_bids]
                
                # Log the prioritization
                print(f"Cancelling {len(bids_to_cancel)} bids furthest from oracle price:")
                for i, bid in enumerate(bids_to_cancel):
                    print(f"  {i+1}. Bid at ${bid['price']:.2f} - {abs(bid['distance_percent']):.2f}% from oracle")
                
                orders_to_cancel.extend(bids_to_cancel)
            
            if excess_asks > 0:
                print("Prioritizing ask cancellations by distance from oracle price")
                # Calculate distance from oracle price for each ask
                for ask in our_asks:
                    ask['distance'] = ask['price'] - self.oracle_price
                    ask['distance_percent'] = (ask['distance'] / self.oracle_price) * 100
                
                # Sort asks by absolute distance (furthest first)
                our_asks.sort(key=lambda x: abs(x['distance']), reverse=True)
                
                # Select excess asks to cancel
                asks_to_cancel = our_asks[:excess_asks]
                
                # Log the prioritization
                print(f"Cancelling {len(asks_to_cancel)} asks furthest from oracle price:")
                for i, ask in enumerate(asks_to_cancel):
                    print(f"  {i+1}. Ask at ${ask['price']:.2f} - {abs(ask['distance_percent']):.2f}% from oracle")
                
                orders_to_cancel.extend(asks_to_cancel)
        else:
            # If no oracle price, just take excess orders from the end
            print("No oracle price available, cancelling excess orders by price")
            if excess_bids > 0:
                orders_to_cancel.extend(our_bids[-excess_bids:])
            if excess_asks > 0:
                orders_to_cancel.extend(our_asks[-excess_asks:])
        
        if not orders_to_cancel:
            print("No orders to cancel after prioritization")
            return 0
        
        print(f"Canceling {len(orders_to_cancel)} excess orders ({excess_bids} bids, {excess_asks} asks)")
        
        cancelled_count = 0
        
        # Process in batches with delay between batches
        for i in range(0, len(orders_to_cancel), self.batch_size):
            batch = orders_to_cancel[i:i+self.batch_size]
            
            batch_num = (i // self.batch_size) + 1
            total_batches = (len(orders_to_cancel) + self.batch_size - 1) // self.batch_size
            print(f"Processing batch {batch_num}/{total_batches} ({len(batch)} orders)")
            
            # Process each order in the batch
            for order in batch:
                try:
                    for retry in range(2):  # Try up to 2 times
                        try:
                            result = self.dex.cancel_order(
                                account=self.account,
                                order_id=order["identifier"],
                                quote_symbol="USDT",
                                base_symbol="BTC"
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
                except Exception as e:
                    print(f"✗ Error in retry logic: {e}")
            
            # Add delay between batches to avoid rate limiting
            if i + self.batch_size < len(orders_to_cancel):
                time.sleep(self.batch_delay_ms / 1000)
                
        print(f"✅ Cancelled {cancelled_count} excess orders")
        return cancelled_count

    def generate_prices(self, oracle_price: Decimal, dex_price: Decimal) -> Tuple[List[Decimal], List[Decimal]]:
        """Generate price levels for buy and sell orders based on oracle price."""
        # Determine if we need to adjust the midpoint towards the oracle price
        if dex_price and oracle_price:
            # Calculate how far the DEX price is from the oracle price as a percentage
            price_gap_percent = abs(oracle_price - dex_price) / oracle_price
            
            # If there's a significant gap, adjust our center price toward the oracle
            if price_gap_percent > Decimal('0.005'):  # If more than 0.5% difference
                # Use a weighted center price that moves towards the oracle price
                if dex_price < oracle_price:
                    # DEX price is too low, need to create more buys at higher prices
                    center_price = dex_price + ((oracle_price - dex_price) * Decimal('0.7'))
                    print(f"Adjusting center price upward toward oracle: ${center_price}")
                else:
                    # DEX price is too high, need to create more sells at lower prices
                    center_price = dex_price - ((dex_price - oracle_price) * Decimal('0.7'))
                    print(f"Adjusting center price downward toward oracle: ${center_price}")
            else:
                # If close enough, we can use the oracle price directly
                center_price = oracle_price
                print(f"Using oracle price directly as center: ${center_price}")
        else:
            # If we don't have both prices, default to oracle price if available
            center_price = oracle_price if oracle_price else dex_price
            print(f"Using available price as center: ${center_price}")
        
        # Calculate the spread ranges
        min_spread = self.min_spread_percentage
        max_spread = self.max_spread_percentage
        
        # Generate buy prices (bids)
        buy_prices = []
        for i in range(self.orders_per_side):
            # Create a distribution of prices from min_spread to max_spread
            # Start closer to the center and spread outward
            spread_factor = min_spread + ((max_spread - min_spread) * (Decimal(str(i)) / Decimal(str(self.orders_per_side))))
            price = center_price * (Decimal('1') - spread_factor)
            
            # Add some randomness to avoid obvious patterns (0.1% variation)
            randomness = Decimal(str(random.uniform(-0.001, 0.001)))
            price = price * (Decimal('1') + randomness)
            
            buy_prices.append(price)
            
        # Generate sell prices (asks)
        sell_prices = []
        for i in range(self.orders_per_side):
            # Create a distribution of prices from min_spread to max_spread
            # Start closer to the center and spread outward
            spread_factor = min_spread + ((max_spread - min_spread) * (Decimal(str(i)) / Decimal(str(self.orders_per_side))))
            price = center_price * (Decimal('1') + spread_factor)
            
            # Add some randomness to avoid obvious patterns (0.1% variation)
            randomness = Decimal(str(random.uniform(-0.001, 0.001)))
            price = price * (Decimal('1') + randomness)
            
            sell_prices.append(price)
        
        # Sort prices so they're in the correct order
        buy_prices.sort(reverse=True)  # Highest bids first
        sell_prices.sort()  # Lowest asks first
        
        return buy_prices, sell_prices

    def create_missing_orders(self, our_bids: List[Dict], our_asks: List[Dict], oracle_price: Decimal, dex_price: Decimal) -> int:
        """Create missing orders to reach desired counts per side."""
        try:
            # Calculate how many orders we need to create
            missing_bids = max(0, self.orders_per_side - len(our_bids))
            missing_asks = max(0, self.orders_per_side - len(our_asks))
            
            # If we don't need to create any orders, return
            if missing_bids == 0 and missing_asks == 0:
                print("No missing orders to create")
                return 0
                
            print(f"Creating missing orders: {missing_bids} bids, {missing_asks} asks")
            
            # Get account balances before placing orders
            try:
                # Get BTC balance for sell orders
                btc_balance_str = self.client.get_currency_balance(self.account, "BTC")
                btc_balance = Decimal(btc_balance_str.split()[0]) if btc_balance_str else Decimal('0')
                
                # Get USDT balance for buy orders
                usdt_balance_str = self.client.get_currency_balance(self.account, "USDT")
                usdt_balance = Decimal(usdt_balance_str.split()[0]) if usdt_balance_str else Decimal('0')
                
                print(f"Available balances: {btc_balance} BTC, {usdt_balance} USDT")
                
                # Check if we have enough balance to place orders
                if btc_balance < Decimal('0.001') and missing_asks > 0:
                    print("⚠️ Not enough BTC balance to place sell orders")
                    missing_asks = 0
                
                if usdt_balance < Decimal('100') and missing_bids > 0:
                    print("⚠️ Not enough USDT balance to place buy orders")
                    missing_bids = 0
                
                if missing_bids == 0 and missing_asks == 0:
                    print("No orders to create due to insufficient balances")
                    return 0
                
            except Exception as e:
                print(f"Error fetching balances: {e}")
                # Continue with the original missing order counts
            
            # Generate price levels
            if missing_bids > 0 or missing_asks > 0:
                bid_prices, ask_prices = self.generate_prices(oracle_price, dex_price)
                
                # Filter out prices we already have orders at
                existing_bid_prices = [order['price'] for order in our_bids]
                existing_ask_prices = [order['price'] for order in our_asks]
                
                # Get the correct number of unique new prices
                new_bid_prices = [p for p in bid_prices if p not in existing_bid_prices][:missing_bids]
                new_ask_prices = [p for p in ask_prices if p not in existing_ask_prices][:missing_asks]
                
                price_strings = [f"${float(p):.2f}" for p in new_bid_prices]
                print(f"New bid prices: {', '.join(price_strings) if price_strings else 'None'}")
                
                price_strings = [f"${float(p):.2f}" for p in new_ask_prices]
                print(f"New ask prices: {', '.join(price_strings) if price_strings else 'None'}")
            else:
                new_bid_prices = []
                new_ask_prices = []
            
            # Track remaining balance
            remaining_usdt = usdt_balance
            remaining_btc = btc_balance
            
            # Calculate order quantities - use much smaller sizes to ensure we can place all orders
            # Start with a small percentage of the total available balance
            usdt_percent_per_order = Decimal('0.05')  # Use 5% of USDT per order
            btc_percent_per_order = Decimal('0.05')   # Use 5% of BTC per order
            
            # Adjust based on how many orders we need to place
            if len(new_bid_prices) > 0:
                usdt_percent_per_order = min(usdt_percent_per_order, Decimal('0.9') / Decimal(str(len(new_bid_prices))))
            
            if len(new_ask_prices) > 0:
                btc_percent_per_order = min(btc_percent_per_order, Decimal('0.9') / Decimal(str(len(new_ask_prices))))
            
            # Limit to reasonable values
            usdt_per_order = min(usdt_balance * usdt_percent_per_order, Decimal('50'))
            btc_per_order = min(btc_balance * btc_percent_per_order, Decimal('0.005'))
            
            print(f"Allocation per order: ~{usdt_per_order:.2f} USDT for buys, ~{btc_per_order:.8f} BTC for sells")
            
            all_orders = []
            
            # Create bid orders data - with smaller quantities to avoid overdraw
            for bid_price in new_bid_prices:
                # Calculate quantity based on our target USDT per order
                max_btc = usdt_per_order / bid_price
                
                # Ensure it's not more than our remaining balance
                max_btc = min(max_btc, remaining_usdt / bid_price * Decimal('0.99'))  # 99% to account for price fluctuations
                
                # Set a reasonable quantity
                base_amount = max(Decimal('0.0001'), min(max_btc, Decimal('0.001')))
                
                all_orders.append({
                    'type': 'buy',
                    'price': bid_price,
                    'quantity': base_amount,
                    'cost': base_amount * bid_price
                })
            
            # Create ask orders data - with smaller quantities to avoid overdraw
            for ask_price in new_ask_prices:
                # Set a reasonable quantity
                base_amount = min(btc_per_order, remaining_btc * Decimal('0.99') / Decimal(str(len(new_ask_prices))))
                base_amount = max(Decimal('0.0001'), min(base_amount, Decimal('0.001')))
                
                all_orders.append({
                    'type': 'sell',
                    'price': ask_price,
                    'quantity': base_amount
                })
            
            created_count = 0
            
            # Process in batches
            for i in range(0, len(all_orders), self.batch_size):
                batch = all_orders[i:i+self.batch_size]
                
                batch_num = (i // self.batch_size) + 1
                total_batches = (len(all_orders) + self.batch_size - 1) // self.batch_size
                print(f"Processing batch {batch_num}/{total_batches} ({len(batch)} orders)")
                
                # Place each order in the batch
                for order in batch:
                    try:
                        # Apply a tiny random variation to quantity (±1%)
                        variation = Decimal(str(random.uniform(-0.01, 0.01)))  # Convert float to Decimal
                        quantity = order['quantity'] * (Decimal('1') + variation)
                        
                        # Double-check we have enough balance
                        if order['type'] == 'buy':
                            cost = quantity * order['price']
                            if cost > remaining_usdt:
                                print(f"⚠️ Skipping buy order - would cost {cost:.2f} USDT but only {remaining_usdt:.2f} USDT remaining")
                                continue
                        else:  # sell
                            if quantity > remaining_btc:
                                print(f"⚠️ Skipping sell order - would use {quantity:.8f} BTC but only {remaining_btc:.8f} BTC remaining")
                                continue
                        
                        # Ensure at least 8 decimal places precision for BTC
                        quantity_str = f"{quantity:.8f}"
                        
                        for retry in range(2):  # Try up to 2 times
                            try:
                                result = self.dex.place_order(
                                    account=self.account,
                                    order_type=order['type'],
                                    quantity=quantity_str,
                                    price=f"{order['price']:.8f}",
                                    quote_symbol="USDT",
                                    base_symbol="BTC"
                                )
                                
                                if result:
                                    created_count += 1
                                    print(f"✓ Created {order['type']} order for {quantity_str} BTC at ${float(order['price']):.2f}")
                                    
                                    # Update remaining balance
                                    if order['type'] == 'buy':
                                        cost = quantity * order['price']
                                        remaining_usdt -= cost
                                        print(f"  Remaining USDT: {remaining_usdt:.2f}")
                                    else:
                                        remaining_btc -= quantity
                                        print(f"  Remaining BTC: {remaining_btc:.8f}")
                                    
                                    break  # Exit retry loop
                                else:
                                    print(f"✗ Attempt {retry+1}: Failed to create {order['type']} order")
                                    if retry < 1:
                                        time.sleep(0.5)  # Short delay before retry
                            except Exception as e:
                                print(f"✗ Attempt {retry+1}: Error creating {order['type']} order: {e}")
                                if retry < 1:
                                    time.sleep(0.5)  # Short delay before retry
                    except Exception as e:
                        print(f"✗ Error in order creation: {e}")
                
                # Add delay between batches
                if i + self.batch_size < len(all_orders):
                    time.sleep(self.batch_delay_ms / 1000)
            
            print(f"✅ Created {created_count} new orders")
            return created_count
            
        except Exception as e:
            print(f"Error in create_missing_orders: {e}")
            import traceback
            print(traceback.format_exc())
            return 0

    def print_status(self, our_bids: List[Dict], our_asks: List[Dict], oracle_price: Decimal, dex_price: Decimal):
        """Print current status of the orderbook and prices."""
        print("\n=== Orderbook Status ===")
        print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        print(f"\nPrices:")
        print(f"  Oracle:   ${oracle_price:.2f}")
        print(f"  DEX:      ${dex_price:.2f}")
        
        if oracle_price and dex_price:
            price_gap = oracle_price - dex_price
            price_gap_percent = (price_gap / oracle_price) * 100
            direction = "HIGHER" if price_gap > 0 else "LOWER"
            print(f"  Gap:      ${abs(price_gap):.2f} ({abs(price_gap_percent):.2f}%)")
            print(f"  Status:   Oracle price is {direction} than DEX price")
        
        print(f"\nOrders:")
        print(f"  Our Bids:  {len(our_bids)}/{self.orders_per_side}")
        print(f"  Our Asks:  {len(our_asks)}/{self.orders_per_side}")
        print(f"  Total:     {len(our_bids) + len(our_asks)}/{self.orders_per_side * 2}")
            
        # Show our top bids and asks
        if our_bids:
            print(f"\nTop 5 Bids:")
            for i, bid in enumerate(our_bids[:5]):
                print(f"  {i+1}. ${bid['price']:.2f} - {bid['quantity']:.8f} BTC")
        
        if our_asks:
            print(f"\nTop 5 Asks:")
            for i, ask in enumerate(our_asks[:5]):
                print(f"  {i+1}. ${ask['price']:.2f} - {ask['quantity']:.8f} BTC")
        
        print("\n" + "=" * 35)

    def manage_orderbook(self):
        """Main function to manage the orderbook."""
        try:
            message = "\n" + "=" * 80
            message += f"\nStarting orderbook management cycle at {time.strftime('%Y-%m-%d %H:%M:%S')}"
            message += "\n" + "=" * 80
            
            print(message)
            sys.stdout.flush()
            
            # Get oracle price
            oracle_price = self.get_oracle_price()
            if not oracle_price:
                print("Could not get oracle price, aborting this cycle")
                sys.stdout.flush()
                return
            
            # Get current orderbook
            our_bids, our_asks, dex_price = self.get_current_orderbook()
            
            # Check if we can calculate a DEX price (need both bids and asks)
            if not dex_price:
                print("Could not calculate DEX price - orderbook may be missing bids or asks")
                print(f"Using oracle price as reference: ${oracle_price}")
                sys.stdout.flush()
                # Use oracle price as reference
                dex_price = oracle_price
            
            # Cancel excess orders
            cancelled_count = self.cancel_excess_orders(our_bids, our_asks)
            
            # Create missing orders
            created_count = self.create_missing_orders(our_bids, our_asks, oracle_price, dex_price)
            
            # If we made changes, refresh the orderbook to get updated status
            if cancelled_count > 0 or created_count > 0:
                print("\nRefreshing orderbook to get updated status...")
                sys.stdout.flush()
                # Add a short delay to allow blockchain to process
                time.sleep(2)
                our_bids, our_asks, dex_price = self.get_current_orderbook()
                if not dex_price:
                    dex_price = oracle_price
            
            # Print the status
            self.print_status(our_bids, our_asks, oracle_price, dex_price)
            
        except Exception as e:
            print(f"Error in manage_orderbook: {e}")
            import traceback
            print(traceback.format_exc())
            sys.stdout.flush()
        
        message = f"\nNext cycle in {self.refresh_interval} seconds.\n"
        print(message)
        sys.stdout.flush()

def main():
    """Main function to run orderbook management."""
    try:
        # Check for command line arguments
        import argparse
        parser = argparse.ArgumentParser(description='Oracle Aligned Orderbook Manager')
        parser.add_argument('--once', action='store_true', help='Run once and exit')
        args = parser.parse_args()
        
        manager = OracleAlignedOrderbookManager(run_once=args.once)
        
        if args.once:
            print("Running orderbook manager once and then exiting...")
            manager.manage_orderbook()
            print("Done!")
        else:
            # Run continuously with specified interval
            while True:
                manager.manage_orderbook()
                time.sleep(manager.refresh_interval)
                
    except KeyboardInterrupt:
        print("\nOrderbook manager stopped by user.")
    except Exception as e:
        print(f"Fatal error in orderbook manager: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 