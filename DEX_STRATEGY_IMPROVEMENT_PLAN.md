# DEX Strategy System Improvement Plan

## Current Issues

1. **Price Alignment Problem**: Large discrepancy between Binance price (~$84,782) and DEX market price (~$80,777)
2. **Order Excess**: 449 orders when max should be 40
3. **Monitoring vs. Strategy Coordination**: The monitor script is compensating for failures in the primary strategies
4. **Oracle Integration Issues**: Oracle price checking isn't working correctly
5. **Inconsistent Library Usage**: Scripts aren't fully utilizing the pylibre library functions

## Root Causes

1. **Strategy Coordination Failures**: The primary strategies aren't properly managing order cancellation
2. **Market Pressure**: There may be significant sell pressure pushing the price down on Libre
3. **Order Book Management**: Orders aren't being effectively cleared when they become irrelevant
4. **System Architecture**: Separate monitoring and strategy processes aren't coordinated
5. **Library Integration**: Some scripts use direct API calls instead of leveraging existing pylibre functions

## Short-term Solutions

1. **Fix Monitor Script Oracle Integration**
   - Fix the `get_table_rows()` API call by removing `json=True` parameter
   - Ensure proper error handling for oracle data retrieval
   - Add fallback mechanisms when oracle data is unavailable
   - Standardize on pylibre library methods for all blockchain interactions

2. **Improve Order Cleanup**
   - Enhance batch processing with proper error handling
   - Add order book refreshing to avoid attempting to cancel non-existent orders
   - Prioritize orders furthest from current market price for cancellation
   - Implement rate limiting to avoid transaction rejections
   - Use DexClient methods consistently for all order operations

3. **Adjust Order Limits**
   - Consider temporarily reducing `num_orders` to 30 or even 20 to make management easier
   - Balance order distribution evenly between bid and ask sides
   - Tighten spread parameters to keep orders closer to market price

4. **Prevent Excess Order Creation**
   - Implement order creation rate limiting
   - Add minimum order spacing to avoid duplicate price levels
   - Disable unnecessary strategy components
   - Increase update intervals to reduce creation frequency
   - Add order throttling between placements

## Medium-term Solutions

1. **Consolidate Monitoring and Strategy Execution**
   - Integrate the monitoring logic directly into the strategy coordinator
   - Add periodic health checks within the coordinator to detect and fix issues
   - Implement automatic strategy rebalancing based on market conditions
   - Create a unified logging system for better diagnostics
   - Leverage pylibre's existing StrategyCoordinator framework

2. **Improve Price Alignment Mechanism**
   - Use chainlink oracle as the primary price reference via pylibre's data retrieval methods
   - Implement weighted price calculation (oracle + binance + existing orders)
   - Add dynamic spread adjustment based on market volatility
   - Implement circuit breakers for extreme market conditions

3. **Enhanced Error Recovery**
   - Add transaction retry mechanisms with exponential backoff
   - Implement circuit breakers for extreme market conditions
   - Create automatic failover for API connection issues
   - Add monitoring for blockchain congestion and adjust accordingly
   - Utilize pylibre's error handling mechanisms consistently

## Long-term Strategy Redesign

1. **Unified Strategy Framework**
   - Create a single coordinator that manages all strategies
   - Implement priority-based execution where cleanup and price alignment take precedence
   - Add logging/telemetry for better monitoring and analysis
   - Design pluggable strategy components for easier maintenance
   - Build on top of the existing pylibre strategy framework

2. **Smart Order Management**
   - Implement order aging and lifecycle management
   - Use dynamic order sizing based on market conditions
   - Add intelligent order placement that avoids creating excess orders
   - Develop order batching to reduce transaction costs
   - Extend the DexClient with advanced order management capabilities

3. **Market Adaptive Behavior**
   - Develop strategies that adapt to changing market conditions
   - Monitor price impact and adjust strategy accordingly
   - Implement machine learning for pattern recognition and strategy optimization
   - Add support for multiple price feeds and fallback mechanisms

## Core pylibre Components to Utilize

1. **LibreClient (`src/pylibre/client.py`)**
   - `get_table_rows()` for retrieving blockchain data
   - `get_table()` for paginated data retrieval
   - `get_currency_balance()` for checking account balances
   - `push_action()` for executing blockchain actions
   - Error handling and formatting logic

