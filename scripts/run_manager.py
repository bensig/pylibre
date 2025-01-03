from pylibre.manager.strategy_manager import StrategyManager
import signal
import sys

def signal_handler(sig, frame):
    print("\nShutting down all strategies...")
    manager.stop_all()
    sys.exit(0)

if __name__ == "__main__":
    manager = StrategyManager()
    
    # Handle graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start all strategies
    manager.start_all()
    
    # Keep the main process running
    signal.pause() 