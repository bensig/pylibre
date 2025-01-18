from decimal import Decimal
from typing import Optional
from .base import PriceSource

class FixedPriceSource(PriceSource):
    """Price source that returns a fixed price."""
    
    def __init__(self, price: str):
        """Initialize with a fixed price value.
        
        Args:
            price: Fixed price as a string (e.g. "0.00000001" for 1 SAT)
        """
        self.price = Decimal(price)
        
    async def get_price(self) -> Optional[Decimal]:
        """Return the fixed price.
        
        Returns:
            Decimal: The configured fixed price
        """
        return self.price
        
    async def start(self):
        """No startup needed for fixed price source."""
        pass
        
    async def stop(self):
        """No cleanup needed for fixed price source."""
        pass 