from .random_walk import RandomWalkStrategy
from .market_rate import MarketRateStrategy
from .orderbook_maker import OrderBookMakerStrategy
from typing import Optional, Type
from .templates.base_strategy import BaseStrategy

def get_strategy_class(strategy_name: str) -> Optional[Type[BaseStrategy]]:
    """Get the strategy class based on the strategy name."""
    strategies = {
        'RandomWalkStrategy': RandomWalkStrategy,
        'MarketRateStrategy': MarketRateStrategy,
        'OrderBookMakerStrategy': OrderBookMakerStrategy
    }
    return strategies.get(strategy_name)

__all__ = [
    'RandomWalkStrategy',
    'MarketRateStrategy',
    'OrderBookMakerStrategy',
    'get_strategy_class'
]
