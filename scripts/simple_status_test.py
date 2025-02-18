#!/usr/bin/env python3
"""
Simple script to test the status report functionality of the StrategyCoordinator.
"""

import sys
import os
import time

# Add the parent directory to the path so we can import the pylibre module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.pylibre import LibreClient
from src.pylibre.strategies import StrategyCoordinator

def main():
    """Test the status report functionality."""
    print("\n=== STRATEGY COORDINATOR STATUS REPORT TEST ===\n")
    
    # Initialize LibreClient
    print("Initializing LibreClient...")
    client = LibreClient(api_url="https://testnet.libre.org", verbose=False)
    
    # Create a simple coordinator configuration
    coordinator_config = {
        'account': 'dextester',
        'base_symbol': 'BTC',
        'quote_symbol': 'USDT',
        'strategies': {}
    }
    
    try:
        # Create coordinator
        print("\nCreating StrategyCoordinator...")
        coordinator = StrategyCoordinator(client, coordinator_config)
        
        # Check if the status report methods exist
        has_get_report = hasattr(coordinator, 'get_status_report')
        has_print_report = hasattr(coordinator, 'print_status_report')
        
        print(f"Has get_status_report method: {has_get_report}")
        print(f"Has print_status_report method: {has_print_report}")
        
        # Try to get a status report
        if has_get_report:
            print("\nGetting status report...")
            report = coordinator.get_status_report()
            print("Status report data:")
            print(f"  Coordinator running: {report['coordinator']['running']}")
            print(f"  Trading pair: {report['coordinator']['trading_pair']}")
            print(f"  Total strategies: {report['coordinator']['total_strategies']}")
            print(f"  Status counts: {report['coordinator']['status_counts']}")
        
        # Try to print a status report
        if has_print_report:
            print("\nPrinting status report...")
            coordinator.print_status_report()
        
    except Exception as e:
        print(f"Error during test: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
    
    print("\nTest completed.")

if __name__ == "__main__":
    main()
