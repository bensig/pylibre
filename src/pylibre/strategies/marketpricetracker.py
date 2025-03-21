from .templates.base_strategy import BaseStrategy
from decimal import Decimal
import time
import threading
import os
import json
import asyncio
from typing import Dict, Any, Optional, List
from pylibre.utils.logger import StrategyLogger, LogLevel
from pylibre.utils.shared_data import write_price, read_price
from pylibre.price_feed import PriceFeedFactory
from pylibre.price_feed.base import PriceSource
from pylibre.utils.binance_api import fetch_btc_usdt_price

class MarketPriceTrackerStrategy(BaseStrategy):
    """
    Monitors external market prices and updates the center price of orderbooks.
    Periodically fetches prices from external sources and adjusts orders.
    """
    

    def __init__(self, client, account, base_symbol, quote_symbol, parameters, logger=None):
        super().__init__(client, account, base_symbol, quote_symbol, parameters, logger)
        
        # Ensure we have a dedicated logger for this strategy
        if logger is None:
            from pylibre.utils.logger import StrategyLogger, LogLevel
            self.logger = StrategyLogger(
                f"MarketPriceTracker_{account}_{base_symbol}_{quote_symbol}", 
                level=LogLevel.DEBUG
            )
        
        # Initialize parameters - Support both 'source' and 'price_source' parameter names for compatibility
        self.price_source = parameters.get('price_source', parameters.get('source', 'binance'))
        
        # Automatically set price source to 'binance' for BTC/USDT if not explicitly set to 'fixed'
        if self.base_symbol == 'BTC' and self.quote_symbol == 'USDT' and self.price_source != 'fixed':
            self.price_source = 'binance'
            self.logger.info(f"Setting price source to 'binance' for {self.base_symbol}/{self.quote_symbol}")
        
        self.update_interval_ms = parameters.get('update_interval_ms', 30000)  # 30 seconds default
        
        # For LIBRE/BTC, default to 1 SAT (0.00000001 BTC) per LIBRE if not specified
        default_price = Decimal('0.00000001') if (self.base_symbol == 'LIBRE' and self.quote_symbol == 'BTC') else Decimal('0')
        self.fixed_price = Decimal(str(parameters.get('fixed_price', parameters.get('fallback_price', default_price))))
        
        self.price_change_threshold = Decimal(str(parameters.get('price_change_threshold', 0.005)))  # 0.5% default
        
        # Initialize price file path
        self.price_file_path = parameters.get('price_file_path', 
                                             f"shared_data/{self.base_symbol.lower()}{self.quote_symbol.lower()}_price.json")
        
        # Ensure shared_data directory exists
        os.makedirs(os.path.dirname(self.price_file_path), exist_ok=True)
        
        # Last fetched price - start with the fixed price
        self.last_price = self._get_last_saved_price() or self.fixed_price
        
        # Notification callbacks
        self.price_update_callbacks = []
        
        # Add runtime verification
        self._last_run_time = None
        self._run_count = 0
        
        # Background update thread (only for relevant price sources)
        self.use_background_updater = parameters.get('use_background_updater', True)
        self.running = True
        self.background_thread = None
        
        # Initialize price feed
        self.price_feed = self._initialize_price_feed()
        
        # Log initialization
        self.logger.info(f"MarketPriceTrackerStrategy initialized with price source: {self.price_source}")
        self.logger.info(f"Update interval: {self.update_interval_ms}ms")
        self.logger.info(f"Price file path: {self.price_file_path}")
        self.logger.info(f"Initialized MarketPriceTrackerStrategy with:")
        self.logger.info(f"  Account: {account}")
        self.logger.info(f"  Trading pair: {base_symbol}/{quote_symbol}")
        self.logger.info(f"  Price source: {self.price_source}")
        self.logger.info(f"  Fixed price: {self.fixed_price}")
        self.logger.info(f"  Update interval: {self.update_interval_ms}ms")
        self.logger.info(f"  Price change threshold: {float(self.price_change_threshold)*100}%")
        self.logger.info(f"  Price file: {self.price_file_path}")
        
        # Start background update thread if needed and if not fixed price
        if self.use_background_updater and self.price_source != 'fixed':
            self._start_background_updater()

    def _initialize_price_feed(self) -> Optional[PriceSource]:
        """Initialize the price feed based on the configured source."""
        if self.price_source == 'fixed':
            # For fixed price source, we don't need to initialize a price feed
            return None
        elif self.price_source == 'binance':
            # For BTC/USDT, we use the Binance price source
            if self.base_symbol == 'BTC' and self.quote_symbol == 'USDT':
                config = {
                    "source": "binance",
                    "reference_symbol": "BTCUSDT"
                }
                try:
                    return PriceFeedFactory.create_price_source(config)
                except Exception as e:
                    self.logger.error(f"Error initializing Binance price feed: {e}")
                    return None
            else:
                self.logger.warning(f"Binance source only supported for BTC/USDT, not {self.base_symbol}/{self.quote_symbol}")
                return None
        else:
            self.logger.warning(f"Unknown price source: {self.price_source}, using fixed price")
            return None
            
    def _get_last_saved_price(self) -> Optional[Decimal]:
        """Get the last saved price from the price file."""
        price = read_price(self.price_file_path)
        if price is not None:
            return Decimal(str(price))
        return None
        
    def register_price_update_callback(self, callback):
        """Register a callback to be called when the price is updated."""
        self.price_update_callbacks.append(callback)
        
    def _check_internet_connectivity(self):
        """Check if internet connection is working by pinging common reliable sites."""
        import requests
        
        # List of reliable sites to check
        test_urls = [
            "https://www.google.com",
            "https://www.cloudflare.com",
            "https://www.amazon.com"
        ]
        
        working_count = 0
        for url in test_urls:
            try:
                self.logger.info(f"Testing internet connectivity with {url}...")
                response = requests.get(url, timeout=3)
                if response.status_code == 200:
                    working_count += 1
                    self.logger.info(f"✅ Successfully connected to {url}")
                else:
                    self.logger.warning(f"⚠️ Connection to {url} returned status code {response.status_code}")
            except Exception as e:
                self.logger.error(f"❌ Failed to connect to {url}: {e}")
        
        # If at least one site is reachable, internet is likely working
        if working_count > 0:
            self.logger.info(f"✅ Internet connectivity confirmed ({working_count}/{len(test_urls)} sites reachable)")
            return True
        else:
            self.logger.error("❌ Internet connectivity issues detected - unable to reach any test sites")
            return False

    def fetch_current_price(self) -> Optional[Decimal]:
        """Fetch the current price from the appropriate source."""
        # For LIBRE/BTC, we always use the fixed price
        if self.base_symbol == 'LIBRE' and self.quote_symbol == 'BTC':
            self.logger.debug(f"Using fixed price for {self.base_symbol}/{self.quote_symbol}: {self.fixed_price}")
            return self.fixed_price
            
        # For BTC/USDT, we use Binance if specified
        if self.base_symbol == 'BTC' and self.quote_symbol == 'USDT' and self.price_source == 'binance':
            self.logger.info(f"Fetching {self.base_symbol}/{self.quote_symbol} price from Binance...")
            try:
                price = fetch_btc_usdt_price()
                if price is not None:
                    self.logger.info(f"✅ Successfully fetched price from Binance: {price} {self.quote_symbol}")
                    return Decimal(str(price))
                else:
                    self.logger.error(f"❌ Failed to fetch price from Binance - returned None")
                    # Check internet connectivity
                    if not self._check_internet_connectivity():
                        self.logger.error("Internet connectivity issues detected - check your network connection")
                    
                    if self.last_price and self.last_price > 0:
                        self.logger.warning(f"Using last known price instead: {self.last_price} {self.quote_symbol}")
                        return self.last_price
                    else:
                        self.logger.warning(f"Using fallback fixed price: {self.fixed_price} {self.quote_symbol}")
                        return self.fixed_price
            except Exception as e:
                self.logger.error(f"❌ Error fetching price from Binance: {e}")
                self.logger.error("Check your internet connection and Binance API availability")
                
                # Check internet connectivity
                self._check_internet_connectivity()
                
                if self.last_price and self.last_price > 0:
                    self.logger.warning(f"Using last known price instead: {self.last_price} {self.quote_symbol}")
                    return self.last_price
                else:
                    self.logger.warning(f"Using fallback fixed price: {self.fixed_price} {self.quote_symbol}")
                    return self.fixed_price
                
        # Default to fixed price for all other cases
        return self.fixed_price
            
    def is_significant_price_change(self, new_price: Decimal) -> bool:
        """Check if the price change is significant enough to trigger an update."""
        if self.last_price is None:
            return True
            
        if self.last_price == Decimal('0'):
            return True
            
        price_change_percentage = abs(new_price - self.last_price) / self.last_price
        return price_change_percentage >= self.price_change_threshold
        
    def update_price(self, new_price: Decimal) -> bool:
        """Update the current price and notify other strategies."""
        try:
            # Get current price for comparison
            current_price = self.last_price
            
            # Log file write attempt
            self.logger.info(f"Writing price {new_price} to file: {self.price_file_path}")
            
            # Save the price to the file
            try:
                from pylibre.utils.shared_data import write_price
                success = write_price(self.price_file_path, float(new_price))
                if success:
                    self.logger.info(f"Successfully wrote price to file")
                else:
                    self.logger.error(f"Failed to write price to file")
            except Exception as file_error:
                self.logger.error(f"Exception writing price to file: {file_error}")
                import traceback
                self.logger.error(f"File write traceback: {traceback.format_exc()}")
            
            # Only proceed if price is valid
            if new_price <= 0:
                self.logger.warning(f"Ignoring invalid price update: {new_price}")
                return False
            
            # Determine if this is a significant change
            threshold = self.price_change_threshold
            is_significant = False
            
            if current_price is None:
                self.logger.info(f"Setting initial price: {new_price} {self.quote_symbol}")
                is_significant = True
            elif current_price == Decimal('0'):
                self.logger.info(f"Setting price from zero: {new_price} {self.quote_symbol}")
                is_significant = True
            elif abs(new_price - current_price) / current_price > threshold:
                change_pct = ((new_price - current_price) / current_price) * 100
                self.logger.info(f"Price updated: {self.base_symbol}/{self.quote_symbol} from {current_price} to {new_price} ({change_pct:.2f}%)")
                is_significant = True
            else:
                # Minor change, log at debug level only
                self.logger.debug(f"Minor price update: {current_price} → {new_price} {self.quote_symbol}")
            
            # Update the last price
            self.last_price = new_price
            
            # Only notify other strategies for significant changes
            if is_significant:
                self._notify_strategies(new_price)
            
            return True
        except Exception as e:
            self.logger.error(f"Error updating price: {e}")
            return False
            
    def run(self):
        """Execute one cycle of the strategy."""
        try:
            # Check runtime
            if self._last_run_time is not None:
                elapsed_ms = (time.time() - self._last_run_time) * 1000
                if elapsed_ms < self.update_interval_ms:
                    # Not time to update yet
                    return
                    
            # Get the current price
            self.logger.debug(f"Fetching current price for {self.base_symbol}/{self.quote_symbol}...")
            
            # Attempt to fetch the latest price
            current_price = self.fetch_current_price()
            
            # Check if price is valid
            if current_price is None or current_price <= 0:
                self.logger.error(f"❌ Failed to get valid price - got {current_price}")
                return
                
            # Get the last update time for logging purposes
            last_update_time = self.get_last_update_time()
            time_since_update = "Never" if last_update_time is None else self._format_time_since(last_update_time)
                
            # Detect if price has changed significantly
            if self.last_price is None or self.last_price <= 0:
                # First price fetch
                self.logger.info(f"Initial price set to {current_price} {self.quote_symbol} (last update: {time_since_update})")
                price_changed = True
            elif self.is_significant_price_change(current_price):
                # Significant price change
                change_pct = ((current_price - self.last_price) / self.last_price) * 100
                self.logger.info(f"Price update: {self.base_symbol}/{self.quote_symbol} from {self.last_price} to {current_price} ({change_pct:.2f}%) (last update: {time_since_update})")
                price_changed = True
            else:
                # Minor price change - just log at debug level
                change_pct = ((current_price - self.last_price) / self.last_price) * 100
                self.logger.debug(f"Minor price change: {self.last_price} -> {current_price} ({change_pct:.2f}%) (last update: {time_since_update})")
                price_changed = False
                
            # Update price if changed
            if price_changed:
                self.update_price(current_price)
                
            # Always update the runtime tracking
            self._last_run_time = time.time()
            self._run_count += 1
            
            # Every 30 runs (roughly 15 min at default settings), log a heartbeat message
            if self._run_count % 30 == 0:
                self.logger.info(f"MarketPriceTracker heartbeat: Current price is {current_price} {self.quote_symbol} (last update: {time_since_update})")
                
            return True
        except Exception as e:
            self.logger.error(f"Error in MarketPriceTracker run cycle: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False
            
    def get_last_update_time(self):
        """Get the timestamp when the price was last updated from the price file."""
        try:
            import json
            import os
            if not os.path.exists(self.price_file_path):
                return None
                
            with open(self.price_file_path, 'r') as f:
                data = json.load(f)
                
            if isinstance(data, dict) and "last_updated" in data:
                return data["last_updated"]
            return None
        except Exception as e:
            self.logger.debug(f"Could not read last update time: {e}")
            return None
            
    def _format_time_since(self, timestamp_str):
        """Format the time since the given timestamp in a human-readable format."""
        try:
            from datetime import datetime
            last_time = datetime.fromisoformat(timestamp_str)
            now = datetime.now()
            delta = now - last_time
            
            seconds = delta.total_seconds()
            if seconds < 60:
                return f"{int(seconds)}s ago"
            elif seconds < 3600:
                return f"{int(seconds/60)}m ago"
            elif seconds < 86400:
                return f"{int(seconds/3600)}h ago"
            else:
                return f"{int(seconds/86400)}d ago"
        except Exception:
            return timestamp_str

    def cleanup(self):
        """Clean up resources."""
        self.logger.info("Cleaning up MarketPriceTrackerStrategy")
        self.running = False
        
        # Wait for background thread to finish if it exists
        if self.background_thread and self.background_thread.is_alive():
            self.logger.info("Waiting for background price updater to stop...")
            self.background_thread.join(timeout=2.0)
            if self.background_thread.is_alive():
                self.logger.warning("Background price updater did not stop cleanly")

    def place_orders(self, signal: Dict[str, Any]) -> bool:
        """
        Implementation of the abstract method from BaseStrategy.
        
        The MarketPriceTrackerStrategy doesn't place orders directly,
        it only tracks prices and notifies other strategies.
        
        Args:
            signal: The trading signal (not used in this strategy)
            
        Returns:
            bool: Always returns True as this strategy doesn't place orders
        """
        # This strategy doesn't place orders, it only tracks prices
        # and notifies other strategies of price changes
        self.logger.debug("MarketPriceTrackerStrategy doesn't place orders directly")
        return True 

    def fetch_price_from_binance(self):
        """Fetch price from Binance API."""
        try:
            import requests
            
            # Log the attempt
            self.logger.info(f"Fetching price from Binance for {self.base_symbol}/{self.quote_symbol}")
            
            url = f"https://api.binance.com/api/v3/ticker/price?symbol={self.base_symbol}{self.quote_symbol}"
            self.logger.debug(f"Binance API URL: {url}")
            
            response = requests.get(url, timeout=10)
            
            # Log response status
            self.logger.debug(f"Binance response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                price = Decimal(data['price'])
                self.logger.info(f"Successfully fetched price from Binance: {price} {self.quote_symbol}")
                return price
            else:
                self.logger.error(f"Error fetching price from Binance: {response.status_code}")
                self.logger.error(f"Response: {response.text}")
                return None
        except Exception as e:
            self.logger.error(f"Exception fetching price from Binance: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return None 

    def _start_background_updater(self):
        """Start a background thread to fetch and update prices independently."""
        if self.price_source == 'fixed':
            self.logger.info("Not starting background price updater for fixed price source")
            return
            
        self.logger.info("Starting background price update thread")
        self.background_thread = threading.Thread(target=self._background_price_update_loop, daemon=True)
        self.background_thread.start()
        
    def _background_price_update_loop(self):
        """Background thread that updates prices at regular intervals."""
        self.logger.info(f"Background price updater started for {self.base_symbol}/{self.quote_symbol}")
        
        while self.running:
            try:
                # Fetch and update price
                self.logger.debug("Background thread checking price...")
                current_price = self.fetch_current_price()
                
                if current_price and current_price > 0:
                    # Detect if price has changed significantly
                    if self.last_price is None or self.last_price <= 0:
                        self.logger.info(f"Background updater: Initial price set to {current_price} {self.quote_symbol}")
                        self.update_price(current_price)
                    elif self.is_significant_price_change(current_price):
                        # Log the significant price change
                        change_pct = ((current_price - self.last_price) / self.last_price) * 100
                        self.logger.info(f"Background updater: Price change from {self.last_price} to {current_price} ({change_pct:.2f}%)")
                        self.update_price(current_price)
                    else:
                        # Minor price change - just log at debug level
                        change_pct = ((current_price - self.last_price) / self.last_price) * 100
                        self.logger.debug(f"Background updater: Minor price change: {self.last_price} -> {current_price} ({change_pct:.2f}%)")
                        # Still update the price file even for minor changes
                        self.update_price(current_price)
                        
                # Sleep for the configured interval
                sleep_seconds = self.update_interval_ms / 1000
                time.sleep(sleep_seconds)
            except Exception as e:
                self.logger.error(f"Error in background price updater: {e}")
                import traceback
                self.logger.error(traceback.format_exc())
                # Sleep for a bit before retrying
                time.sleep(30) 