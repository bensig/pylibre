import threading
import time
import logging
import os
from typing import Dict, Any, List, Optional, Callable
from decimal import Decimal

from pylibre.client import LibreClient
from pylibre.utils.logger import StrategyLogger, LogLevel
from pylibre.monitoring import get_monitor
from .orderbookmaker import OrderBookMakerStrategy
from .marketpricetracker import MarketPriceTrackerStrategy
from .orderbookanimator import OrderBookAnimatorStrategy
from .templates.base_strategy import BaseStrategy
from .tradesimulator import TradeSimulatorStrategy

class StrategyCoordinator:
    """
    Coordinates multiple strategies to work together for a trading pair.
    Manages timing and interactions between strategies.
    """
    
    def __init__(self, client: LibreClient, config: Dict[str, Any], logger=None):
        """Initialize the coordinator with configuration."""
        self.client = client
        self.config = config
        self.logger = logger or logging.getLogger("StrategyCoordinator")
        
        # Extract trading pair info
        self.account = config.get('account')
        self.base_symbol = config.get('base_symbol')
        self.quote_symbol = config.get('quote_symbol')
        
        # Validate required configuration
        if not all([self.account, self.base_symbol, self.quote_symbol]):
            raise ValueError("Missing required configuration: account, base_symbol, quote_symbol")
            
        self.trading_pair = f"{self.base_symbol}/{self.quote_symbol}"
        
        # Initialize strategies
        self.strategies = {}
        self.strategy_threads = {}
        self.strategy_statuses = {}
        self.running = False
        self.start_time = None
        
        # Get the monitor for metrics tracking
        self.monitor = get_monitor()
        
        # Log initialization
        self.logger.info(f"Initialized StrategyCoordinator for {self.trading_pair}")
        self.logger.info(f"  Account: {self.account}")
        self.logger.info(f"  Base Symbol: {self.base_symbol}")
        self.logger.info(f"  Quote Symbol: {self.quote_symbol}")
        self.logger.info(f"  Configuration: {self.config.get('description', 'No description provided')}")
        
    def _create_strategy(self, strategy_type: str, parameters: Dict[str, Any]) -> Optional[BaseStrategy]:
        """Create a strategy instance based on type."""
        try:
            # Generate a unique strategy ID
            strategy_id = f"{strategy_type}_{self.account}_{self.base_symbol}_{self.quote_symbol}"
            
            # Log strategy creation attempt with parameters
            self.logger.info(f"Creating {strategy_type} for {self.trading_pair}")
            self.logger.info(f"  Strategy ID: {strategy_id}")
            self.logger.info(f"  Parameters: {parameters}")
            
            # Register with monitor before creating
            self.monitor.register_strategy(
                strategy_id=strategy_id,
                strategy_type=strategy_type,
                trading_pair=self.trading_pair,
                account=self.account,
                parameters=parameters
            )
            
            # Initialize strategy based on type
            strategy = None
            if strategy_type == 'MarketPriceTrackerStrategy':
                self.logger.info(f"Initializing MarketPriceTrackerStrategy with price source: {parameters.get('price_source', 'default')}")
                strategy = MarketPriceTrackerStrategy(
                    client=self.client,
                    account=self.account,
                    base_symbol=self.base_symbol,
                    quote_symbol=self.quote_symbol,
                    parameters=parameters
                )
            elif strategy_type == 'OrderBookMakerStrategy':
                self.logger.info(f"Initializing OrderBookMakerStrategy with order count: {parameters.get('order_count', 'default')}")
                strategy = OrderBookMakerStrategy(
                    client=self.client,
                    account=self.account,
                    base_symbol=self.base_symbol,
                    quote_symbol=self.quote_symbol,
                    parameters=parameters
                )
            elif strategy_type == 'OrderBookAnimatorStrategy':
                self.logger.info(f"Initializing OrderBookAnimatorStrategy with animation frequency: {parameters.get('animation_frequency', 'default')}")
                strategy = OrderBookAnimatorStrategy(
                    client=self.client,
                    account=self.account,
                    base_symbol=self.base_symbol,
                    quote_symbol=self.quote_symbol,
                    parameters=parameters
                )
            elif strategy_type == 'TradeSimulatorStrategy':
                self.logger.info(f"Initializing TradeSimulatorStrategy with trades per cycle: {parameters.get('trades_per_cycle', 'default')}")
                strategy = TradeSimulatorStrategy(
                    client=self.client,
                    account=self.account,
                    base_symbol=self.base_symbol,
                    quote_symbol=self.quote_symbol,
                    parameters=parameters
                )
            else:
                self.logger.error(f"Unknown strategy type: {strategy_type}")
                return None
                
            # Log successful creation
            if strategy:
                self.logger.info(f"Successfully created {strategy_type}")
                # Store initial status
                self.strategy_statuses[strategy_type] = {
                    "status": "initialized",
                    "last_update": time.time(),
                    "cycles_completed": 0,
                    "errors": 0
                }
                
            return strategy
        except Exception as e:
            self.logger.error(f"Error creating strategy {strategy_type}: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return None
            
    def add_strategy(self, strategy_type: str, parameters: Dict[str, Any]) -> bool:
        """Add a strategy to the coordinator."""
        if strategy_type in self.strategies:
            self.logger.warning(f"Strategy {strategy_type} already exists")
            return False
            
        strategy = self._create_strategy(strategy_type, parameters)
        if not strategy:
            return False
        
        self.strategies[strategy_type] = strategy
        self.logger.info(f"Added {strategy_type} to coordinator")
        
        # Update monitor with strategy status
        strategy_id = f"{strategy_type}_{self.account}_{self.base_symbol}_{self.quote_symbol}"
        self.monitor.update_strategy_status(strategy_id, "initialized")
        
        return True
        
    def remove_strategy(self, strategy_type: str) -> bool:
        """Remove a strategy from the coordinator."""
        if strategy_type not in self.strategies:
            self.logger.warning(f"Strategy {strategy_type} does not exist")
            return False
            
        # Stop the strategy if it's running
        if strategy_type in self.strategy_threads and self.strategy_threads[strategy_type].is_alive():
            self.strategies[strategy_type].running = False
            self.strategy_threads[strategy_type].join(timeout=5)
            
            if self.strategy_threads[strategy_type].is_alive():
                self.logger.warning(f"Strategy {strategy_type} did not stop gracefully")
        
        # Clean up the strategy
        try:
            self.strategies[strategy_type].cleanup()
        except Exception as e:
            self.logger.error(f"Error cleaning up strategy {strategy_type}: {e}")
        
        # Remove from containers
        del self.strategies[strategy_type]
        if strategy_type in self.strategy_threads:
            del self.strategy_threads[strategy_type]
        
        # Update monitor with strategy status
        strategy_id = f"{strategy_type}_{self.account}_{self.base_symbol}_{self.quote_symbol}"
        self.monitor.update_strategy_status(strategy_id, "removed")
        
        self.logger.info(f"Removed {strategy_type} from coordinator")
        return True
        
    def _run_strategy(self, strategy_type: str):
        """Run a strategy in a separate thread."""
        if strategy_type not in self.strategies:
            self.logger.error(f"Strategy {strategy_type} does not exist")
            return
            
        strategy = self.strategies[strategy_type]
        strategy_id = f"{strategy_type}_{self.account}_{self.base_symbol}_{self.quote_symbol}"
        
        try:
            # Update monitor with strategy status
            self.monitor.update_strategy_status(strategy_id, "running")
            
            # Update internal status
            if strategy_type in self.strategy_statuses:
                self.strategy_statuses[strategy_type]["status"] = "running"
                self.strategy_statuses[strategy_type]["last_update"] = time.time()
            
            # Initialize metrics
            cycle_count = 0
            error_count = 0
            last_status_print = time.time()
            start_time = time.time()
            
            self.logger.info(f"Strategy {strategy_type} started execution loop")
            
            # Run the strategy
            while strategy.running and self.running:
                # Measure cycle time
                cycle_start = time.time()
                
                try:
                    # Execute strategy cycle
                    if hasattr(strategy, 'simulate_trades') and callable(getattr(strategy, 'simulate_trades')):
                        # For TradeSimulatorStrategy
                        trades_executed = strategy.simulate_trades()
                        
                        # Update metrics
                        self.monitor.update_strategy_metrics(strategy_id, {
                            "cycle_count": cycle_count,
                            "last_cycle_duration_ms": int((time.time() - cycle_start) * 1000),
                            "history_update": {
                                "orders_filled": trades_executed
                            }
                        })
                        
                        # Log progress periodically
                        if trades_executed > 0:
                            self.logger.info(f"{strategy_type}: Executed {trades_executed} trades in cycle {cycle_count}")
                        
                    elif hasattr(strategy, 'animate_orderbook') and callable(getattr(strategy, 'animate_orderbook')):
                        # For OrderBookAnimatorStrategy
                        orders_updated = strategy.animate_orderbook()
                        
                        # Update metrics
                        self.monitor.update_strategy_metrics(strategy_id, {
                            "cycle_count": cycle_count,
                            "orders_placed": orders_updated,
                            "last_cycle_duration_ms": int((time.time() - cycle_start) * 1000),
                            "history_update": {
                                "orders_placed": orders_updated
                            }
                        })
                        
                        # Log progress periodically
                        if orders_updated is not None and orders_updated > 0:
                            self.logger.info(f"{strategy_type}: Updated {orders_updated} orders in cycle {cycle_count}")
                        
                    else:
                        # For other strategies
                        signal = strategy.generate_signal()
                        if signal:
                            orders_placed = strategy.place_orders(signal)
                            
                            # Update metrics
                            self.monitor.update_strategy_metrics(strategy_id, {
                                "cycle_count": cycle_count,
                                "orders_placed": orders_placed,
                                "last_cycle_duration_ms": int((time.time() - cycle_start) * 1000),
                                "history_update": {
                                    "orders_placed": 1 if orders_placed else 0
                                }
                            })
                            
                            # Log progress
                            if orders_placed:
                                self.logger.info(f"{strategy_type}: Placed orders based on signal in cycle {cycle_count}")
                    
                    # Update internal status
                    if strategy_type in self.strategy_statuses:
                        self.strategy_statuses[strategy_type]["cycles_completed"] = cycle_count
                        self.strategy_statuses[strategy_type]["last_update"] = time.time()
                    
                except Exception as e:
                    error_count += 1
                    self.logger.error(f"Error in {strategy_type} cycle {cycle_count}: {e}")
                    import traceback
                    self.logger.error(f"Traceback: {traceback.format_exc()}")
                    
                    # Update error count in status
                    if strategy_type in self.strategy_statuses:
                        self.strategy_statuses[strategy_type]["errors"] = error_count
                    
                    # If too many consecutive errors, break
                    if error_count >= 5:
                        self.logger.error(f"Too many errors in {strategy_type}, stopping strategy")
                        break
                
                # Increment cycle count
                cycle_count += 1
                
                # Calculate average cycle duration
                avg_duration = int(((time.time() - start_time) * 1000) / max(1, cycle_count))
                self.monitor.update_strategy_metrics(strategy_id, {
                    "avg_cycle_duration_ms": avg_duration
                })
                
                # Print status summary periodically (every 5 minutes)
                if time.time() - last_status_print > 300:  # 5 minutes
                    self.logger.info(f"{strategy_type} status: {cycle_count} cycles completed, {error_count} errors")
                    last_status_print = time.time()
                
                # Wait for next cycle using strategy's update interval
                interval_ms = strategy.parameters.get('update_interval_ms', 1000)
                time.sleep(interval_ms / 1000)
                
        except Exception as e:
            self.logger.error(f"Fatal error running strategy {strategy_type}: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            # Update monitor with error status
            self.monitor.update_strategy_status(strategy_id, "error")
            
            # Update internal status
            if strategy_type in self.strategy_statuses:
                self.strategy_statuses[strategy_type]["status"] = "error"
                self.strategy_statuses[strategy_type]["last_update"] = time.time()
                self.strategy_statuses[strategy_type]["errors"] += 1
        finally:
            # Update monitor with stopped status
            self.monitor.update_strategy_status(strategy_id, "stopped")
            
            # Update internal status
            if strategy_type in self.strategy_statuses:
                self.strategy_statuses[strategy_type]["status"] = "stopped"
                self.strategy_statuses[strategy_type]["last_update"] = time.time()
                
            self.logger.info(f"Strategy {strategy_type} execution loop ended after {cycle_count} cycles")
            
    def _setup_price_tracker_callbacks(self):
        """Set up callbacks for price updates from the price tracker."""
        if 'MarketPriceTrackerStrategy' not in self.strategies:
            self.logger.warning("No MarketPriceTrackerStrategy found for price update callbacks")
            return
            
        price_tracker = self.strategies['MarketPriceTrackerStrategy']
        
        # Register callbacks for other strategies
        for strategy_type, strategy in self.strategies.items():
            if strategy_type != 'MarketPriceTrackerStrategy' and hasattr(strategy, 'on_price_update'):
                self.logger.info(f"Registering price update callback for {strategy_type}")
                price_tracker.register_price_update_callback(strategy.on_price_update)
                    
    def start(self):
        """Start all strategies."""
        if self.running:
            self.logger.warning("Coordinator is already running")
            return
        
        try:    
            self.running = True
            self.start_time = time.time()
            self.logger.info(f"Starting StrategyCoordinator for {self.trading_pair}")
            self.logger.info(f"Active strategies: {list(self.strategies.keys())}")
            
            # Verify that all required strategies exist
            missing_strategies = []
            if 'MarketPriceTrackerStrategy' not in self.strategies and self.base_symbol != 'LIBRE':
                missing_strategies.append('MarketPriceTrackerStrategy')
                self.logger.warning(f"MarketPriceTrackerStrategy is recommended for {self.trading_pair}")
            
            if missing_strategies:
                self.logger.warning(f"Missing recommended strategies: {', '.join(missing_strategies)}")
            
            # Set up price tracker callbacks
            self._setup_price_tracker_callbacks()
            
            # Start each strategy in its own thread
            started_strategies = 0
            for strategy_type, strategy in self.strategies.items():
                self.logger.info(f"Starting {strategy_type} for {self.trading_pair}")
                
                # Reset the running flag
                strategy.running = True
                
                # Update status
                self.strategy_statuses[strategy_type] = {
                    "status": "starting",
                    "last_update": time.time(),
                    "cycles_completed": 0,
                    "errors": 0,
                    "start_time": time.time()
                }
                
                # Create and start thread
                thread = threading.Thread(
                    target=self._run_strategy,
                    args=(strategy_type,),
                    name=f"{strategy_type}Thread"
                )
                thread.daemon = True
                thread.start()
                
                self.strategy_threads[strategy_type] = thread
                started_strategies += 1
                
                # Small delay between starting strategies to avoid resource contention
                time.sleep(0.5)
                
                # Verify thread started successfully
                if not thread.is_alive():
                    self.logger.error(f"Failed to start {strategy_type} thread")
                    self.strategy_statuses[strategy_type]["status"] = "failed"
                    self.strategy_statuses[strategy_type]["errors"] += 1
                else:
                    self.logger.info(f"Successfully started {strategy_type} thread")
            
            if started_strategies == 0:
                self.logger.warning(f"No strategies were started for {self.trading_pair}")
            else:
                self.logger.info(f"Started {started_strategies} strategies for {self.trading_pair}")
                
            # Print summary of started strategies
            self._print_status_summary()
            
            # Start the status monitor
            self.start_status_monitor(interval_seconds=300)  # Status updates every 5 minutes
            
        except Exception as e:
            self.logger.error(f"Error starting coordinator: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            self.running = False
        
    def stop(self):
        """Stop all strategies."""
        if not self.running:
            self.logger.warning("Coordinator is not running")
            return
        
        try:    
            self.running = False
            self.logger.info(f"Stopping StrategyCoordinator for {self.trading_pair}")
            
            # Calculate runtime
            if self.start_time:
                runtime_seconds = time.time() - self.start_time
                hours, remainder = divmod(runtime_seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                self.logger.info(f"Total runtime: {int(hours)}h {int(minutes)}m {int(seconds)}s")
            
            # Stop each strategy
            for strategy_type, strategy in self.strategies.items():
                self.logger.info(f"Stopping {strategy_type}")
                strategy.running = False
                
                # Update status
                if strategy_type in self.strategy_statuses:
                    self.strategy_statuses[strategy_type]["status"] = "stopping"
                    self.strategy_statuses[strategy_type]["last_update"] = time.time()
            
            # Wait for threads to finish
            stopped_count = 0
            for strategy_type, thread in self.strategy_threads.items():
                if thread.is_alive():
                    self.logger.info(f"Waiting for {strategy_type} to stop...")
                    thread.join(timeout=10)
                    
                    if thread.is_alive():
                        self.logger.warning(f"{strategy_type} did not stop gracefully after 10 seconds")
                        self.strategy_statuses[strategy_type]["status"] = "force_stopped"
                    else:
                        self.logger.info(f"{strategy_type} stopped successfully")
                        stopped_count += 1
                        self.strategy_statuses[strategy_type]["status"] = "stopped"
                else:
                    self.logger.info(f"{strategy_type} was already stopped")
                    stopped_count += 1
                    self.strategy_statuses[strategy_type]["status"] = "stopped"
            
            # Clean up strategies
            cleanup_errors = 0
            for strategy_type, strategy in self.strategies.items():
                try:
                    self.logger.info(f"Cleaning up {strategy_type}")
                    strategy.cleanup()
                    
                    # Update monitor with strategy status
                    strategy_id = f"{strategy_type}_{self.account}_{self.base_symbol}_{self.quote_symbol}"
                    self.monitor.update_strategy_status(strategy_id, "stopped")
                    
                except Exception as e:
                    self.logger.error(f"Error cleaning up {strategy_type}: {e}")
                    import traceback
                    self.logger.error(f"Traceback: {traceback.format_exc()}")
                    cleanup_errors += 1
                    if strategy_type in self.strategy_statuses:
                        self.strategy_statuses[strategy_type]["errors"] += 1
            
            # Print final status summary
            self.logger.info(f"Stop summary: {stopped_count}/{len(self.strategy_threads)} strategies stopped successfully")
            if cleanup_errors > 0:
                self.logger.warning(f"Encountered {cleanup_errors} errors during cleanup")
            
            # Stop the status monitor if it's running
            self.stop_status_monitor()
                
            self._print_status_summary(final=True)
            self.logger.info(f"All strategies stopped for {self.trading_pair}")
        except Exception as e:
            self.logger.error(f"Error stopping coordinator: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
        
    def is_running(self) -> bool:
        """Check if the coordinator is running."""
        return self.running
        
    def get_status_report(self) -> Dict[str, Any]:
        """Get a detailed status report of all strategies.
        
        Returns:
            A dictionary containing status information for the coordinator and all strategies.
        """
        # Calculate runtime
        runtime_seconds = 0
        if self.start_time:
            runtime_seconds = time.time() - self.start_time
        
        # Count strategies by status
        status_counts = {}
        for strategy_type, status in self.strategy_statuses.items():
            current_status = status.get("status", "unknown")
            status_counts[current_status] = status_counts.get(current_status, 0) + 1
        
        # Build the report
        report = {
            "coordinator": {
                "running": self.running,
                "runtime_seconds": runtime_seconds,
                "trading_pair": self.trading_pair,
                "account": self.account,
                "total_strategies": len(self.strategies),
                "status_counts": status_counts
            },
            "strategies": {}
        }
        
        # Add detailed strategy information
        for strategy_type, status in self.strategy_statuses.items():
            # Calculate strategy runtime
            strategy_runtime = 0
            if "start_time" in status:
                strategy_runtime = time.time() - status["start_time"]
                
            report["strategies"][strategy_type] = {
                "status": status.get("status", "unknown"),
                "cycles_completed": status.get("cycles_completed", 0),
                "errors": status.get("errors", 0),
                "runtime_seconds": strategy_runtime,
                "last_update": status.get("last_update", 0),
                "last_error": status.get("last_error", None)
            }
            
        return report
        
    def print_status_report(self):
        """Print a formatted status report to the log."""
        report = self.get_status_report()
        
        # Print coordinator status
        self.logger.info(f"Status Report for {self.trading_pair} Coordinator:")
        self.logger.info("-" * 60)
        
        # Format runtime
        runtime = report["coordinator"]["runtime_seconds"]
        hours, remainder = divmod(runtime, 3600)
        minutes, seconds = divmod(remainder, 60)
        runtime_str = f"{int(hours)}h {int(minutes)}m {int(seconds)}s"
        
        self.logger.info(f"Running: {report['coordinator']['running']}")
        self.logger.info(f"Runtime: {runtime_str}")
        self.logger.info(f"Account: {report['coordinator']['account']}")
        self.logger.info(f"Trading Pair: {report['coordinator']['trading_pair']}")
        self.logger.info(f"Total Strategies: {report['coordinator']['total_strategies']}")
        
        # Print status counts
        status_summary = ", ".join([f"{count} {status}" for status, count in report["coordinator"]["status_counts"].items()])
        self.logger.info(f"Status Summary: {status_summary}")
        
        # Print strategy details
        self.logger.info("\nStrategy Details:")
        self.logger.info("-" * 60)
        
        for strategy_name, strategy_data in report["strategies"].items():
            # Format strategy runtime
            s_runtime = strategy_data["runtime_seconds"]
            s_hours, s_remainder = divmod(s_runtime, 3600)
            s_minutes, s_seconds = divmod(s_remainder, 60)
            s_runtime_str = f"{int(s_hours)}h {int(s_minutes)}m {int(s_seconds)}s"
            
            # Format last update time
            last_update = strategy_data["last_update"]
            if last_update > 0:
                time_since_update = time.time() - last_update
                if time_since_update < 60:
                    update_str = f"{int(time_since_update)}s ago"
                elif time_since_update < 3600:
                    update_str = f"{int(time_since_update/60)}m ago"
                else:
                    update_str = f"{int(time_since_update/3600)}h ago"
            else:
                update_str = "never"
                
            self.logger.info(f"Strategy: {strategy_name}")
            self.logger.info(f"  Status: {strategy_data['status'].upper()}")
            self.logger.info(f"  Cycles: {strategy_data['cycles_completed']}")
            self.logger.info(f"  Errors: {strategy_data['errors']}")
            self.logger.info(f"  Runtime: {s_runtime_str}")
            self.logger.info(f"  Last Update: {update_str}")
            
            if strategy_data["last_error"]:
                self.logger.info(f"  Last Error: {strategy_data['last_error']}")
            
            self.logger.info("")
        
        self.logger.info("-" * 60)
        
    def _print_status_summary(self, final=False):
        """Print a summary of all strategy statuses."""
        if not self.strategy_statuses:
            self.logger.info("No strategies to report status for")
            return
            
        summary_type = "Final" if final else "Current"
        self.logger.info(f"{summary_type} Strategy Status Summary for {self.trading_pair}:")
        self.logger.info("-" * 50)
        
        # Calculate runtime if coordinator is running
        runtime_str = "N/A"
        if self.start_time:
            runtime_seconds = time.time() - self.start_time
            hours, remainder = divmod(runtime_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            runtime_str = f"{int(hours)}h {int(minutes)}m {int(seconds)}s"
            
        self.logger.info(f"Total Runtime: {runtime_str}")
        self.logger.info(f"Total Strategies: {len(self.strategy_statuses)}")
        
        # Count strategies by status
        status_counts = {}
        for strategy_type, status in self.strategy_statuses.items():
            current_status = status.get("status", "unknown")
            status_counts[current_status] = status_counts.get(current_status, 0) + 1
            
        status_summary = ", ".join([f"{count} {status}" for status, count in status_counts.items()])
        self.logger.info(f"Status Summary: {status_summary}")
        
        # Print details for each strategy
        for strategy_type, status in self.strategy_statuses.items():
            current_status = status.get("status", "unknown")
            cycles = status.get("cycles_completed", 0)
            errors = status.get("errors", 0)
            
            # Calculate strategy runtime
            strategy_runtime = "N/A"
            if "start_time" in status:
                strategy_seconds = time.time() - status["start_time"]
                hours, remainder = divmod(strategy_seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                strategy_runtime = f"{int(hours)}h {int(minutes)}m {int(seconds)}s"
                
            self.logger.info(f"  {strategy_type}: {current_status.upper()}, Cycles: {cycles}, Errors: {errors}, Runtime: {strategy_runtime}")
            
        self.logger.info("-" * 50)
        
    def start_status_monitor(self, interval_seconds=300):
        """Start a background thread to periodically print status updates.
        
        Args:
            interval_seconds: How often to print status updates (default: 5 minutes)
        """
        if not hasattr(self, 'status_monitor_thread') or not self.status_monitor_thread.is_alive():
            self.logger.info(f"Starting status monitor thread with {interval_seconds}s interval")
            self.status_monitor_running = True
            self.status_monitor_thread = threading.Thread(
                target=self._status_monitor_loop,
                args=(interval_seconds,),
                name="StatusMonitorThread"
            )
            self.status_monitor_thread.daemon = True
            self.status_monitor_thread.start()
        else:
            self.logger.warning("Status monitor thread is already running")
    
    def stop_status_monitor(self):
        """Stop the status monitor thread."""
        if hasattr(self, 'status_monitor_thread') and self.status_monitor_thread.is_alive():
            self.logger.info("Stopping status monitor thread")
            self.status_monitor_running = False
            self.status_monitor_thread.join(timeout=10)
            if self.status_monitor_thread.is_alive():
                self.logger.warning("Status monitor thread did not stop gracefully")
        else:
            self.logger.warning("Status monitor thread is not running")
    
    def _status_monitor_loop(self, interval_seconds):
        """Background loop to periodically print status updates."""
        last_print = time.time()
        
        while self.running and self.status_monitor_running:
            # Check if it's time to print status
            current_time = time.time()
            if current_time - last_print >= interval_seconds:
                # Use the new detailed status report instead of the summary
                self.print_status_report()
                last_print = current_time
                
                # Also check for any stalled strategies
                self._check_for_stalled_strategies()
                
            # Sleep for a short time to avoid busy waiting
            time.sleep(5)
    
    def _check_for_stalled_strategies(self):
        """Check for strategies that haven't updated their status recently."""
        current_time = time.time()
        stalled_strategies = []
        
        for strategy_type, status in self.strategy_statuses.items():
            if status.get("status") == "running":
                last_update = status.get("last_update", 0)
                if current_time - last_update > 300:  # 5 minutes
                    stalled_strategies.append(strategy_type)
                    self.logger.warning(f"Strategy {strategy_type} may be stalled - no updates for {int(current_time - last_update)}s")
        
        if stalled_strategies:
            self.logger.warning(f"Detected {len(stalled_strategies)} potentially stalled strategies: {', '.join(stalled_strategies)}")
        
    @classmethod
    def from_config(cls, client: LibreClient, config: Dict[str, Any]) -> 'StrategyCoordinator':
        """Create a coordinator from a configuration dictionary."""
        coordinator = cls(client, config)
        
        # Add strategies from configuration
        strategies_config = config.get('strategies', {})
        for strategy_type, parameters in strategies_config.items():
            if parameters.get('enabled', True):
                coordinator.add_strategy(strategy_type, parameters)
                
        return coordinator 