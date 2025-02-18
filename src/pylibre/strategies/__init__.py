from .orderbookfiller import OrderBookFillerStrategy
from .orderbookmaker import OrderBookMakerStrategy
from .marketpricetracker import MarketPriceTrackerStrategy
from .orderbookanimator import OrderBookAnimatorStrategy
from .tradesimulator import TradeSimulatorStrategy
from .coordinator import StrategyCoordinator
from .templates.base_strategy import BaseStrategy

# Add other strategy imports as needed

STRATEGIES = {
    'OrderBookFillerStrategy': OrderBookFillerStrategy,
    'OrderBookMakerStrategy': OrderBookMakerStrategy,
    'MarketPriceTrackerStrategy': MarketPriceTrackerStrategy,
    'OrderBookAnimatorStrategy': OrderBookAnimatorStrategy,
    'TradeSimulatorStrategy': TradeSimulatorStrategy,
    # Add other strategies here
}

def get_strategy_class(name):
    return STRATEGIES.get(name)
