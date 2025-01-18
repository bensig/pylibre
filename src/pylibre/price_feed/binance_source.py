from decimal import Decimal
from typing import Optional
from .base import PriceSource
from ..utils.binance_api import fetch_btc_usdt_price

class BinancePriceSource(PriceSource):
    """Price source that fetches from Binance."""
    
    def __init__(self, symbol: str):
        """Initialize with a trading symbol.
        
        Args:
            symbol: Trading symbol (e.g. "BTCUSDT")
        """
        self.symbol = symbol
        
    async def get_price(self) -> Optional[Decimal]:
        """Get current price from Binance.
        
        Returns:
            Decimal: Current price or None if unavailable
        """
        price = fetch_btc_usdt_price()
        return Decimal(str(price)) if price is not None else None
        
    async def start(self):
        """No special initialization needed."""
        pass
        
    async def stop(self):
        """No cleanup needed."""
        pass 