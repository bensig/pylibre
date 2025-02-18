#!/usr/bin/env python3
"""
Comprehensive end-to-end test script for pylibre.
Tests the entire flow from client to dex to strategies, with special focus on BTC sell orders.
"""

import sys
import os
import time
import logging
import yaml
import json
from decimal import Decimal, getcontext

# Set higher precision for decimal calculations
getcontext().prec = 28

# Add the parent directory to the path so we can import the pylibre module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from src.pylibre.client import LibreClient
from src.pylibre.dex import DexClient
from src.pylibre.strategies.marketpricetracker import MarketPriceTrackerStrategy
from src.pylibre.strategies.tradesimulator import TradeSimulatorStrategy
from src.pylibre.strategies import StrategyCoordinator
from src.pylibre.utils.logger import StrategyLogger, LogLevel

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("EndToEndTest")

def test_client_basic_operations():
    """Test basic client operations like balance checking and transfers."""
    print("\n" + "=" * 80)
    print("TESTING CLIENT BASIC OPERATIONS")
    print("=" * 80)
    
    client = LibreClient(verbose=True)
    
    # Define accounts to test
    from_account = "bentester"
    to_account = "bentest3"
    
    # Test tokens to check
    tokens = ["BTC", "USDT", "LIBRE"]
    
    # Check balances
    for token in tokens:
        print(f"\nChecking balance for {token}...")
        balance = client.get_balance(from_account, token)
        print(f"{from_account} has {balance} {token}")
    
    # Test a small transfer for each token
    for token in tokens:
        print(f"\nTesting small {token} transfer...")
        
        # Define amount based on token
        if token == "BTC":
            amount = "0.00001000"
        elif token == "USDT":
            amount = "0.00010000"
        else:  # LIBRE
            amount = "0.0001"
        
        # Get contract for token
        if token == "BTC":
            contract = "btc.libre"
        elif token == "USDT":
            contract = "usdt.libre"
        else:  # LIBRE
            contract = "eosio.token"
        
        # Execute transfer
        result = client.transfer(
            from_account=from_account,
            to_account=to_account,
            quantity=f"{amount} {token}",
            memo="End-to-end test transfer",
            contract=contract
        )
        
        if result.get("success"):
            print(f"✅ {token} transfer successful: {amount} {token} sent to {to_account}")
            print(f"Transaction ID: {result.get('data', {}).get('transaction_id')}")
        else:
            print(f"❌ {token} transfer failed: {result.get('error')}")
    
    return client

def test_dex_operations(client):
    """Test DEX operations like placing orders and fetching the orderbook."""
    print("\n" + "=" * 80)
    print("TESTING DEX OPERATIONS")
    print("=" * 80)
    
    dex = DexClient(client)
    
    # Define account to test
    account = "bentester"
    
    # Test fetching orderbook
    print("\nFetching BTC/USDT orderbook...")
    orderbook = dex.fetch_order_book(quote_symbol="USDT", base_symbol="BTC")
    
    if orderbook:
        print(f"Orderbook fetched successfully")
        print(f"Number of bids: {len(orderbook.get('bids', []))}")
        print(f"Number of offers: {len(orderbook.get('offers', []))}")
        
        # Print a few offers if available
        if orderbook.get('offers'):
            print("\nSample offers:")
            for offer in orderbook.get('offers', [])[:3]:
                print(f"  {offer.get('account')} selling {offer.get('quantity')} BTC at {offer.get('price')} USDT")
        
        # Print a few bids if available
        if orderbook.get('bids'):
            print("\nSample bids:")
            for bid in orderbook.get('bids', [])[:3]:
                print(f"  {bid.get('account')} buying {bid.get('quantity')} BTC at {bid.get('price')} USDT")
    else:
        print("Failed to fetch orderbook")
    
    # Test placing a small BTC buy order
    print("\nPlacing a small BTC buy order...")
    buy_result = dex.place_order(
        account=account,
        order_type="buy",
        quantity="0.00001000",
        price="80000.00000000",
        quote_symbol="USDT",
        base_symbol="BTC"
    )
    
    if buy_result:
        print(f"✅ BTC buy order placed successfully")
        print(f"Transaction ID: {buy_result}")
    else:
        print(f"❌ BTC buy order failed")
    
    # Wait a bit before placing the sell order
    time.sleep(2)
    
    # Test placing a small BTC sell order
    print("\nPlacing a small BTC sell order...")
    sell_result = dex.place_order(
        account=account,
        order_type="sell",
        quantity="0.00001000",
        price="85000.00000000",
        quote_symbol="USDT",
        base_symbol="BTC"
    )
    
    if sell_result:
        print(f"✅ BTC sell order placed successfully")
        print(f"Transaction ID: {sell_result}")
    else:
        print(f"❌ BTC sell order failed")
    
    return dex

