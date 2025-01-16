import requests
from decimal import Decimal
from typing import Optional

class BinancePriceFeed:
    """Price feed implementation using Binance API."""
    
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.api_url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
        
    def get_price(self) -> Optional[Decimal]:
        """Get current price from Binance."""
        try:
            response = requests.get(self.api_url)
            if response.status_code != 200:
                raise Exception(f"Binance API error: {response.status_code}")
                
            data = response.json()
            return Decimal(data["price"])
            
        except Exception as e:
            raise Exception(f"Failed to fetch price: {str(e)}")

class PriceFeed:
    """Base class for price feeds."""
    
    def get_price(self) -> Optional[Decimal]:
        """Get current price. Must be implemented by subclasses."""
        raise NotImplementedError() 