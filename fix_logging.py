#!/usr/bin/env python3
"""
Script to implement logging improvements for the PyLibre trading system.
This will modify several files to fix the identified logging issues.
"""

import os
import sys
import re
import shutil
from pathlib import Path
from datetime import datetime

def backup_file(filepath):
    """Create a backup of a file before modifying it."""
    backup_path = f"{filepath}.bak.{datetime.now().strftime('%Y%m%d%H%M%S')}"
    shutil.copy2(filepath, backup_path)
    print(f"Backed up {filepath} to {backup_path}")
    return backup_path

def update_logger_py():
    """Update the logger.py file to support different console and file logging levels."""
    filepath = "src/pylibre/utils/logger.py"
    
    # Ensure directory exists
    if not os.path.exists(filepath):
        print(f"ERROR: {filepath} not found. Make sure you're running this from the project root.")
        return False
    
    # Backup original file
    backup_file(filepath)
    
    # Read the current content
    with open(filepath, 'r') as f:
        content = f.read()
    
    # New logger implementation
    new_logger_class = '''
class StrategyLogger:
    def __init__(self, strategy_name: str, level: LogLevel = LogLevel.INFO, 
                 console_level: LogLevel = LogLevel.INFO):
        # Create logs directory if it doesn't exist
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        
        # Create a logger
        self.logger = logging.getLogger(f"pylibre.{strategy_name}")
        self.logger.setLevel(min(level.value, console_level.value))  # Set to lowest level
        
        # Prevent duplicate handlers
        if not self.logger.handlers:
            # File handler - detailed logs
            timestamp = datetime.now().strftime("%Y%m%d")
            file_handler = logging.FileHandler(
                f"{log_dir}/{strategy_name}_{timestamp}.log"
            )
            file_formatter = logging.Formatter(
                '%(asctime)s | %(levelname)s | %(message)s'
            )
            file_handler.setFormatter(file_formatter)
            file_handler.setLevel(level.value)
            self.logger.addHandler(file_handler)
            
            # Console handler - more concise logs
            console_handler = logging.StreamHandler()
            console_formatter = logging.Formatter(
                '%(asctime)s | %(name)s | %(levelname)s | %(message)s'
            )
            console_handler.setFormatter(console_formatter)
            console_handler.setLevel(console_level.value)  # Higher level for console
            self.logger.addHandler(console_handler)
    '''
    
    # Replace the existing StrategyLogger class with the new implementation
    pattern = r'class StrategyLogger:[\s\S]*?def error\(self, msg: str\) -> None:[\s\S]*?self\.logger\.error\(msg\)'
    if re.search(pattern, content):
        updated_content = re.sub(pattern, new_logger_class + '''
    def debug(self, msg: str) -> None:
        self.logger.debug(msg)
        
    def info(self, msg: str) -> None:
        self.logger.info(msg)
        
    def warning(self, msg: str) -> None:
        self.logger.warning(msg)
        
    def error(self, msg: str) -> None:
        self.logger.error(msg)''', content)
        
        # Write the updated content
        with open(filepath, 'w') as f:
            f.write(updated_content)
        
        print(f"Updated {filepath} with new StrategyLogger implementation")
        return True
    else:
        print(f"ERROR: Could not find StrategyLogger class in {filepath}")
        return False

def update_run_strategy_coordinator():
    """Update the run_strategy_coordinator.py script with improved logging and signal handling."""
    filepath = "scripts/run_strategy_coordinator.py"
    
    # Ensure directory exists
    if not os.path.exists(filepath):
        print(f"ERROR: {filepath} not found. Make sure you're running this from the project root.")
        return False
    
    # Backup original file
    backup_file(filepath)
    
    # Read the current content
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Add imports if needed
    imports_to_add = '''import logging.handlers
from datetime import datetime
'''
    if "logging.handlers" not in content:
        import_pattern = r'import logging\n'
        content = re.sub(import_pattern, imports_to_add, content)
    
    # Update signal handler
    new_signal_handler = '''def signal_handler(sig, frame):
    """Handle Ctrl+C and other signals to gracefully stop the coordinator."""
    global running
    print("\\nStopping coordinator (this may take a moment)...")
    print("Please wait while strategies are being stopped...")
    running = False
    
    # Log termination signal
    logger = logging.getLogger("StrategyCoordinator")
    logger.warning(f"Received termination signal {sig}, shutting down gracefully")
    
    # Give the coordinator time to clean up
    for i in range(5, 0, -1):
        print(f"Shutting down in {i} seconds...")
        time.sleep(1)
    
    # Force exit if still running after timeout
    print("Coordinator shutdown complete")
    sys.exit(0)
'''
    
    signal_pattern = r'def signal_handler\(sig, frame\):[\s\S]*?running = False'
    if re.search(signal_pattern, content):
        content = re.sub(signal_pattern, new_signal_handler, content)
    
    # Add setup_logging function
    setup_logging_func = '''
def setup_logging():
    """Configure logging with rotation to prevent large log files."""
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # Capture all logs
    
    # Console handler - INFO level
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    console_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console.setFormatter(console_format)
    
    # File handler with rotation - DEBUG level (detailed logs)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = f"{log_dir}/coordinator_{timestamp}.log"
    file_handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=10*1024*1024, backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    file_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_format)
    
    # Add handlers
    root_logger.handlers = []  # Remove existing handlers
    root_logger.addHandler(console)
    root_logger.addHandler(file_handler)
    
    return root_logger
'''
    
    # Add the setup_logging function before the main function
    main_pattern = r'def main\(\):'
    content = re.sub(main_pattern, setup_logging_func + '\ndef main():', content)
    
    # Update the logging setup in main
    main_logging_pattern = r'# Setup logging\s+logging\.basicConfig\([^)]+\)'
    new_logging_setup = '''# Setup enhanced logging
    logger = setup_logging()'''
    
    if re.search(main_logging_pattern, content):
        content = re.sub(main_logging_pattern, new_logging_setup, content)
    else:
        # If pattern not found, add it before the "main()" call
        main_call_pattern = r'main\(\)'
        content = re.sub(main_call_pattern, f"{new_logging_setup}\n        main()", content)
    
    # Write the updated content
    with open(filepath, 'w') as f:
        f.write(content)
    
    print(f"Updated {filepath} with improved logging and signal handling")
    return True

