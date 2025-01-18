#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path
import json
import asyncio
import signal
from typing import Dict, Any
import logging
import subprocess

# Add project root to Python path
sys.path.append(str(Path(__file__).parent.parent))

from pylibre.manager.config_manager import ConfigManager
from pylibre.manager.trading_manager import TradingManager

class ServiceManager:
    def __init__(self, config_manager: ConfigManager, strategy_group: str):
        self.config_manager = config_manager
        self.strategy_group = strategy_group
        self.group_config = config_manager.get_strategy_group(strategy_group)
        self.price_fetcher_process = None
        self.running = True
        self.logger = self._setup_logging()

    def _setup_logging(self) -> logging.Logger:
        logger = logging.getLogger("ServiceManager")
        logger.setLevel(logging.INFO)
        return logger

    async def start_price_fetcher(self):
        """Start the price fetcher script as a subprocess."""
        if "price_sources" in self.group_config:
            script_path = Path(__file__).parent / "fetch_prices.py"
            self.logger.info(f"Starting price fetcher: {script_path}")
            
            # Start the price fetcher script as a subprocess
            self.price_fetcher_process = subprocess.Popen(
                [sys.executable, str(script_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            self.logger.info("Price fetcher started")

    async def stop_price_fetcher(self):
        """Stop the price fetcher subprocess."""
        if self.price_fetcher_process:
            self.logger.info("Stopping price fetcher")
            self.price_fetcher_process.terminate()
            try:
                self.price_fetcher_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.price_fetcher_process.kill()
            self.logger.info("Price fetcher stopped")

    def handle_shutdown(self, signum, frame):
        """Handle shutdown signals."""
        self.logger.info("Shutdown signal received")
        self.running = False

    async def run(self):
        """Run the service manager."""
        # Setup signal handlers
        signal.signal(signal.SIGINT, self.handle_shutdown)
        signal.signal(signal.SIGTERM, self.handle_shutdown)

        try:
            # Start price fetcher for BTC/USDT if needed
            await self.start_price_fetcher()

            # TODO: Start trading manager here in next phase
            
            # Keep running until shutdown
            while self.running:
                if self.price_fetcher_process:
                    # Check if price fetcher is still running
                    if self.price_fetcher_process.poll() is not None:
                        self.logger.error("Price fetcher process died, restarting...")
                        await self.start_price_fetcher()
                await asyncio.sleep(1)

        finally:
            # Cleanup
            await self.stop_price_fetcher()

def print_strategy_group_info(group_name: str, group: dict) -> None:
    """Print information about a strategy group."""
    print(f"\nStrategy Group: {group_name}")
    print(f"Description: {group.get('description', 'No description')}")
    print(f"Network: {group['network']}")
    print(f"Trading Pairs: {', '.join(group['pairs'])}")
    
    print("\nStrategies:")
    for strategy in group['strategies']:
        print(f"\n  {strategy['name']}:")
        print(f"    Accounts: {', '.join(strategy['accounts'])}")
        print(f"    Parameters:")
        for key, value in strategy.get('parameters', {}).items():
            print(f"      {key}: {value}")

async def main():
    parser = argparse.ArgumentParser(description='Run trading strategies')
    parser.add_argument('strategy_group', help='Strategy group to run')
    parser.add_argument('--config', default='config/config.yaml', help='Path to config file')
    args = parser.parse_args()
    
    try:
        config_manager = ConfigManager(args.config)
        trading_manager = TradingManager(config_manager)
        await trading_manager.start_all(args.strategy_group)
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())