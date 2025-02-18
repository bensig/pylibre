from .base import PriceSource
from .binance_source import BinancePriceSource
from .fixed_source import FixedPriceSource
from .factory import PriceFeedFactory
from decimal import Decimal
from typing import Optional, Dict, Any

# Create BasePriceFeed as an alias for PriceSource to fix import errors
class BasePriceFeed(PriceSource):
    """
    Base class for all price feeds. This is an alias for PriceSource.
    """
    def __init__(self, base_symbol: str, quote_symbol: str, parameters: Dict[str, Any] = None):
        self.base_symbol = base_symbol
        self.quote_symbol = quote_symbol
        self.parameters = parameters or {}

    async def get_price(self) -> Optional[Decimal]:
        """Get the current price for the trading pair."""
        pass
        
    async def start(self):
        """Initialize the price feed."""
        pass
        
    async def stop(self):
        """Clean up resources."""
        pass

__all__ = [
    'PriceSource',
    'BinancePriceSource',
    'FixedPriceSource',
    'PriceFeedFactory',
    'BasePriceFeed'
] 