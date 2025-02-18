- 
+ # Testing Libre Trading Strategies on macOS
+ 
+ This guide provides instructions for testing the Libre trading strategies on macOS using multiple accounts.
+ 
+ ## Prerequisites
+ 
+ - macOS
+ - Python 3.8+
+ - Git
+ - Multiple Libre accounts with API keys
+ 
+ ## Setup
+ 
+ ### 1. Clone the Repository (if you haven't already)
+ 
+ ```bash
+ git clone https://github.com/libre-org/pylibre.git
+ cd pylibre
+ ```
+ 
+ ### 2. Create a Virtual Environment
+ 
+ ```bash
+ python3 -m venv .venv
+ source .venv/bin/activate
+ pip install -r requirements.txt
+ ```
+ 
+ ### 3. Configure the Strategies
+ 
+ Edit your `config/strategies.yaml` file to use different accounts:
+ 
+ ```yaml
+ # API endpoint
+ api_endpoint: "https://testnet.libre.org"
+ 
+ # Trading pairs configuration
+ trading_pairs:
+   LIBREBTC:
+     market_maker:
+       num_orders: 30
+       min_spread_percentage: 0.01
+       max_spread_percentage: 0.15
+       quantity_distribution: "random"
+       update_interval_ms: 120000  # 2 minutes
+     
+     animator:
+       activity_level: "high"
+       orders_per_cycle: 5
+       cycle_interval_ms: 3000  # 3 seconds
+     
+     price_tracker:
+       source: "fixed"  # manually set price
+       update_interval_ms: 60000  # 1 minute
+       price_change_threshold: 0.01  # 1%
+       fallback_price: 0.0000002  # Default price for LIBRE/BTC
+       
+     simulator:
+       trade_frequency: "high"
+       trade_size_variation: "high"
+       price_range_percentage: 0.01
+       cycle_interval_ms: 15000
+       trades_per_cycle: 2
+       trade_pattern: "trend"
+       trend_direction: "up"
+       trend_strength: 0.7
+ 
+ # Account configuration
+ accounts:
+   # Using different accounts for different purposes
+   main: "bentester"       # Main account for market making
+   animator: "bentest3"    # Account for animation
+   tracker: "dextester"    # Account for price tracking
+   simulator_primary: "dextrader"    # Primary account for trade simulation
+   simulator_secondary: "bentester"  # Secondary account for trade simulation
+ ```
+ 
+ ## Testing Individual Strategies
+ 
+ Open a separate terminal window or tab for each strategy you want to run simultaneously.
+ 
+ ### 1. Test OrderBookMakerStrategy
+ 
+ This strategy creates a spread of orders around a center price.
+ 
+ ```bash
+ python scripts/run_orderbook_maker.py --account bentester --base LIBRE --quote BTC
+ ```
+ 
+ Additional options:
+ ```bash
+ # For LIBRE/BTC, use a wider spread range to ensure different price points
+ python scripts/run_orderbook_maker.py --account bentester --base LIBRE --quote BTC --min-spread 0.05 --max-spread 0.25 --orders 30 --distribution random
+ ```
+ 
+ **Note:** For LIBRE/BTC pairs, it's recommended to use a wider spread range (e.g., 5% to 25%) to ensure that orders are placed at different price points. This is because BTC prices for LIBRE are very small (around 0.0000002), and with a narrow spread, all prices might round to the same value.
+ 
+ ### 2. Test MarketPriceTrackerStrategy
+ 
+ This strategy monitors market prices and updates the center price for other strategies.
+ 
+ ```bash
+ python scripts/run_market_price_tracker.py --account dextester --base LIBRE --quote BTC
+ ```
+ 
+ For LIBRE/BTC, the strategy uses a fixed price of 0.00000001 BTC (1 SAT) per LIBRE by default. You can specify a different price:
+ 
+ ```bash
+ python scripts/run_market_price_tracker.py --account dextester --base LIBRE --quote BTC --fixed-price 0.0000002
+ ```
+ 
+ Additional options:
+ ```bash
+ python scripts/run_market_price_tracker.py --account dextester --base LIBRE --quote BTC --source fixed --interval 60000 --threshold 0.01
+ ```
+ 
+ ### 3. Test OrderBookAnimatorStrategy
+ 
+ This strategy creates the appearance of market activity by periodically canceling and replacing orders.
+ 
+ ```bash
+ python scripts/run_orderbook_animator.py --account bentest3 --base LIBRE --quote BTC
+ ```
+ 
+ Additional options:
+ ```bash
+ python scripts/run_orderbook_animator.py --account bentest3 --base LIBRE --quote BTC --activity high --orders 5 --interval 3000 --price-variation 0.005 --quantity-variation 0.15
+ ```
+ 
+ ### 4. Test TradeSimulatorStrategy
+ 
+ This strategy creates the appearance of trades being filled by simulating trades between accounts.
+ 
+ ```bash
+ python scripts/run_trade_simulator.py --account dextrader --base LIBRE --quote BTC --secondary-account bentester
+ ```
+ 
+ Additional options:
+ ```bash
+ python scripts/run_trade_simulator.py --account dextrader --base LIBRE --quote BTC --secondary-account bentester --frequency high --size-variation high --price-range 0.01 --interval 15000 --trades-per-cycle 2 --pattern trend --trend-direction up --trend-strength 0.7
+ ```
+ 
+ ## Testing the StrategyCoordinator
+ 
+ The StrategyCoordinator manages multiple strategies for a trading pair. It will use the account mappings from your config file.
+ 
+ ```bash
+ python scripts/run_strategy_coordinator.py --account bentester --base LIBRE --quote BTC
+ ```
+ 
+ With dashboard:
+ ```bash
+ python scripts/run_strategy_coordinator.py --account bentester --base LIBRE --quote BTC --dashboard --dashboard-port 5000
+ ```
+ 
+ ## Testing the Monitoring Dashboard
+ 
+ Run the dashboard in a separate terminal:
+ 
+ ```bash
+ python scripts/run_dashboard.py
+ ```
+ 
+ Then open your browser and navigate to `http://localhost:5000` to view the dashboard.
+ 
+ Additional options:
+ ```bash
+ python scripts/run_dashboard.py --host 0.0.0.0 --port 5000 --data-dir monitor_data
+ ```
+ 
+ ## Running Strategies in the Background
+ 
+ To run a strategy in the background on macOS:
+ 
+ ```bash
+ python scripts/run_strategy_coordinator.py --account bentester --base LIBRE --quote BTC &
+ ```
+ 
+ The `&` at the end runs the process in the background.
+ 
+ To bring it back to the foreground:
+ ```bash
+ fg
+ ```
+ 
+ To stop a background process:
+ ```bash
+ # First find the process ID
+ ps aux | grep python
+ # Then kill it
+ kill <process_id>
+ ```
+ 
+ ## Testing Multiple Trading Pairs
+ 
+ To test strategies for multiple trading pairs, run separate instances with different parameters:
+ 
+ ```bash
+ # For LIBRE/BTC
+ python scripts/run_strategy_coordinator.py --account bentester --base LIBRE --quote BTC
+ 
+ # For LIBRE/USDT
+ python scripts/run_strategy_coordinator.py --account bentester --base LIBRE --quote USDT
+ ```
+ 
+ ## Monitoring and Debugging
+ 
+ ### View Orders in the DEX
+ 
+ You can check the orders placed by each account on the Libre testnet DEX interface.
+ 
+ ### Check Logs
+ 
+ Each strategy outputs logs to the console. You can redirect these to files:
+ 
+ ```bash
+ python scripts/run_orderbook_maker.py --account bentester --base LIBRE --quote BTC > orderbook_maker.log 2>&1 &
+ ```
+ 
+ ### Dashboard Metrics
+ 
+ The dashboard provides real-time metrics for all running strategies, including:
+ - Strategy status
+ - Orders placed/filled/cancelled
+ - Performance metrics
+ - Historical data visualization
+ 
+ ## Stopping Strategies
+ 
+ To stop a strategy running in the foreground, press `Ctrl+C`.
+ 
+ To stop a strategy running in the background:
+ ```bash
+ # Find the process ID
+ ps aux | grep python
+ # Kill the process
+ kill <process_id>
+ ```
+ 
+ ## Troubleshooting
+ 
+ ### Common Issues and Solutions
+ 
+ 1. **API connection errors**:
+    - Verify API endpoint in your configuration
+    - Check your internet connection
+    - Ensure your API keys are valid
+ 
+ 2. **Order placement failures**:
+    - Check account balances
+    - Verify minimum order requirements
+    - Look for error messages in the logs
+ 
+ 3. **Dashboard not showing data**:
+    - Ensure strategies are running
+    - Check that the dashboard is running on the correct port
+    - Verify there are no firewall issues
+ 
+ ### Strategy-Specific Issues
+ 
+ #### Missing `place_orders` Method in OrderBookAnimatorStrategy
+ 
+ If you encounter an error like this when running the OrderBookAnimatorStrategy:
+ 
+ ```
+ TypeError: Can't instantiate abstract class OrderBookAnimatorStrategy with abstract method place_orders
+ ```
+ 
+ This is because the `OrderBookAnimatorStrategy` class is missing the required `place_orders` method from the `BaseStrategy` abstract class. The fix has been applied in the latest version, but if you're still seeing this error, you can add the method manually:
+ 
+ ```python
+ def place_orders(self, signal: Dict[str, Any]) -> bool:
+     """
+     Implementation of the abstract method from BaseStrategy.
+     
+     The OrderBookAnimatorStrategy doesn't place orders directly through this method.
+     Instead, it uses the animate_orderbook method to cancel and replace orders.
+     
+     Args:
+         signal: The trading signal (not used in this strategy)
+         
+     Returns:
+         bool: Always returns True as this method is not the primary way this strategy places orders
+     """
+     self.logger.debug("OrderBookAnimatorStrategy doesn't place orders through the place_orders method")
+     return True
+ ```
+ 
+ #### Type Error in OrderBookAnimatorStrategy
+ 
+ If you see errors like this when running the OrderBookAnimatorStrategy:
+ 
+ ```
+ Error creating replacement order: unsupported operand type(s) for *: 'decimal.Decimal' and 'float'
+ ```
+ 
+ This is because the strategy is trying to multiply a `Decimal` value with a `float` value. The fix is to ensure that the `price_variation_percentage` and `quantity_variation_percentage` parameters are converted to `Decimal` objects in the `__init__` method:
+ 
+ ```python
+ # Change these lines in src/pylibre/strategies/orderbookanimator.py
+ self.activity_factors = {
+     'low': {'price': '0.001', 'quantity': '0.05'},    # 0.1% price, 5% quantity
+     'medium': {'price': '0.003', 'quantity': '0.10'}, # 0.3% price, 10% quantity
+     'high': {'price': '0.005', 'quantity': '0.15'}    # 0.5% price, 15% quantity
+ }
+ 
+ # And these lines
+ if self.price_variation_percentage is None:
+     self.price_variation_percentage = Decimal(self.activity_factors[self.activity_level]['price'])
+ else:
+     self.price_variation_percentage = Decimal(str(self.price_variation_percentage))
+     
+ if self.quantity_variation_percentage is None:
+     self.quantity_variation_percentage = Decimal(self.activity_factors[self.activity_level]['quantity'])
+ else:
+     self.quantity_variation_percentage = Decimal(str(self.quantity_variation_percentage))
+ ```
+ 
+ This ensures that all calculations involving price and quantity variations use `Decimal` objects consistently, avoiding type errors.
+ 
+ #### Zero Quantity Orders in OrderBookAnimatorStrategy
+ 
+ If you see errors like this when running the OrderBookAnimatorStrategy:
+ 
+ ```
+ Transaction rejected by the blockchain
+ Failed to replace buy order: Unknown error
+ ```
+ 
+ And you notice that the orders are being placed with zero quantities:
+ 
+ ```
+ Placing buy order: 0.0000 LIBRE @ 0.0000001940 BTC
+ ```
+ 
+ This is because the strategy is not correctly parsing the base amount from the order or the base amount is missing. The fix is to ensure that a minimum quantity is used for orders, even if the parsed base amount is 0:
+ 
+ ```python
+ # Add these lines to the _create_replacement_order method in src/pylibre/strategies/orderbookanimator.py
+ # Set minimum quantities based on the trading pair
+ min_base_amount = Decimal('100.0000') if self.base_symbol == 'LIBRE' else Decimal('0.0001')
+
+ # And modify the quantity calculation logic
+ # If base_amount is 0 or very small, use the minimum amount
+ if base_amount < min_base_amount:
+     new_base_amount = min_base_amount
+ else:
+     quantity_variation = base_amount * self.quantity_variation_percentage
+     quantity_delta = Decimal(str(random.uniform(-float(quantity_variation), float(quantity_variation))))
+     new_base_amount = base_amount + quantity_delta
+
+ # Ensure quantity is positive and meets minimum requirements
+ new_base_amount = max(new_base_amount, min_base_amount)
+ ```
+ 
+ This ensures that orders are always placed with a valid quantity, preventing blockchain rejections.
+ 
+ #### Import Path Issues with TradeSimulatorStrategy
+ 
+ If you encounter import errors when running the TradeSimulatorStrategy, it might be due to inconsistent import paths. The fix is to update the import statements in `scripts/run_trade_simulator.py` from:
+ 
+ ```python
+ from src.pylibre import LibreClient
+ from src.pylibre.strategies import TradeSimulatorStrategy
+ from src.pylibre.utils.logger import StrategyLogger, LogLevel
+ ```
+ 
+ to:
+ 
+ ```python
+ from pylibre.client import LibreClient
+ from pylibre.strategies import TradeSimulatorStrategy
+ from pylibre.utils.logger import StrategyLogger, LogLevel
+ ```
+ 
+ Also, update the Python path setup:
+ 
+ ```python
+ # Add the src directory to the Python path
+ sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
+ ```
+ 
+ ## Getting Help
+ 
+ If you encounter issues not covered in this guide, please:
+ 1. Check the project's GitHub issues
+ 2. Join the Libre community Discord
+ 3. Contact the development team
+ 
+ ## Cancelling Orders
+ 
+ To cancel all orders for a specific account and trading pair, you can use the `cancel_orders.py` script:
+ 
+ ```bash
+ # Cancel orders using the pair format
+ ./scripts/cancel_orders.py --account bentest3 --pair LIBREBTC
+ 
+ # Or using the base/quote format
+ ./scripts/cancel_orders.py --account bentest3 --base LIBRE --quote BTC
+ ```
+ 
+ This script will cancel all orders for the specified account on the specified trading pair. It's useful for cleaning up after testing or when you want to start fresh.
+ 
+ ## Utility Scripts
+ 
+ The project includes several utility scripts to help with testing and monitoring:
+ 
+ ### Check Balances
+ 
+ To check the balances of an account:
+ 
+ ```bash
+ python scripts/check_balances.py --account bentester
+ ```
+ 
+ ### Check Orderbook
+ 
+ To check the current state of the orderbook for a trading pair:
+ 
+ ```bash
+ python scripts/check_orderbook.py --pair LIBREBTC
+ ```
+ 
+ ### Fetch Prices
+ 
+ To fetch prices from various sources:
+ 
+ ```bash
+ python scripts/fetch_prices.py --base LIBRE --quote BTC --source binance
+ ``` 