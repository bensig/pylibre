from .random_walk import RandomWalkStrategy
from .market_rate import MarketRateStrategy
from .orderbook_filler import OrderBookFillerStrategy
from typing import Optional, Type
from .templates.base_strategy import BaseStrategy

def get_strategy_class(strategy_name: str) -> Optional[Type[BaseStrategy]]:
    """Get the strategy class based on the strategy name."""
    strategies = {
        'RandomWalkStrategy': RandomWalkStrategy,
        'MarketRateStrategy': MarketRateStrategy,
        'OrderBookFillerStrategy': OrderBookFillerStrategy
    }
    return strategies.get(strategy_name)

__all__ = [
    'RandomWalkStrategy',
    'MarketRateStrategy',
    'OrderBookMakerStrategy',
    'OrderBookFillerStrategy',
    'get_strategy_class'
]
