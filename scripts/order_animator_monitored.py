#!/usr/bin/env python3
"""
Enhanced Order Animator with monitoring integration.
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

# Import the original animator
from scripts.order_animator import OrderAnimator, logger
from src.pylibre.utils.shared_data import SharedDataManager

class MonitoredOrderAnimator(OrderAnimator):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.monitor_data_dir = Path("monitor_data")
        self.monitor_data_dir.mkdir(exist_ok=True)
        self.shared_data = SharedDataManager()
        self.strategy_id = f"OrderAnimator_{self.account}_BTC_USDT"
        self.start_time = datetime.utcnow()
        self.cycles_completed = 0
        self.orders_animated = 0
        
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
                "type": "OrderAnimator",
                "trading_pair": "BTC/USDT",
                "account": self.account,
                "parameters": {
                    "interval": self.interval,
                    "min_orders": self.min_orders,
                    "max_orders": self.max_orders
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
                "orders_animated": self.orders_animated,
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
                
        except Exception as e:
            logger.error(f"Failed to update monitoring: {e}")
    
    def animate_orders(self):
        """Override to add monitoring."""
        result = super().animate_orders()
        if result:
            self.orders_animated += len(result.get('animated', []))
        self.cycles_completed += 1
        self.update_monitoring()
        return result
    
    def run(self):
        """Override to add initial monitoring update."""
        self.update_monitoring()
        super().run()

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Animate orderbook with monitoring')
    parser.add_argument('--interval', type=int, default=5, help='Interval between animations in seconds')
    parser.add_argument('--min-orders', type=int, default=2, help='Minimum orders to animate per cycle')
    parser.add_argument('--max-orders', type=int, default=8, help='Maximum orders to animate per cycle')
    parser.add_argument('--config', default='config/config.yaml', help='Config file path')
    parser.add_argument('--strategy-config', default='config/strategies.mainnet.yaml', help='Strategy config file path')
    parser.add_argument('--run-once', action='store_true', help='Run one cycle and exit')
    
    args = parser.parse_args()
    
    try:
        animator = MonitoredOrderAnimator(
            config_path=args.config,
            strategy_config_path=args.strategy_config
        )
        animator.interval = args.interval
        animator.min_orders = args.min_orders
        animator.max_orders = args.max_orders
        
        if args.run_once:
            logger.info("Running single animation cycle...")
            animator.animate_orders()
            logger.info("Single cycle complete")
            return
        
        animator.run()
    except Exception as e:
        logger.exception(f"Failed to start monitored animator: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()