2. **DexClient (`src/pylibre/dex.py`)**
   - `fetch_order_book()` for retrieving order book data
   - `place_order()` for creating new orders
   - `cancel_order()` for removing existing orders
   - Order data parsing and formatting functions

3. **Strategy Framework (`src/pylibre/strategies`)**
   - `StrategyCoordinator` for managing multiple strategies
   - Individual strategy classes for specific behaviors
   - Monitoring and reporting mechanisms
   - Strategy lifecycle management

4. **CLI Utilities (`src/pylibre/cli.py`)**
   - Command formatting and parsing patterns
   - Interactive components
   - Configuration handling

## Implementation Timeline

### Phase 1: Immediate Fixes (1-2 days)
- Fix oracle price fetching in monitor script
- Adjust cleanup parameters for more efficient order cancellation
- Temporarily reduce order count limits
- Implement basic rate limiting for transaction submissions
- Standardize on pylibre methods for all blockchain interactions

### Phase 2: Monitoring Enhancement (3-5 days)
- Extend the monitor script to provide better analytics
- Add automatic notifications for large price deviations
- Implement smarter order cleanup logic
- Create basic dashboard for system status
- Build monitoring extensions for the pylibre framework

### Phase 3: Strategy Coordination (1-2 weeks)
- Integrate monitoring directly into the strategy coordinator
- Add automatic rebalancing of the order book
- Implement priority-based strategy execution
- Develop better error handling and recovery mechanisms
- Extend the StrategyCoordinator with health checks

### Phase 4: Complete System Redesign (2-4 weeks)
- Create a new unified strategy framework
- Implement intelligent order management
- Develop adaptive market behavior
- Add comprehensive testing framework
- Build advanced extensions to the pylibre library

## Implementation Checklist

### Phase 1: Immediate Fixes
- [x] Fix `get_table_rows()` API call in monitor script (removing `json=True` parameter)
- [x] Add error handling for oracle data retrieval with fallback to Binance
- [x] Add periodic order book refresh during cleanup to avoid trying to cancel non-existent orders
- [x] Implement exponential backoff for transaction retry logic
- [x] Update the batch size and delay parameters for order cancellation
- [x] Adjust `num_orders` parameter in `strategies.mainnet.yaml` to a more manageable number
- [x] Ensure order distribution is balanced between bid and ask sides
- [x] Add order prioritization based on distance from market price (cancel furthest first)
- [x] Update prioritization to use Chainlink oracle price instead of DEX mid-market price
- [x] Implement smart market-alignment logic to prioritize orders that will help move DEX price toward oracle price
- [x] Implement advanced price-gap based order book analysis with dynamic bid/ask cancellation ratio
- [x] Update monitor script to use `DexClient.fetch_order_book()` consistently
- [x] Add proper exception handling for all API calls
- [x] Test fixed monitor script with real-time monitoring
- [x] Create launch scripts to run coordinator and monitor in separate screen sessions
- [x] Create status check script to monitor both services
- [x] Implement smaller batch sizes for transaction processing (3 orders per batch)
- [x] Increase delay between transaction batches to reduce rejections
- [x] Optimize the fast cancellation method to handle large order counts reliably
- [x] Create dedicated oracle-aligned orderbook manager script to maintain exactly 15 bids and 15 asks

### Phase 1.5: Order Creation Prevention
- [x] Disable unnecessary simulator strategy components
- [x] Increase update intervals to reduce order creation frequency
- [x] Add order creation rate limiting parameters (max_orders_per_update)
- [x] Implement minimum order spacing to prevent duplicates
- [x] Add order creation throttling parameters
- [x] Further reduce animator activity levels
- [x] Consolidate configuration in strategy_groups section
- [x] Add order age limits to automatically cancel old orders
- [x] Implement intelligent price level selection to reuse existing levels
- [x] Add order placement validation to reject orders too close to existing ones
- [ ] Implement global rate limiting across all strategies

### Phase 2: Monitoring Enhancements
- [x] Extend monitor script with detailed analytics reporting
- [ ] Create a simple dashboard for real-time system status
- [x] Implement more aggressive cleanup for orders far from market price
- [ ] Add automated email/chat notifications for large price deviations
- [ ] Create a history log of strategy performance for trend analysis
- [ ] Add blockchain congestion detection and adaptive retry logic
- [ ] Build monitoring extensions as a reusable component
- [ ] Create a standardized logging format for all strategy components
- [ ] Implement system health metrics collection
- [ ] Add automated testing framework for monitoring components

