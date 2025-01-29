from typing import Dict, Any, Optional
import asyncio
import logging
from pylibre import LibreClient
from pylibre.strategies import get_strategy_class
from pylibre.utils.logger import StrategyLogger, LogLevel

class TradingManager:
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.strategies = {}
        self.logger = StrategyLogger("TradingManager", level=LogLevel.INFO)

    async def start_all(self, group_name: str) -> None:
        """Start all strategies in a group."""
        group_config = self.config_manager.get_strategy_group(group_name)
        if not group_config:
            raise ValueError(f"Strategy group {group_name} not found")

        network = "testnet"  # For now, hardcode to testnet
        network_config = self.config_manager.get_network_config(network)
        
        for pair in group_config["pairs"]:
            base_symbol, quote_symbol = pair.split("/")
            
            for strategy_config in group_config["strategies"]:
                account = strategy_config["account"]
                strategy_name = strategy_config["name"]
                
                # Get strategy parameters
                parameters = self.config_manager.get_strategy_parameters(strategy_name, pair)
                
                try:
                    # Initialize client
                    client = LibreClient(
                        network=network,
                        config_path=self.config_manager.config_path
                    )
                    
                    # Get strategy class and create instance
                    strategy_class = get_strategy_class(strategy_name)
                    if not strategy_class:
                        self.logger.error(f"Strategy class not found: {strategy_name}")
                        continue
                        
                    strategy = strategy_class(
                        client=client,
                        account=account,
                        base_symbol=base_symbol,
                        quote_symbol=quote_symbol,
                        parameters=parameters
                    )
                    
                    # Store strategy instance
                    key = f"{account}_{pair}_{strategy_name}"
                    self.strategies[key] = strategy
                    
                    # Start strategy in background
                    asyncio.create_task(self._run_strategy(strategy, key))
                    self.logger.info(f"Started {strategy_name} for {account} on {pair}")
                    
                except Exception as e:
                    self.logger.error(f"Error starting strategy {strategy_name} for {account}: {e}")

    async def _run_strategy(self, strategy, key: str) -> None:
        """Run a single strategy."""
        try:
            await asyncio.get_event_loop().run_in_executor(None, strategy.run)
        except Exception as e:
            self.logger.error(f"Strategy {key} failed: {e}")
        finally:
            if key in self.strategies:
                del self.strategies[key]

    async def stop_all(self) -> None:
        """Stop all running strategies."""
        for strategy in self.strategies.values():
            strategy.running = False
        self.strategies.clear() 