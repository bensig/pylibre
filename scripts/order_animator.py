#!/usr/bin/env python3
"""
Script to animate the orderbook with small changes for UI activity.
This script works alongside the oracle_aligned_orderbook.py script.
It focuses on:
1. Creating visual activity by periodically canceling and replacing orders
2. Making small price adjustments to existing orders
3. Operating at a higher frequency (every 5 seconds)
4. Selecting a random number of orders (2-8) each cycle
"""

import os
import sys
import yaml
import time
import random
import logging
from datetime import datetime
from decimal import Decimal, ROUND_DOWN

# Add the parent directory to the path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.pylibre.client import LibreClient
from src.pylibre.dex import DexClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/order_animator.log')
    ]
)
logger = logging.getLogger(__name__)

class OrderAnimator:
    def __init__(self, config_path='config/config.yaml', strategy_config_path='config/strategies.mainnet.yaml'):
        self.load_config(config_path, strategy_config_path)
        
        # Initialize the API client
        self.client = LibreClient(
            api_url=self.config['api_endpoint'],
            network='mainnet',
            config_path=config_path,
            verbose=True
        )
        
        self.dex = DexClient(self.client, self.config['dex_contract'])
        
        # Animation parameters
        self.price_jitter_percent = 0.05  # Small price jitter (0.05%)
        self.amount_jitter_percent = 0.5  # Slight amount variation (0.5%)
        self.min_orders_per_cycle = 2
        self.max_orders_per_cycle = 8
        self.animation_interval = 5  # seconds

    def load_config(self, config_path, strategy_config_path):
        """Load configuration from the YAML file."""
        try:
            with open(config_path, 'r') as file:
                self.config = yaml.safe_load(file)
            
            with open(strategy_config_path, 'r') as file:
                self.strategy_config = yaml.safe_load(file)
                
            # Extract API endpoint from strategy config (which takes precedence)
            self.config['api_endpoint'] = self.strategy_config.get('api_endpoint') or self.config.get('api_url') or self.config.get('api_endpoint')
            
            if not self.config.get('api_endpoint'):
                logger.warning("API endpoint not found in any config, using default: https://lb.libre.org")
                self.config['api_endpoint'] = "https://lb.libre.org"
            else:
                logger.info(f"Using API endpoint: {self.config['api_endpoint']}")
            
            # Extract DEX contract from config
            self.config['dex_contract'] = self.config.get('dex_contract') or "dex.libre"
            
            # Extract account from strategy config
            if 'account' not in self.strategy_config:
                if 'accounts' in self.strategy_config and 'BTCUSDT' in self.strategy_config['accounts']:
                    self.strategy_config['account'] = self.strategy_config['accounts']['BTCUSDT']['liquidity_provider']
                    logger.info(f"Using account from BTCUSDT liquidity_provider: {self.strategy_config['account']}")
                else:
                    logger.warning("Account not found in strategy config, please check your configuration")
                    raise ValueError("Missing 'account' in strategy configuration")
            
            # Extract pair from strategy config
            if 'pair' not in self.strategy_config:
                self.strategy_config['pair'] = 'btcusdt'
                logger.info(f"Pair not specified, defaulting to: {self.strategy_config['pair']}")
                
        except Exception as e:
            logger.exception(f"Error loading configuration: {e}")
            raise
    
    def apply_jitter(self, value, percent):
        """Apply a small random jitter to the given value."""
        # Convert to Decimal to avoid float multiplication errors
        jitter = Decimal(str(random.uniform(-percent, percent))) / Decimal('100')
        jitter_factor = Decimal('1') + jitter
        return value * jitter_factor
    
    def get_orderbook(self):
        """Get the complete orderbook and filter our orders."""
        try:
            # Get orderbook data for BTC/USDT
            orderbook = self.dex.fetch_order_book(
                quote_symbol="USDT",
                base_symbol="BTC"
            )
            
            if not orderbook:
                logger.warning("Failed to fetch orderbook")
                return [], []
                
            # Extract our orders
            account = self.strategy_config['account']
            our_bids = []
            our_asks = []
            
            # Process bids
            for bid in orderbook.get('bids', []):
                if bid.get('account') == account:
                    our_bids.append({
                        'id': bid.get('identifier'),
                        'type': 'buy',
                        'price': Decimal(str(bid.get('price'))),
                        'quantity': bid.get('quantity'),
                        'account': account
                    })
            
            # Process asks
            for ask in orderbook.get('offers', []):
                if ask.get('account') == account:
                    our_asks.append({
                        'id': ask.get('identifier'),
                        'type': 'sell',
                        'price': Decimal(str(ask.get('price'))),
                        'quantity': ask.get('quantity'),
                        'account': account
                    })
            
            return our_bids, our_asks
            
        except Exception as e:
            logger.exception(f"Error getting orderbook: {e}")
            return [], []
    
    def select_orders_for_animation(self, bids, asks):
        """Select a random number of orders for animation, including the highest bid and lowest ask."""
        num_orders = random.randint(self.min_orders_per_cycle, self.max_orders_per_cycle)
        logger.info(f"Selecting {num_orders} orders for animation (including highest bid/lowest ask when possible)")
        
        selected_bids = []
        selected_asks = []
        
        # First, try to include highest bid and lowest ask to help move the mid-market price
        if bids:
            # Find highest bid (sort by price descending)
            sorted_bids = sorted(bids, key=lambda x: x['price'], reverse=True)
            highest_bid = sorted_bids[0]
            selected_bids.append(highest_bid)
            logger.info(f"Selected highest bid at ${highest_bid['price']} for animation")
            
            # Remove the highest bid from the list of bids to avoid duplicates
            sorted_bids = sorted_bids[1:]
            
            # Select remaining random bids
            remaining_bids = min(len(sorted_bids), random.randint(0, num_orders // 2))
            if remaining_bids > 0 and sorted_bids:
                selected_bids.extend(random.sample(sorted_bids, remaining_bids))
        
        if asks:
            # Find lowest ask (sort by price ascending)
            sorted_asks = sorted(asks, key=lambda x: x['price'])
            lowest_ask = sorted_asks[0]
            selected_asks.append(lowest_ask)
            logger.info(f"Selected lowest ask at ${lowest_ask['price']} for animation")
            
            # Remove the lowest ask from the list of asks to avoid duplicates
            sorted_asks = sorted_asks[1:]
            
            # Select remaining random asks
            remaining_asks = min(len(sorted_asks), num_orders - len(selected_bids) - 1)
            if remaining_asks > 0 and sorted_asks:
                selected_asks.extend(random.sample(sorted_asks, remaining_asks))
        
        # If we still haven't selected enough orders, add more from either side
        if len(selected_bids) + len(selected_asks) < num_orders:
            # Determine how many more to select
            remaining = num_orders - len(selected_bids) - len(selected_asks)
            
            # Try to select evenly from both sides
            avail_bids = [b for b in bids if b not in selected_bids]
            avail_asks = [a for a in asks if a not in selected_asks]
            
            # Calculate how many more to take from each side
            more_bids = min(len(avail_bids), remaining // 2 + (remaining % 2))
            more_asks = min(len(avail_asks), remaining - more_bids)
            
            # Adjust if needed
            if more_bids + more_asks < remaining and len(avail_bids) > more_bids:
                more_bids = min(len(avail_bids), remaining - more_asks)
            
            # Add additional random orders
            if more_bids > 0 and avail_bids:
                selected_bids.extend(random.sample(avail_bids, more_bids))
            if more_asks > 0 and avail_asks:
                selected_asks.extend(random.sample(avail_asks, more_asks))
        
        total_selected = len(selected_bids) + len(selected_asks)
        logger.info(f"Total selected: {total_selected} orders ({len(selected_bids)} bids, {len(selected_asks)} asks)")
        
        return selected_bids, selected_asks
    
    def animate_order(self, order):
        """Cancel an order and create a new one with slightly different parameters."""
        try:
            order_id = order['id']
            order_type = order['type']
            price = order['price']
            account = order['account']
            
            # Apply jitter to price
            new_price = self.apply_jitter(price, self.price_jitter_percent)
            
            # Cancel the order
            logger.info(f"Animating {order_type} order at price {price}")
            
            # Cancel order
            cancel_result = self.dex.cancel_order(
                account=account,
                order_id=order_id,
                base_symbol="BTC",
                quote_symbol="USDT"
            )
            
            if not cancel_result.get('success', False):
                logger.error(f"Failed to cancel order {order_id}: {cancel_result.get('error', 'Unknown error')}")
                return False
            
            logger.info(f"✓ Cancelled {order_type} order at price {price}")
            
            # Wait briefly to ensure order cancellation is processed
            time.sleep(1)
            
            # Calculate new quantity with slight variation
            quantity_str = str(order['quantity'])
            # If quantity has a unit (like "0.00123456 BTC"), strip it
            if ' ' in quantity_str:
                quantity_str = quantity_str.split(' ')[0]
            
            quantity = Decimal(quantity_str)
            new_quantity = self.apply_jitter(quantity, self.amount_jitter_percent)
            
            # Format quantity and price for order placement
            quantity_str = f"{new_quantity:.8f}"
            price_str = f"{new_price:.8f}"
            
            # Place new order
            place_result = self.dex.place_order(
                account=account,
                order_type=order_type,
                quantity=quantity_str,
                price=price_str,
                base_symbol="BTC",
                quote_symbol="USDT"
            )
            
            # Check if the result is a success (either a dict with success=True or a string transaction ID)
            if place_result:
                if isinstance(place_result, str):
                    # String transaction ID means success
                    logger.info(f"✓ Created {order_type} order for {quantity_str} BTC at ${price_str} (tx: {place_result[:8]}...)")
                    return True
                elif isinstance(place_result, dict) and place_result.get('success', False):
                    # Dictionary with success=True
                    tx_id = place_result.get('transaction_id', 'unknown')
                    logger.info(f"✓ Created {order_type} order for {quantity_str} BTC at ${price_str} (tx: {tx_id[:8] if isinstance(tx_id, str) else 'unknown'}...)")
                    return True
                else:
                    # Some other unexpected result
                    logger.error(f"Failed to create new {order_type} order: Unexpected result {place_result}")
                    return False
            else:
                logger.error(f"Failed to create new {order_type} order: No result")
                return False
                
        except Exception as e:
            logger.exception(f"Error animating order: {e}")
            return False
    
    def run_animation_cycle(self):
        """Run a single animation cycle."""
        try:
            cycle_start = datetime.now()
            logger.info(f"\n=== Animation Cycle {self.cycle_count} ===")
            logger.info(f"Time: {cycle_start.strftime('%Y-%m-%d %H:%M:%S')}")
            
            # Get our orders
            bids, asks = self.get_orderbook()
            logger.info(f"Found {len(bids)} bids and {len(asks)} asks for our account")
            
            if not bids and not asks:
                logger.warning("No orders found to animate")
                return
            
            # Calculate current market price if possible
            if bids and asks:
                best_bid = max([b['price'] for b in bids])
                best_ask = min([a['price'] for a in asks])
                mid_market = (best_bid + best_ask) / 2
                logger.info(f"Current DEX price range: ${best_bid} - ${best_ask} (mid: ${mid_market})")
            
            # Select orders for animation
            selected_bids, selected_asks = self.select_orders_for_animation(bids, asks)
            total_selected = len(selected_bids) + len(selected_asks)
            logger.info(f"Selected {total_selected} orders for animation")
            
            # Animate selected orders
            successful_animations = 0
            
            for order in selected_bids + selected_asks:
                if self.animate_order(order):
                    successful_animations += 1
                
                # Brief pause between operations to avoid rate limits
                time.sleep(0.5)
            
            logger.info(f"\n✨ Animation cycle completed: {successful_animations}/{total_selected} orders animated")
            logger.info(f"Next animation cycle in {self.animation_interval} seconds")
            
        except Exception as e:
            logger.exception(f"Error in animation cycle: {e}")
    
    def run(self):
        """Run the order animator continuously."""
        self.cycle_count = 1
        
        try:
            logger.info(f"Starting Order Animator for {self.strategy_config['account']} on {self.strategy_config['pair']}")
            logger.info(f"Animation parameters: {self.min_orders_per_cycle}-{self.max_orders_per_cycle} orders every {self.animation_interval} seconds")
            logger.info(f"Price jitter: {self.price_jitter_percent}%, Amount jitter: {self.amount_jitter_percent}%")
            
            # Check if running in test mode
            run_once = getattr(self, 'run_once', False)
            if run_once:
                logger.info("Running in test mode (one cycle only)")
                self.run_animation_cycle()
                logger.info("Test cycle completed")
                return
            
            # Run continuously
            while True:
                try:
                    self.run_animation_cycle()
                except Exception as e:
                    logger.exception(f"Error in cycle {self.cycle_count}: {e}")
                
                self.cycle_count += 1
                time.sleep(self.animation_interval)
                
        except KeyboardInterrupt:
            logger.info("Animation stopped by user")
        except Exception as e:
            logger.exception(f"Fatal error in animator: {e}")

def main():
    """Main function to run the orderbook animator."""
    import argparse
    parser = argparse.ArgumentParser(description='Order Animator')
    parser.add_argument('--once', action='store_true', help='Run once and exit')
    parser.add_argument('--config', default='config/config.yaml', help='Path to config file')
    parser.add_argument('--strategy', default='config/strategies.mainnet.yaml', help='Path to strategy config file')
    parser.add_argument('--interval', type=int, help='Animation interval in seconds')
    parser.add_argument('--min-orders', type=int, help='Minimum orders to animate per cycle')
    parser.add_argument('--max-orders', type=int, help='Maximum orders to animate per cycle')
    args = parser.parse_args()
    
    # Ensure logs directory exists
    os.makedirs("logs", exist_ok=True)
    
    try:
        # Create animator
        animator = OrderAnimator(config_path=args.config, strategy_config_path=args.strategy)
        
        # Set test mode if requested
        if args.once:
            animator.run_once = True
            
        # Override parameters if provided
        if args.interval:
            animator.animation_interval = args.interval
        if args.min_orders:
            animator.min_orders_per_cycle = args.min_orders
        if args.max_orders:
            animator.max_orders_per_cycle = args.max_orders
            
        # Run animator
        animator.run()
    except Exception as e:
        logger.exception(f"Failed to start animator: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 