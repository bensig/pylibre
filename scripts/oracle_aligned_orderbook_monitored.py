#!/usr/bin/env python3
"""
Enhanced Oracle Aligned Orderbook with monitoring integration.
This version integrates with the PyLibre monitoring system.
"""

import os
import sys
import json
import time
from datetime import datetime
from pathlib import Path

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the original manager
from scripts.oracle_aligned_orderbook import OracleAlignedOrderbookManager
from src.pylibre.utils.shared_data import SharedDataManager

class MonitoredOracleAlignedOrderbookManager(OracleAlignedOrderbookManager):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.monitor_data_dir = Path("monitor_data")
        self.monitor_data_dir.mkdir(exist_ok=True)
        self.shared_data = SharedDataManager()
        self.strategy_id = f"OracleAlignedOrderbook_{self.account}_BTC_USDT"
        self.start_time = datetime.utcnow()
        self.cycles_completed = 0
        self.orders_placed = 0
        self.orders_cancelled = 0
        self.last_oracle_price = None
        
    def update_monitoring(self):
        """Update monitoring data files."""
        try:
            # Update strategy status
            strategies_file = self.monitor_data_dir / "strategies.json"
            strategies = {}
            if strategies_file.exists():
                with open(strategies_file, 'r') as f:
                    strategies = json.load(f)
            
            strategies[self.strategy_id] = {
                "id": self.strategy_id,
                "type": "OracleAlignedOrderbook",
                "trading_pair": "BTC/USDT",
                "account": self.account,
                "parameters": {
                    "orders_per_side": self.orders_per_side,
                    "min_spread_percentage": float(self.min_spread_percentage),
                    "max_spread_percentage": float(self.max_spread_percentage),
                    "batch_size": self.batch_size,
                    "batch_delay_ms": self.batch_delay_ms
                },
                "status": "running",
                "start_time": self.start_time.isoformat(),
                "last_active": datetime.utcnow().isoformat()
            }
            
            with open(strategies_file, 'w') as f:
                json.dump(strategies, f, indent=2)
            
            # Update metrics
            metrics_file = self.monitor_data_dir / "metrics.json"
            metrics = {}
            if metrics_file.exists():
                with open(metrics_file, 'r') as f:
                    metrics = json.load(f)
            
            metrics[self.strategy_id] = {
                "cycles_completed": self.cycles_completed,
                "orders_placed": self.orders_placed,
                "orders_cancelled": self.orders_cancelled,
                "last_oracle_price": float(self.last_oracle_price) if self.last_oracle_price else None,
                "uptime_seconds": (datetime.utcnow() - self.start_time).total_seconds(),
                "last_update": datetime.utcnow().isoformat()
            }
            
            with open(metrics_file, 'w') as f:
                json.dump(metrics, f, indent=2)
            
            # Update last update timestamp
            last_update_file = self.monitor_data_dir / "last_update.json"
            last_updates = {}
            if last_update_file.exists():
                with open(last_update_file, 'r') as f:
                    last_updates = json.load(f)
            
            last_updates[self.strategy_id] = datetime.utcnow().isoformat()
            
            with open(last_update_file, 'w') as f:
                json.dump(last_updates, f, indent=2)
            
            # Update shared price data if we have oracle price
            if self.last_oracle_price:
                self.shared_data.update_price("btcusdt", float(self.last_oracle_price))
                
        except Exception as e:
            print(f"Failed to update monitoring: {e}")
    
    def get_oracle_price(self):
        """Override to capture oracle price."""
        price = super().get_oracle_price()
        if price:
            self.last_oracle_price = price
        return price
    
    def manage_orderbook(self):
        """Override to add monitoring."""
        # Track metrics before management
        orders_before = self.orders_placed
        cancels_before = self.orders_cancelled
        
        # Run the management cycle
        super().manage_orderbook()
        
        # Update counters based on what happened
        # Note: You might need to modify the base class to return these counts
        # For now, we'll increment the cycle counter
        self.cycles_completed += 1
        
        # Update monitoring
        self.update_monitoring()
    
    def place_order(self, order_type, quantity, price):
        """Override to track placed orders."""
        result = super().place_order(order_type, quantity, price)
        if result:
            self.orders_placed += 1
        return result
    
    def cancel_order(self, order_id):
        """Override to track cancelled orders."""
        result = super().cancel_order(order_id)
        if result:
            self.orders_cancelled += 1
        return result
    
    def run(self):
        """Override to add initial monitoring update."""
        self.update_monitoring()
        super().run()

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Manage oracle-aligned orderbook with monitoring')
    parser.add_argument('--run-once', action='store_true', help='Run one cycle and exit')
    
    args = parser.parse_args()
    
    try:
        manager = MonitoredOracleAlignedOrderbookManager(run_once=args.run_once)
        
        if args.run_once:
            print("Running single management cycle...")
            manager.manage_orderbook()
            print("Single cycle complete")
            return
        
        manager.run()
    except Exception as e:
        print(f"Failed to start monitored manager: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()