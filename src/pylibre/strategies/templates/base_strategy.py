from abc import ABC, abstractmethod
from typing import Dict, Any
from pylibre import LibreClient
from pylibre.dex import DexClient

class BaseStrategy(ABC):
    def __init__(self, 
                 client: LibreClient,
                 account: str,
                 quote_symbol: str,
                 base_symbol: str,
                 config: Dict[str, Any]):
        """
        Initialize the base strategy.
        
        Args:
            client: LibreClient instance for blockchain interaction
            account: Trading account name
            quote_symbol: Base asset symbol (e.g., 'BTC')
            base_symbol: Quote asset symbol (e.g., 'LIBRE')
            config: Strategy-specific configuration parameters
        """
        self.client = client
        self.dex = DexClient(client)
        self.account = account
        self.quote_symbol = quote_symbol
        self.base_symbol = base_symbol
        self.config = config
        self.is_running = False

    @abstractmethod
    def generate_signal(self) -> Dict[str, Any]:
        """
        Generate trading signals based on strategy logic.
        
        Returns:
            Dict containing signal information (e.g., price, direction, size)
        """
        pass

    @abstractmethod
    def place_orders(self, signal: Dict[str, Any]) -> bool:
        """
        Place orders based on the generated signal.
        
        Args:
            signal: The trading signal from generate_signal()
            
        Returns:
            bool: Success status of order placement
        """
        pass

    def cancel_orders(self) -> bool:
        """
        Cancel all existing orders for the account.
        
        Returns:
            bool: Success status of cancellation
        """
        try:
            order_book = self.dex.fetch_order_book(
                quote_symbol=self.quote_symbol,
                base_symbol=self.base_symbol
            )
            
            # Cancel bids
            for bid in order_book["bids"]:
                if bid["account"] == self.account:
                    self.dex.cancel_order(
                        account=self.account,
                        order_id=bid['identifier'],
                        quote_symbol=self.quote_symbol,
                        base_symbol=self.base_symbol
                    )
            
            # Cancel offers
            for offer in order_book["offers"]:
                if offer["account"] == self.account:
                    self.dex.cancel_order(
                        account=self.account,
                        order_id=offer['identifier'],
                        quote_symbol=self.quote_symbol,
                        base_symbol=self.base_symbol
                    )
            
            return True
        except Exception as e:
            print(f"Error cancelling orders: {e}")
            return False

    def run(self) -> None:
        """
        Main strategy execution loop.
        """
        self.is_running = True
        print(f"🚀 Starting {self.__class__.__name__} for {self.base_symbol}/{self.quote_symbol}")
        
        try:
            while self.is_running:
                # Generate trading signal
                signal = self.generate_signal()
                
                # Cancel existing orders
                self.cancel_orders()
                
                # Place new orders
                self.place_orders(signal)
                
                # Wait for next iteration
                import time
                time.sleep(self.config.get('interval', 5))
                
        except KeyboardInterrupt:
            print("\n\n🛑 Strategy stopped by user")
        finally:
            self.cleanup()

    def cleanup(self) -> None:
        """
        Cleanup resources and cancel orders on shutdown.
        """
        print("🧹 Cleaning up...")
        self.cancel_orders()
        self.is_running = False 