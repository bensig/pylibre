import asyncio
from typing import Dict, Any, Optional
from ..strategies import get_strategy_class
from ..price_feed import PriceFeedFactory
from .config_manager import ConfigManager
from ..utils.logger import StrategyLogger, LogLevel

class TradingManager:
    """Manages the execution of trading strategies."""
    
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.logger = StrategyLogger("TradingManager", level=LogLevel.INFO)
        self.running_strategies = {}
        self.price_feeds = {}
        
    async def start_strategy(self, strategy_config: Dict[str, Any], pair: str, price_sources: Dict[str, Any]):
        """Start a single strategy."""
        strategy_name = strategy_config["name"]
        account = strategy_config["account"]
        parameters = strategy_config["parameters"]
        
        # Get strategy class
        strategy_class = get_strategy_class(strategy_name)
        if not strategy_class:
            self.logger.error(f"Strategy {strategy_name} not found")
            return None
            
        # Initialize price feed if needed
        if pair not in self.price_feeds and pair in price_sources:
            price_feed = PriceFeedFactory.create_price_feed(
                pair=pair,
                **price_sources[pair]
            )
            if price_feed:
                await price_feed.start()
                self.price_feeds[pair] = price_feed
        
        # Initialize strategy
        strategy = strategy_class(
            pair=pair,
            account=account,
            parameters=parameters,
            price_feed=self.price_feeds.get(pair)
        )
        
        # Start strategy
        await strategy.start()
        
        # Store running strategy
        strategy_id = f"{strategy_name}_{account}_{pair}"
        self.running_strategies[strategy_id] = strategy
        
        return strategy
        
    async def start_all(self, group_name: str):
        """Start all strategies in a group."""
        group_config = self.config_manager.get_strategy_group(group_name)
        if not group_config:
            self.logger.error(f"Strategy group {group_name} not found")
            return
            
        pair = group_config["pairs"][0]  # Currently supporting one pair per group
        price_sources = group_config.get("price_sources", {})
        
        # Start each strategy in the group
        for strategy_config in group_config["strategies"]:
            await self.start_strategy(strategy_config, pair, price_sources)
            
        self.logger.info(f"Started all strategies in group {group_name}")
        
    async def stop_all(self):
        """Stop all running strategies."""
        for strategy in self.running_strategies.values():
            await strategy.stop()
            
        for price_feed in self.price_feeds.values():
            await price_feed.stop()
            
        self.running_strategies.clear()
        self.price_feeds.clear()
        
        self.logger.info("Stopped all strategies") 