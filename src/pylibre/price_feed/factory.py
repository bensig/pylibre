from typing import Dict, Any
from .base import PriceSource
from .binance_source import BinancePriceSource
from .fixed_source import FixedPriceSource

class PriceFeedFactory:
    """Factory for creating price feed sources."""
    
    @staticmethod
    def create_price_source(config: Dict[str, Any]) -> PriceSource:
        """Create a price source based on configuration.
        
        Args:
            config: Price source configuration dictionary containing:
                - source: Type of price source ("binance" or "fixed")
                - reference_symbol: Symbol for Binance source
                - price: Fixed price value for fixed source
            
        Returns:
            PriceSource: Configured price source instance
            
        Raises:
            ValueError: If source type is unknown
        """
        source_type = config.get("source")
        
        if source_type == "binance":
            return BinancePriceSource(config["reference_symbol"])
        elif source_type == "fixed":
            return FixedPriceSource(config["price"])
        else:
            raise ValueError(f"Unknown price source type: {source_type}") 