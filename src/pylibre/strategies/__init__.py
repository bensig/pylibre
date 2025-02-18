from .orderbookfiller import OrderBookFillerStrategy
from .templates.base_strategy import BaseStrategy

# Add other strategy imports as needed

STRATEGIES = {
    'OrderBookFillerStrategy': OrderBookFillerStrategy,
    # Add other strategies here
}

def get_strategy_class(name):
    return STRATEGIES.get(name)