def patch_marketpricetracker():
    """Update the MarketPriceTrackerStrategy to have better price update logging."""
    filepath = "src/pylibre/strategies/marketpricetracker.py"
    
    # Check if file exists
    if not os.path.exists(filepath):
        print(f"ERROR: {filepath} not found. Skipping...")
        return False
    
    # Backup original file
    backup_file(filepath)
    
    # Read the current content
    with open(filepath, 'r') as f:
        content = f.read()
    
    # New update_price method
    new_update_price = '''    def update_price(self, new_price):
        """Update the current price and notify other strategies."""
        current_price = self.current_price
        
        # Only log if price actually changed (with minimum threshold)
        threshold = self.parameters.get('price_change_threshold', 0.001)  # 0.1% default
        if current_price is None:
            self.logger.info(f"Setting initial price: {new_price} {self.quote_symbol}")
        elif abs(new_price - current_price) / current_price > threshold:
            change_pct = ((new_price - current_price) / current_price) * 100
            self.logger.info(f"Price updated: {self.base_symbol}/{self.quote_symbol} from {current_price} to {new_price} ({change_pct:.2f}%)")
        else:
            # Still update price but log at debug level only
            self.logger.debug(f"Minor price update: {current_price} → {new_price} {self.quote_symbol}")
        
        # Update price and notify observers
        self.current_price = new_price
        for callback in self.price_callbacks:
            callback(new_price)'''
    
    # Look for the update_price method
    update_price_pattern = r'def update_price\(self, new_price\):[\s\S]*?for callback in self\.price_callbacks:[\s\S]*?callback\(new_price\)'
    
    if re.search(update_price_pattern, content):
        content = re.sub(update_price_pattern, new_update_price, content)
        
        # Write the updated content
        with open(filepath, 'w') as f:
            f.write(content)
        
        print(f"Updated {filepath} with improved price update logging")
        return True
    else:
        print(f"ERROR: Could not find update_price method in {filepath}")
        return False

def create_test_script():
    """Create a test script to validate the logging changes."""
    filepath = "scripts/test_logging.py"
    
    script_content = '''#!/usr/bin/env python3
"""
Test script to validate the logging changes.
Run this after applying the logging fixes to check that everything works correctly.
"""

import sys
import os
import time
import logging

# Add the parent directory to the path so we can import the pylibre module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.pylibre.utils.logger import StrategyLogger, LogLevel

def test_logging_levels():
    """Test that the different logging levels work correctly."""
    # Create a test logger with different levels for console and file
    logger = StrategyLogger("LoggingTest", 
                           level=LogLevel.DEBUG,  # DEBUG and above to file
                           console_level=LogLevel.INFO)  # INFO and above to console
    
    print("\\n" + "=" * 80)
    print("LOGGING TEST")
    print("=" * 80 + "\\n")
    
    print("Sending test messages at different levels...")
    print("DEBUG messages should only appear in the log file, not console")
    
    # Log test messages
    logger.debug("This is a DEBUG message - should only be in log file")
    logger.info("This is an INFO message - should be in console and file")
    logger.warning("This is a WARNING message - should be in console and file")
    logger.error("This is an ERROR message - should be in console and file")
    
    print("\\nTest complete!")
    print(f"Check the log file in logs/LoggingTest_*.log for all messages")

if __name__ == "__main__":
    test_logging_levels()
'''
    
    with open(filepath, 'w') as f:
        f.write(script_content)
    
    # Make the script executable
    os.chmod(filepath, 0o755)
    
    print(f"Created test script at {filepath}")
    return True

def main():
    """Main function to run all the updates."""
    print("=" * 80)
    print("PyLibre Logging Improvements Script")
    print("=" * 80)
    print()
    
    # Check if we're in the right directory
    if not os.path.exists("src/pylibre") or not os.path.exists("scripts"):
        print("ERROR: This script must be run from the project root directory")
        print("       that contains the src/pylibre and scripts directories.")
        return 1
    
    print("Beginning updates...")
    
    # Update files
    success = []
    success.append(update_logger_py())
    success.append(update_run_strategy_coordinator())
    success.append(patch_marketpricetracker())
    success.append(create_test_script())
    
    # Print summary
    print("\n" + "=" * 80)
    print("Update Summary")
    print("=" * 80)
    
    if all(success):
        print("✅ All updates completed successfully!")
    else:
        print("⚠️ Some updates failed. Please check the log above for details.")
    
    print("\nNext Steps:")
    print("1. Review the changes made to the files")
    print("2. Run the test script to verify logging works correctly:")
    print("   python scripts/test_logging.py")
    print("3. Start the coordinator with your normal command to test in a real environment")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 