def test_market_price_tracker(client, dex):
    """Test the MarketPriceTrackerStrategy."""
    print("\n" + "=" * 80)
    print("TESTING MARKET PRICE TRACKER STRATEGY")
    print("=" * 80)
    
    # Create a strategy logger
    strategy_logger = StrategyLogger("MarketPriceTrackerTest", log_level=LogLevel.INFO)
    
    # Create strategy configuration
    config = {
        'update_interval_ms': 5000,
        'price_source_config': {
            'source': 'binance',
            'symbol': 'BTCUSDT'
        }
    }
    
    # Create and initialize the strategy
    print("\nInitializing MarketPriceTrackerStrategy...")
    strategy = MarketPriceTrackerStrategy(
        client=client,
        dex=dex,
        logger=strategy_logger,
        config=config
    )
    
    # Start the strategy (non-blocking)
    print("Starting MarketPriceTrackerStrategy...")
    strategy.start()
    
    # Let it run for a few seconds
    print("Running for 10 seconds...")
    for i in range(10):
        time.sleep(1)
        print(f"Current price: {strategy.current_price}")
    
    # Stop the strategy
    print("Stopping MarketPriceTrackerStrategy...")
    strategy.stop()
    
    return strategy

def test_trade_simulator(client, dex, market_price_tracker):
    """Test the TradeSimulatorStrategy."""
    print("\n" + "=" * 80)
    print("TESTING TRADE SIMULATOR STRATEGY")
    print("=" * 80)
    
    # Create a strategy logger
    strategy_logger = StrategyLogger("TradeSimulatorTest", log_level=LogLevel.INFO)
    
    # Create strategy configuration
    config = {
        'account': 'bentester',
        'base_symbol': 'BTC',
        'quote_symbol': 'USDT',
        'update_interval_ms': 5000,
        'min_order_value_usd': 0.1,
        'max_order_value_usd': 1.0,
        'price_deviation_pct': 0.5,
        'trade_frequency_ms': 10000,
        'price_source': market_price_tracker
    }
    
    # Create and initialize the strategy
    print("\nInitializing TradeSimulatorStrategy...")
    strategy = TradeSimulatorStrategy(
        client=client,
        dex=dex,
        logger=strategy_logger,
        config=config
    )
    
    # Start the strategy (non-blocking)
    print("Starting TradeSimulatorStrategy...")
    strategy.start()
    
    # Let it run for a short time to place a few orders
    print("Running for 30 seconds to place a few orders...")
    for i in range(30):
        time.sleep(1)
        print(f"Running second {i+1}/30...")
    
    # Stop the strategy
    print("Stopping TradeSimulatorStrategy...")
    strategy.stop()
    
    return strategy

def test_strategy_coordinator(client, dex):
    """Test the StrategyCoordinator with both strategies."""
    print("\n" + "=" * 80)
    print("TESTING STRATEGY COORDINATOR")
    print("=" * 80)
    
    # Load strategies from config file
    try:
        with open('config/strategies.yaml', 'r') as f:
            strategies_config = yaml.safe_load(f)
            print(f"Loaded strategies config from file: {len(strategies_config)} strategies defined")
    except Exception as e:
        print(f"Error loading strategies config: {e}")
        strategies_config = {}
    
    # Create a coordinator configuration
    coordinator_config = {
        'account': 'bentester',
        'base_symbol': 'BTC',
        'quote_symbol': 'USDT',
        'update_interval_ms': 5000,
        'strategies': strategies_config
    }
    
    # Create and initialize the coordinator
    print("\nInitializing StrategyCoordinator...")
    coordinator = StrategyCoordinator(
        client=client,
        dex=dex,
        config=coordinator_config
    )
    
    # Start the coordinator (non-blocking)
    print("Starting StrategyCoordinator...")
    coordinator.start()
    
    # Let it run for a short time
    print("Running for 30 seconds...")
    for i in range(30):
        time.sleep(1)
        print(f"Running second {i+1}/30...")
        
        # Print status every 5 seconds
        if i % 5 == 0:
            status = coordinator.get_status()
            print(f"\nCoordinator Status:")
            print(f"  Running: {status.get('running', False)}")
            print(f"  Active Strategies: {len(status.get('strategies', []))}")
            
            # Print status of each strategy
            for strategy_status in status.get('strategies', []):
                print(f"  - {strategy_status.get('name', 'Unknown')}: {strategy_status.get('status', 'Unknown')}")
    
    # Stop the coordinator
    print("Stopping StrategyCoordinator...")
    coordinator.stop()
    
    return coordinator

def main():
    """Run the end-to-end test."""
    print("\n" + "=" * 80)
    print("COMPREHENSIVE END-TO-END TEST")
    print("=" * 80 + "\n")
    
    try:
        # Test client operations
        client = test_client_basic_operations()
        
        # Test DEX operations
        dex = test_dex_operations(client)
        
        # Test MarketPriceTrackerStrategy
        market_price_tracker = test_market_price_tracker(client, dex)
        
        # Test TradeSimulatorStrategy
        trade_simulator = test_trade_simulator(client, dex, market_price_tracker)
        
        # Test StrategyCoordinator
        coordinator = test_strategy_coordinator(client, dex)
        
        print("\n" + "=" * 80)
        print("END-TO-END TEST COMPLETED SUCCESSFULLY")
        print("=" * 80 + "\n")
        
        return 0
    except Exception as e:
        logger.error(f"Error in end-to-end test: {str(e)}", exc_info=True)
        print(f"\n❌ END-TO-END TEST FAILED: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
