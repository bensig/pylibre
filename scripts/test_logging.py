#!/usr/bin/env python3
"""
Test script to validate the logging changes.
Run this after applying the logging fixes to check that everything works correctly.
"""

import sys
import os
import time
import logging
from decimal import Decimal

# Add the parent directory to the path so we can import the pylibre module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.pylibre.utils.logger import StrategyLogger, LogLevel

def test_logging_levels():
    """Test that the different logging levels work correctly."""
    # Create a test logger with different levels for console and file
    logger = StrategyLogger("LoggingTest", 
                          level=LogLevel.DEBUG,  # DEBUG and above to file
                          console_level=LogLevel.INFO)  # INFO and above to console
    
    print("\n" + "=" * 80)
    print("LOGGING TEST")
    print("=" * 80 + "\n")
    
    print("Sending test messages at different levels...")
    print("DEBUG messages should only appear in the log file, not console")
    
    # Log test messages
    logger.debug("This is a DEBUG message - should only be in log file")
    logger.info("This is an INFO message - should be in console and file")
    logger.warning("This is a WARNING message - should be in console and file")
    logger.error("This is an ERROR message - should be in console and file")
    
    print("\nTest complete!")
    print(f"Check the log file in logs/LoggingTest_*.log for all messages")

def test_price_logging():
    """Test the price update logging to ensure proper threshold handling."""
    logger = StrategyLogger("PriceTest", level=LogLevel.DEBUG)
    
    print("\n" + "=" * 80)
    print("PRICE UPDATE LOGGING TEST")
    print("=" * 80 + "\n")
    
    # Mock the necessary functions
    class MockPriceTracker:
        def __init__(self):
            self.logger = logger.logger
            self.base_symbol = "BTC"
            self.quote_symbol = "USDT"
            self.last_price = None
            self.price_update_callbacks = []
            self.price_change_threshold = Decimal('0.005')  # 0.5%
        
        def write_price(self, path, price):
            # Mock function
            print(f"Would write price {price} to {path}")
    
    tracker = MockPriceTracker()
    
    # Helper function to call correct update_price logic
    def update_price(tracker, new_price):
        # Similar implementation to MarketPriceTrackerStrategy.update_price
        try:
            # Get current price for comparison
            current_price = tracker.last_price
            
            # Only log if price actually changed (with minimum threshold)
            threshold = tracker.price_change_threshold
            
            # Save the price to the file
            print(f"Would save price {new_price} to file")
            
            # Determine if this is a significant change
            is_significant = False
            if current_price is None:
                tracker.logger.info(f"Setting initial price: {new_price} {tracker.quote_symbol}")
                is_significant = True
            elif current_price == Decimal('0'):
                tracker.logger.info(f"Setting price from zero: {new_price} {tracker.quote_symbol}")
                is_significant = True
            elif abs(new_price - current_price) / current_price > threshold:
                change_pct = ((new_price - current_price) / current_price) * 100
                tracker.logger.info(f"Price updated: {tracker.base_symbol}/{tracker.quote_symbol} from {current_price} to {new_price} ({change_pct:.2f}%)")
                is_significant = True
            else:
                # Minor change, log at debug level only
                tracker.logger.debug(f"Minor price update: {current_price} → {new_price} {tracker.quote_symbol}")
                
            # Update the last price
            tracker.last_price = new_price
            
            return True
        except Exception as e:
            tracker.logger.error(f"Error updating price: {e}")
            return False
    
    # Test cases
    print("Testing initial price set")
    update_price(tracker, Decimal('50000'))
    
    print("\nTesting minor price update (< 0.5% change)")
    update_price(tracker, Decimal('50200'))  # 0.4% change
    
    print("\nTesting significant price update (> 0.5% change)")
    update_price(tracker, Decimal('50500'))  # 1% change
    
    print("\nTesting downward significant price move")
    update_price(tracker, Decimal('49000'))  # ~3% drop
    
    print("\nTest complete!")
    print(f"Check the log file in logs/PriceTest_*.log for all messages")
    

if __name__ == "__main__":
    test_logging_levels()
    time.sleep(1)  # Pause between tests
    test_price_logging()
