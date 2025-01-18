from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Optional

class PriceSource(ABC):
    """Base class for all price sources."""
    
    @abstractmethod
    async def get_price(self) -> Optional[Decimal]:
        """Get the current price.
        
        Returns:
            Decimal: Current price or None if unavailable
        """
        pass
        
    @abstractmethod
    async def start(self):
        """Initialize the price source."""
        pass
        
    @abstractmethod
    async def stop(self):
        """Clean up resources."""
        pass 