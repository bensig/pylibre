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
        """Initialize the strategy with parameters."""
        super().__init__(client, account, base_symbol, quote_symbol, parameters, logger)
        
        # Strategy parameters
        self.update_interval_ms = parameters.get('update_interval_ms', 30000)  # 30 seconds default
        # Support both 'source' and 'price_source' parameter names for compatibility
        self.price_source = parameters.get('price_source', parameters.get('source', 'fixed'))  # Default to fixed price source
        
        # For LIBRE/BTC, default to 1 SAT (0.00000001 BTC) per LIBRE if not specified
        default_price = Decimal('0.00000001') if (self.base_symbol == 'LIBRE' and self.quote_symbol == 'BTC') else Decimal('0')
        self.fixed_price = Decimal(str(parameters.get('fixed_price', parameters.get('fallback_price', default_price))))
        
        # Automatically set price source to 'binance' for BTC/USDT if not explicitly set to 'fixed'
        if self.base_symbol == 'BTC' and self.quote_symbol == 'USDT' and self.price_source != 'fixed':
            self.price_source = 'binance'
            self.logger.info(f"Setting price source to 'binance' for {self.base_symbol}/{self.quote_symbol}")
        
        self.price_change_threshold = Decimal(str(parameters.get('price_change_threshold', 0.005)))  # 0.5% default
        self.price_file_path = parameters.get('price_file_path', 
                                             f"shared_data/{self.base_symbol.lower()}{self.quote_symbol.lower()}_price.json")
        
        # Ensure shared_data directory exists
        os.makedirs(os.path.dirname(self.price_file_path), exist_ok=True)
        
        # Last fetched price - start with the fixed price
        self.last_price = self._get_last_saved_price() or self.fixed_price
        
        # Notification callbacks
        self.price_update_callbacks = []
        
        # Initialize price feed
        self.price_feed = self._initialize_price_feed()
        
        # Log initialization
        self.logger.info(f"Initialized MarketPriceTrackerStrategy with:")
        self.logger.info(f"  Account: {account}")
        self.logger.info(f"  Trading pair: {base_symbol}/{quote_symbol}")
        self.logger.info(f"  Price source: {self.price_source}")
        self.logger.info(f"  Fixed price: {self.fixed_price}")
        self.logger.info(f"  Update interval: {self.update_interval_ms}ms")
        self.logger.info(f"  Price change threshold: {float(self.price_change_threshold)*100}%")
        self.logger.info(f"  Price file: {self.price_file_path}")
        
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
        
    def fetch_current_price(self) -> Optional[Decimal]:
        """Fetch the current price from the appropriate source."""
        # For LIBRE/BTC, we always use the fixed price
        if self.base_symbol == 'LIBRE' and self.quote_symbol == 'BTC':
            self.logger.debug(f"Using fixed price for {self.base_symbol}/{self.quote_symbol}: {self.fixed_price}")
            return self.fixed_price
            
        # For BTC/USDT, we use Binance if specified
        if self.base_symbol == 'BTC' and self.quote_symbol == 'USDT' and self.price_source == 'binance':
            try:
                price = fetch_btc_usdt_price()
                if price is not None:
                    self.logger.debug(f"Fetched price from Binance for {self.base_symbol}/{self.quote_symbol}: {price}")
                    return Decimal(str(price))
                else:
                    self.logger.warning(f"Failed to fetch price from Binance, using fallback price: {self.fixed_price}")
                    return self.fixed_price
            except Exception as e:
                self.logger.error(f"Error fetching price from Binance: {e}")
                self.logger.warning(f"Using fallback price: {self.fixed_price}")
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
        """Update the price in the price file and notify callbacks."""
        try:
            # Save the price to the file
            write_price(self.price_file_path, float(new_price))
            
            # Update the last price
            self.last_price = new_price
            
            # Notify callbacks
            for callback in self.price_update_callbacks:
                try:
                    callback(new_price)
                except Exception as e:
                    self.logger.error(f"Error in price update callback: {e}")
                    
            self.logger.info(f"Updated price for {self.base_symbol}/{self.quote_symbol} to {new_price}")
            return True
        except Exception as e:
            self.logger.error(f"Error updating price: {e}")
            return False
            
    def run(self):
        """Main execution loop."""
        self.running = True
        self.logger.info(f"Starting MarketPriceTrackerStrategy for {self.base_symbol}/{self.quote_symbol}")
        
        # Initialize with current price
        initial_price = self.fetch_current_price()
        self.update_price(initial_price)
        
        last_update_time = time.time() * 1000  # Convert to milliseconds
        
        try:
            while self.running:
                current_time = time.time() * 1000  # Convert to milliseconds
                
                # Check if it's time to update the price
                if (current_time - last_update_time) >= self.update_interval_ms:
                    # For LIBRE/BTC, we use a fixed price, so we don't need to fetch a new one
                    # For other pairs, fetch the current price from the appropriate source
                    if not (self.base_symbol == 'LIBRE' and self.quote_symbol == 'BTC' and self.price_source == 'fixed'):
                        current_price = self.fetch_current_price()
                        
                        # Only update if the price has changed significantly
                        if current_price is not None and self.is_significant_price_change(current_price):
                            self.update_price(current_price)
                    
                    # Update the last update time
                    last_update_time = current_time
                
                # Sleep to prevent CPU hogging (100ms)
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            self.logger.info("Strategy stopped by user")
        except Exception as e:
            self.logger.error(f"Strategy error: {e}")
        finally:
            self.cleanup()
            
    def cleanup(self):
        """Clean up resources."""
        self.logger.info("Cleaning up MarketPriceTrackerStrategy")
        self.running = False

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