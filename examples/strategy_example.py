#!/usr/bin/env python3
from pylibre.manager.config_manager import ConfigManager
from pylibre.manager.trading_manager import TradingManager
import asyncio
import sys

async def main():
    """Example of how to run a strategy group using the new configuration system."""
    try:
        # Load configuration
        config_manager = ConfigManager("config/config.yaml")
        
        # Initialize trading manager
        trading_manager = TradingManager(config_manager)
        
        print("\n🚀 Running BTC market making example")
        print("Press Ctrl+C to stop\n")
        
        # Run the btc_market_making strategy group
        await trading_manager.start_all("btc_market_making")
        
    except KeyboardInterrupt:
        print("\n👋 Shutting down...")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 