### Phase 3: Strategy Coordination
- [ ] Integrate monitoring functionality into the strategy coordinator
- [ ] Implement periodic health checks within the coordinator
- [x] Add automatic rebalancing of order book based on market conditions
- [ ] Develop priority-based strategy execution framework
- [ ] Create comprehensive error recovery system with fallbacks
- [ ] Extend StrategyCoordinator with configurable health checks
- [ ] Implement dynamic strategy parameter adjustment based on market conditions
- [ ] Create a unified configuration system for all strategies
- [ ] Add circuit breakers for extreme market conditions
- [ ] Develop comprehensive system documentation

### Phase 4: System Redesign
- [ ] Design new unified strategy framework architecture
- [ ] Implement order lifecycle management system
- [ ] Develop dynamic order sizing based on market conditions
- [ ] Create intelligent order placement algorithm to minimize excess orders
- [ ] Build weighted price calculation system (oracle + binance + market)
- [ ] Implement market condition detection and adaptation system
- [ ] Add comprehensive testing framework for all components
- [ ] Build advanced extensions to the pylibre library
- [ ] Develop system performance monitoring and analytics
- [ ] Create detailed documentation and operation runbooks

## Progress Tracking

| Date       | Milestone                                        | Status      | Notes                                    |
|------------|--------------------------------------------------|-------------|-----------------------------------------|
| 2025-04-11 | Fix `get_table_rows()` in monitor script         | Completed   | Removed `json=True` parameter           |
| 2025-04-11 | Update cleanup parameters                        | Completed   | Reduced batch size, increased delays     |
| 2025-04-11 | Document improvement plan                        | Completed   | Created comprehensive strategy document  |
| 2025-04-11 | Add error handling for oracle price retrieval    | Completed   | Added fallback to Binance with logging  |
| 2025-04-11 | Add order book refresh during cleanup           | Completed   | Added refresh every 20 orders + batch start |
| 2025-04-11 | Prioritize orders by distance from market        | Completed   | Orders furthest from market cancelled first |
| 2025-04-11 | Implement exponential backoff for retries        | Completed   | Added increasing delays between retries |
| 2025-04-11 | Adjust `num_orders` in configuration             | Completed   | Reduced from 40 to 20 in BTCUSDT config |
| 2025-04-11 | Update the batch size and delay parameters       | Completed   | Set batch size to 5, delay to 1000ms    |
| 2025-04-12 | Implement smart market-alignment logic           | Completed   | Added price-gap based cancellation      |
| 2025-04-12 | Optimize fast cancellation logic                 | Completed   | Added robust batching and error handling |
| 2025-04-12 | Create service management scripts                | Completed   | Added start_coordinator.sh and check_strategy_status.sh |
| 2025-04-12 | Prevent excess order creation                    | Completed   | Updated config with rate limiting and spacing |
| 2025-04-12 | Configure strategy_groups for monitoring         | Completed   | Added consolidated parameters           |
| 2025-04-12 | Implement order age limits                       | Completed   | Orders older than configured hours are auto-cancelled |
| 2025-04-13 | Create oracle-aligned orderbook manager          | Completed   | New script that maintains exactly 15 bids and 15 asks |
|            | Create price animator for UI activity            | In Progress | Implementing small price movements for UI |
|            | Standardize on pylibre API methods               | In Progress | Converting direct API calls to library calls |

## Next Steps

1. Create a complementary animator script that works alongside the oracle-aligned orderbook manager
2. Create a basic dashboard for real-time system status monitoring
3. Add automatic notifications for large price deviations
4. Integrate the monitoring functionality directly into the strategy coordinator
5. Begin the redesign of the core strategy framework

## Success Metrics

1. **Price Alignment**: DEX price within 0.5% of oracle/Binance price
2. **Order Management**: Total orders consistently at or below configured limits
3. **Spread Control**: Maintain target spread within configured parameters
4. **System Stability**: Zero unexpected downtime or failed transactions
5. **Market Activity**: Consistent trading volume and order book depth
6. **Code Quality**: 100% utilization of pylibre library functions for blockchain interactions 