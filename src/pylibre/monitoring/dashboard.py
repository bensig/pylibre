import os
import json
import time
import threading
import re
import glob
from typing import Dict, Any, List
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify, request
from pylibre.utils.logger import StrategyLogger, LogLevel

class StrategyMonitor:
    """
    Monitors and collects metrics from running strategies.
    Acts as a central repository for strategy status and performance data.
    """
    
    def __init__(self, data_dir="monitor_data"):
        """Initialize the strategy monitor."""
        self.logger = StrategyLogger("StrategyMonitor", level=LogLevel.INFO)
        self.data_dir = data_dir
        self.strategies = {}
        self.metrics = {}
        self.last_update = {}
        self.pnl_data = {}  # New: Store PnL data by account and trading pair
        
        # Create data directory if it doesn't exist
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Load existing data if available
        self._load_data()
        
        # Start background thread to periodically save data
        self.running = True
        self.save_thread = threading.Thread(target=self._periodic_save)
        self.save_thread.daemon = True
        self.save_thread.start()
        
        # Start background thread to parse logs
        self.log_parser_thread = threading.Thread(target=self._periodic_log_parsing)
        self.log_parser_thread.daemon = True
        self.log_parser_thread.start()
    
    def _load_data(self):
        """Load strategy data from disk."""
        try:
            # Load strategies data
            strategies_file = os.path.join(self.data_dir, "strategies.json")
            if os.path.exists(strategies_file):
                with open(strategies_file, 'r') as f:
                    self.strategies = json.load(f)
                self.logger.info(f"Loaded data for {len(self.strategies)} strategies")
            
            # Load metrics data
            metrics_file = os.path.join(self.data_dir, "metrics.json")
            if os.path.exists(metrics_file):
                with open(metrics_file, 'r') as f:
                    self.metrics = json.load(f)
                self.logger.info(f"Loaded metrics data")
                
            # Load last update timestamps
            update_file = os.path.join(self.data_dir, "last_update.json")
            if os.path.exists(update_file):
                with open(update_file, 'r') as f:
                    self.last_update = json.load(f)
            
            # Load PnL data
            pnl_file = os.path.join(self.data_dir, "pnl_data.json")
            if os.path.exists(pnl_file):
                with open(pnl_file, 'r') as f:
                    self.pnl_data = json.load(f)
                self.logger.info(f"Loaded PnL data")
                
        except Exception as e:
            self.logger.error(f"Error loading monitor data: {e}")
    
    def _save_data(self):
        """Save strategy data to disk."""
        try:
            # Save strategies data
            strategies_file = os.path.join(self.data_dir, "strategies.json")
            with open(strategies_file, 'w') as f:
                json.dump(self.strategies, f, indent=2)
            
            # Save metrics data
            metrics_file = os.path.join(self.data_dir, "metrics.json")
            with open(metrics_file, 'w') as f:
                json.dump(self.metrics, f, indent=2)
                
            # Save last update timestamps
            update_file = os.path.join(self.data_dir, "last_update.json")
            with open(update_file, 'w') as f:
                json.dump(self.last_update, f, indent=2)
            
            # Save PnL data
            pnl_file = os.path.join(self.data_dir, "pnl_data.json")
            with open(pnl_file, 'w') as f:
                json.dump(self.pnl_data, f, indent=2)
                
            self.logger.debug("Saved monitor data to disk")
            
        except Exception as e:
            self.logger.error(f"Error saving monitor data: {e}")
    
    def _periodic_save(self):
        """Periodically save data to disk."""
        while self.running:
            time.sleep(60)  # Save every minute
            self._save_data()
    
    def _periodic_log_parsing(self):
        """Periodically parse strategy logs to update metrics."""
        while self.running:
            try:
                self._parse_strategy_logs()
                time.sleep(60)  # Parse logs every minute
            except Exception as e:
                self.logger.error(f"Error parsing logs: {e}")
                time.sleep(60)  # Continue despite errors
    
    def _parse_strategy_logs(self):
        """Parse strategy logs to extract metrics."""
        self.logger.info("Parsing strategy logs for metrics...")
        
        # Find all strategy log files
        log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "logs")
        today = datetime.now().strftime("%Y%m%d")
        strategy_logs = glob.glob(os.path.join(log_dir, f"Strategy_*_{today}.log"))
        
        for log_file in strategy_logs:
            try:
                # Extract account name from log filename
                filename = os.path.basename(log_file)
                account = filename.split('_')[1]
                
                # Parse the log file
                self._parse_log_file(log_file, account)
            except Exception as e:
                self.logger.error(f"Error parsing log file {log_file}: {e}")
    
    def _parse_log_file(self, log_file, account):
        """Parse a single strategy log file to extract metrics."""
        self.logger.debug(f"Parsing log file: {log_file}")
        
        # Patterns to match in logs
        patterns = {
            'initialized': r"Initialized (\w+)Strategy with:",
            'trading_pair': r"Trading pair: (\w+)/(\w+)",
            'orders_placed': r"Placing (buy|sell) order: ([\d\.]+) (\w+) @ ([\d\.E-]+)",
            'orders_filled_buy': r"💸.*BUY ([\d\.]+) (\w+) at ([\d\.E-]+)",
            'orders_filled_sell': r"💰.*SELL ([\d\.]+) (\w+) at ([\d\.E-]+)",
            'orders_cancelled': r"Cancelled (buy|sell) order at price",
            'cycle_complete': r"cycle complete",
            'error': r"ERROR",
            'warning': r"WARNING"
        }
        
        # Initialize metrics for new strategies
        strategy_metrics = {}
        current_strategy_type = None
        
        with open(log_file, 'r') as f:
            for line in f:
                try:
                    # Extract timestamp
                    timestamp_match = re.match(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})", line)
                    if not timestamp_match:
                        continue
                    
                    timestamp = timestamp_match.group(1)
                    
                    # Check for strategy initialization
                    init_match = re.search(patterns['initialized'], line)
                    if init_match:
                        current_strategy_type = init_match.group(1)
                        continue
                    
                    # Extract trading pair
                    pair_match = re.search(patterns['trading_pair'], line)
                    if pair_match and current_strategy_type:
                        base_symbol = pair_match.group(1)
                        quote_symbol = pair_match.group(2)
                        trading_pair = f"{base_symbol}/{quote_symbol}"
                        
                        # Create a unique strategy ID
                        strategy_id = f"{current_strategy_type}Strategy_{account}_{base_symbol}_{quote_symbol}"
                        
                        # Initialize metrics for this strategy if not exists
                        if strategy_id not in strategy_metrics:
                            strategy_metrics[strategy_id] = {
                                'orders_placed': 0,
                                'orders_filled': 0,
                                'orders_cancelled': 0,
                                'errors': 0,
                                'warnings': 0,
                                'cycle_count': 0,
                                'last_cycle_duration_ms': 0,
                                'avg_cycle_duration_ms': 0,
                                'trading_pair': trading_pair,
                                'type': f"{current_strategy_type}Strategy",
                                'account': account
                            }
                        continue
                    
                    # Process metrics for each strategy
                    for strategy_id, metrics in strategy_metrics.items():
                        # Check for placed orders
                        if re.search(patterns['orders_placed'], line):
                            metrics['orders_placed'] += 1
                        
                        # Check for filled buy orders
                        if re.search(patterns['orders_filled_buy'], line):
                            metrics['orders_filled'] += 1
                        
                        # Check for filled sell orders
                        if re.search(patterns['orders_filled_sell'], line):
                            metrics['orders_filled'] += 1
                        
                        # Check for cancelled orders
                        if re.search(patterns['orders_cancelled'], line):
                            metrics['orders_cancelled'] += 1
                        
                        # Check for cycle completion
                        if re.search(patterns['cycle_complete'], line):
                            metrics['cycle_count'] += 1
                        
                        # Check for errors
                        if re.search(patterns['error'], line):
                            metrics['errors'] += 1
                        
                        # Check for warnings
                        if re.search(patterns['warning'], line):
                            metrics['warnings'] += 1
                
                except Exception as e:
                    self.logger.error(f"Error parsing log line: {e}")
        
        # Update metrics in the monitor
        for strategy_id, metrics in strategy_metrics.items():
            # Register strategy if not exists
            if strategy_id not in self.strategies:
                self.register_strategy(
                    strategy_id=strategy_id,
                    strategy_type=metrics['type'],
                    trading_pair=metrics['trading_pair'],
                    account=metrics['account'],
                    parameters={}
                )
            
            # Update metrics
            self.update_strategy_metrics(strategy_id, metrics)
            
            self.logger.debug(f"Updated metrics for {strategy_id} from logs: orders_placed={metrics['orders_placed']}, orders_filled={metrics['orders_filled']}")
    
    def register_strategy(self, strategy_id: str, strategy_type: str, 
                         trading_pair: str, account: str, parameters: Dict[str, Any]) -> None:
        """Register a new strategy with the monitor."""
        self.strategies[strategy_id] = {
            "id": strategy_id,
            "type": strategy_type,
            "trading_pair": trading_pair,
            "account": account,
            "parameters": parameters,
            "status": "initializing",
            "start_time": datetime.now().isoformat(),
            "last_active": datetime.now().isoformat()
        }
        
        # Initialize metrics for this strategy
        self.metrics[strategy_id] = {
            "orders_placed": 0,
            "orders_filled": 0,
            "orders_cancelled": 0,
            "errors": 0,
            "warnings": 0,
            "cycle_count": 0,
            "last_cycle_duration_ms": 0,
            "avg_cycle_duration_ms": 0,
            "history": {
                "timestamps": [],
                "orders_placed": [],
                "orders_filled": []
            }
        }
        
        # Initialize PnL tracking for this account and trading pair if not exists
        account_key = account
        pair_key = trading_pair.replace("/", "")
        
        if account_key not in self.pnl_data:
            self.pnl_data[account_key] = {}
        
        if pair_key not in self.pnl_data[account_key]:
            self.pnl_data[account_key][pair_key] = {
                "initial_balance_base": 0,
                "initial_balance_quote": 0,
                "current_balance_base": 0,
                "current_balance_quote": 0,
                "trades_executed": 0,
                "volume_base": 0,
                "volume_quote": 0,
                "realized_pnl": 0,
                "unrealized_pnl": 0,
                "total_pnl": 0,
                "history": {
                    "timestamps": [],
                    "realized_pnl": [],
                    "unrealized_pnl": [],
                    "total_pnl": []
                }
            }
        
        self.last_update[strategy_id] = datetime.now().isoformat()
        self.logger.info(f"Registered strategy {strategy_id} ({strategy_type})")
        self._save_data()
    
    def update_strategy_status(self, strategy_id: str, status: str) -> None:
        """Update the status of a strategy."""
        if strategy_id in self.strategies:
            self.strategies[strategy_id]["status"] = status
            self.strategies[strategy_id]["last_active"] = datetime.now().isoformat()
            self.last_update[strategy_id] = datetime.now().isoformat()
            self.logger.debug(f"Updated status for {strategy_id}: {status}")
        else:
            self.logger.warning(f"Attempted to update unknown strategy: {strategy_id}")
    
    def update_strategy_metrics(self, strategy_id: str, metrics_update: Dict[str, Any]) -> None:
        """Update metrics for a strategy."""
        if strategy_id not in self.metrics:
            self.logger.warning(f"Attempted to update metrics for unknown strategy: {strategy_id}")
            return
            
        # Update simple metrics
        for key, value in metrics_update.items():
            if key in self.metrics[strategy_id] and key != "history":
                self.metrics[strategy_id][key] = value
        
        # Update historical data if provided
        if "history_update" in metrics_update:
            history_update = metrics_update["history_update"]
            timestamp = datetime.now().isoformat()
            
            # Add new data points to history
            self.metrics[strategy_id]["history"]["timestamps"].append(timestamp)
            
            for key, value in history_update.items():
                if key in self.metrics[strategy_id]["history"]:
                    self.metrics[strategy_id]["history"][key].append(value)
            
            # Limit history to last 1000 points
            max_history = 1000
            for key in self.metrics[strategy_id]["history"]:
                if len(self.metrics[strategy_id]["history"][key]) > max_history:
                    self.metrics[strategy_id]["history"][key] = self.metrics[strategy_id]["history"][key][-max_history:]
        
        self.last_update[strategy_id] = datetime.now().isoformat()
        self.logger.debug(f"Updated metrics for {strategy_id}")
    
    def get_strategy_status(self, strategy_id: str) -> Dict[str, Any]:
        """Get the current status of a strategy."""
        if strategy_id in self.strategies:
            return self.strategies[strategy_id]
        return None
    
    def get_strategy_metrics(self, strategy_id: str) -> Dict[str, Any]:
        """Get the current metrics for a strategy."""
        if strategy_id in self.metrics:
            return self.metrics[strategy_id]
        return None
    
    def get_all_strategies(self) -> List[Dict[str, Any]]:
        """Get information about all registered strategies."""
        if not self.strategies:
            return []
        return list(self.strategies.values())
    
    def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get metrics for all strategies."""
        if not self.metrics:
            return {}
        return self.metrics
    
    def get_account_pnl(self, account: str = None, trading_pair: str = None) -> Dict[str, Any]:
        """
        Get PnL data for accounts and trading pairs.
        
        Args:
            account: Optional account name to filter by
            trading_pair: Optional trading pair to filter by (e.g., "LIBRE/BTC")
            
        Returns:
            Dict with PnL data
        """
        if not self.pnl_data:
            return {}
        
        if account and trading_pair:
            account_key = account
            pair_key = trading_pair.replace("/", "")
            
            if account_key in self.pnl_data and pair_key in self.pnl_data[account_key]:
                return {account_key: {pair_key: self.pnl_data[account_key][pair_key]}}
            return {}
            
        elif account:
            account_key = account
            if account_key in self.pnl_data:
                return {account_key: self.pnl_data[account_key]}
            return {}
            
        elif trading_pair:
            pair_key = trading_pair.replace("/", "")
            result = {}
            
            for account_key, pairs in self.pnl_data.items():
                if pair_key in pairs:
                    if account_key not in result:
                        result[account_key] = {}
                    result[account_key][pair_key] = pairs[pair_key]
            
            return result
            
        else:
            return self.pnl_data
    
    def get_all_pnl_summary(self) -> Dict[str, Any]:
        """
        Get a summary of PnL across all accounts and trading pairs.
        
        Returns:
            Dict with summary statistics
        """
        if not self.pnl_data:
            return {}
        
        summary = {
            "total_accounts": 0,
            "total_trading_pairs": 0,
            "total_trades": 0,
            "total_pnl": 0.0,
            "accounts": []
        }
        
        trading_pairs = set()
        
        for account, pairs_data in self.pnl_data.items():
            account_summary = {
                "account": account,
                "trading_pairs": len(pairs_data),
                "trades": 0,
                "realized_pnl": 0,
                "unrealized_pnl": 0,
                "total_pnl": 0
            }
            
            for pair, data in pairs_data.items():
                trading_pairs.add(pair)
                
                # Update account summary
                account_summary["trades"] += data["trades_executed"]
                account_summary["realized_pnl"] += data["realized_pnl"]
                account_summary["unrealized_pnl"] += data["unrealized_pnl"]
                account_summary["total_pnl"] += data["total_pnl"]
                
                # Update global summary
                summary["total_trades"] += data["trades_executed"]
                summary["total_pnl"] += data["total_pnl"]
            
            summary["accounts"].append(account_summary)
        
        summary["total_accounts"] = len(self.pnl_data)
        summary["total_trading_pairs"] = len(trading_pairs)
        
        return summary
    
    def update_account_pnl(self, account: str, trading_pair: str, 
                          balance_update: Dict[str, float] = None,
                          trade_data: Dict[str, Any] = None) -> None:
        """
        Update PnL data for an account and trading pair.
        
        Args:
            account: Account name
            trading_pair: Trading pair (e.g., "LIBRE/BTC")
            balance_update: Dict with current balances (optional)
            trade_data: Dict with trade information (optional)
        """
        account_key = account
        pair_key = trading_pair.replace("/", "")
        
        # Initialize account and pair if not exists
        if account_key not in self.pnl_data:
            self.pnl_data[account_key] = {}
        
        if pair_key not in self.pnl_data[account_key]:
            self.pnl_data[account_key][pair_key] = {
                "initial_balance_base": 0,
                "initial_balance_quote": 0,
                "current_balance_base": 0,
                "current_balance_quote": 0,
                "trades_executed": 0,
                "volume_base": 0,
                "volume_quote": 0,
                "realized_pnl": 0,
                "unrealized_pnl": 0,
                "total_pnl": 0,
                "history": {
                    "timestamps": [],
                    "realized_pnl": [],
                    "unrealized_pnl": [],
                    "total_pnl": []
                }
            }
        
        # Update balance information if provided
        if balance_update:
            if "base" in balance_update:
                # If initial balance is 0, set it
                if self.pnl_data[account_key][pair_key]["initial_balance_base"] == 0:
                    self.pnl_data[account_key][pair_key]["initial_balance_base"] = balance_update["base"]
                
                self.pnl_data[account_key][pair_key]["current_balance_base"] = balance_update["base"]
            
            if "quote" in balance_update:
                # If initial balance is 0, set it
                if self.pnl_data[account_key][pair_key]["initial_balance_quote"] == 0:
                    self.pnl_data[account_key][pair_key]["initial_balance_quote"] = balance_update["quote"]
                
                self.pnl_data[account_key][pair_key]["current_balance_quote"] = balance_update["quote"]
        
        # Update trade information if provided
        if trade_data:
            if "volume_base" in trade_data:
                self.pnl_data[account_key][pair_key]["volume_base"] += trade_data["volume_base"]
            
            if "volume_quote" in trade_data:
                self.pnl_data[account_key][pair_key]["volume_quote"] += trade_data["volume_quote"]
            
            if "realized_pnl" in trade_data:
                self.pnl_data[account_key][pair_key]["realized_pnl"] += trade_data["realized_pnl"]
            
            self.pnl_data[account_key][pair_key]["trades_executed"] += 1
        
        # Calculate unrealized PnL based on current market price if provided
        if "market_price" in balance_update:
            base_balance = self.pnl_data[account_key][pair_key]["current_balance_base"]
            quote_balance = self.pnl_data[account_key][pair_key]["current_balance_quote"]
            initial_base = self.pnl_data[account_key][pair_key]["initial_balance_base"]
            initial_quote = self.pnl_data[account_key][pair_key]["initial_balance_quote"]
            
            # Calculate current value in quote currency
            current_value = quote_balance + (base_balance * balance_update["market_price"])
            
            # Calculate initial value in quote currency
            initial_value = initial_quote + (initial_base * balance_update["market_price"])
            
            # Calculate unrealized PnL
            unrealized_pnl = current_value - initial_value
            self.pnl_data[account_key][pair_key]["unrealized_pnl"] = unrealized_pnl
        
        # Calculate total PnL
        realized_pnl = self.pnl_data[account_key][pair_key]["realized_pnl"]
        unrealized_pnl = self.pnl_data[account_key][pair_key]["unrealized_pnl"]
        self.pnl_data[account_key][pair_key]["total_pnl"] = realized_pnl + unrealized_pnl
        
        # Update history
        timestamp = datetime.now().isoformat()
        self.pnl_data[account_key][pair_key]["history"]["timestamps"].append(timestamp)
        self.pnl_data[account_key][pair_key]["history"]["realized_pnl"].append(realized_pnl)
        self.pnl_data[account_key][pair_key]["history"]["unrealized_pnl"].append(unrealized_pnl)
        self.pnl_data[account_key][pair_key]["history"]["total_pnl"].append(realized_pnl + unrealized_pnl)
        
        # Limit history to last 1000 points
        max_history = 1000
        for key in self.pnl_data[account_key][pair_key]["history"]:
            if len(self.pnl_data[account_key][pair_key]["history"][key]) > max_history:
                self.pnl_data[account_key][pair_key]["history"][key] = self.pnl_data[account_key][pair_key]["history"][key][-max_history:]
        
        self.logger.debug(f"Updated PnL for {account}/{pair_key}")
        self._save_data()
    
    def cleanup(self):
        """Clean up resources used by the monitor."""
        self.running = False
        if self.save_thread.is_alive():
            self.save_thread.join(timeout=2)
        if self.log_parser_thread.is_alive():
            self.log_parser_thread.join(timeout=2)
        self._save_data()
        self.logger.info("Strategy monitor cleaned up")


class DashboardServer:
    """
    Flask-based web server for the strategy monitoring dashboard.
    """
    
    def __init__(self, monitor: StrategyMonitor, host="0.0.0.0", port=5000):
        """Initialize the dashboard server."""
        self.monitor = monitor
        self.host = host
        self.port = port
        self.app = Flask(__name__, 
                        template_folder=os.path.join(os.path.dirname(__file__), "templates"),
                        static_folder=os.path.join(os.path.dirname(__file__), "static"))
        self.logger = StrategyLogger("Dashboard", level=LogLevel.INFO)
        
        # Set up routes
        self._setup_routes()
        
        # Server thread
        self.server_thread = None
        self.running = False
    
    def _setup_routes(self):
        """Set up Flask routes."""
        
        @self.app.route('/')
        def index():
            """Render the main dashboard page."""
            return render_template('dashboard.html')
        
        @self.app.route('/api/strategies')
        def get_strategies():
            """API endpoint to get all strategies."""
            return jsonify(self.monitor.get_all_strategies())
        
        @self.app.route('/api/strategy/<strategy_id>')
        def get_strategy(strategy_id):
            """API endpoint to get a specific strategy."""
            strategy = self.monitor.get_strategy_status(strategy_id)
            if strategy:
                return jsonify(strategy)
            return jsonify({"error": "Strategy not found"}), 404
        
        @self.app.route('/api/metrics')
        def get_metrics():
            """API endpoint to get metrics for all strategies."""
            return jsonify(self.monitor.get_all_metrics())
        
        @self.app.route('/api/metrics/<strategy_id>')
        def get_strategy_metrics(strategy_id):
            """API endpoint to get metrics for a specific strategy."""
            metrics = self.monitor.get_strategy_metrics(strategy_id)
            if metrics:
                return jsonify(metrics)
            return jsonify({"error": "Strategy not found"}), 404
        
        @self.app.route('/api/pnl')
        def get_all_pnl():
            """API endpoint to get PnL data for all accounts and trading pairs."""
            account = request.args.get('account')
            trading_pair = request.args.get('trading_pair')
            return jsonify(self.monitor.get_account_pnl(account, trading_pair))
        
        @self.app.route('/api/pnl/summary')
        def get_pnl_summary():
            """API endpoint to get a summary of PnL across all accounts and trading pairs."""
            return jsonify(self.monitor.get_all_pnl_summary())
        
        @self.app.route('/api/update', methods=['POST'])
        def update_strategy():
            """API endpoint to update strategy status and metrics."""
            data = request.json
            if not data or 'strategy_id' not in data:
                return jsonify({"error": "Invalid request"}), 400
                
            strategy_id = data['strategy_id']
            
            # Update status if provided
            if 'status' in data:
                self.monitor.update_strategy_status(strategy_id, data['status'])
            
            # Update metrics if provided
            if 'metrics' in data:
                self.monitor.update_strategy_metrics(strategy_id, data['metrics'])
                
            return jsonify({"success": True})
        
        @self.app.route('/api/update/pnl', methods=['POST'])
        def update_pnl():
            """API endpoint to update PnL data for an account and trading pair."""
            data = request.json
            if not data or 'account' not in data or 'trading_pair' not in data:
                return jsonify({"error": "Invalid request"}), 400
            
            account = data['account']
            trading_pair = data['trading_pair']
            balance_update = data.get('balance_update')
            trade_data = data.get('trade_data')
            
            self.monitor.update_account_pnl(account, trading_pair, balance_update, trade_data)
            return jsonify({"success": True})
    
    def start(self):
        """Start the dashboard server in a background thread."""
        if self.running:
            self.logger.warning("Dashboard server is already running")
            return
            
        self.running = True
        self.server_thread = threading.Thread(target=self._run_server)
        self.server_thread.daemon = True
        self.server_thread.start()
        self.logger.info(f"Dashboard server started on http://{self.host}:{self.port}")
    
    def _run_server(self):
        """Run the Flask server."""
        self.app.run(host=self.host, port=self.port, debug=False, use_reloader=False)
    
    def stop(self):
        """Stop the dashboard server."""
        self.running = False
        # Flask doesn't provide a clean way to stop the server from another thread
        # In a production environment, you would use a proper WSGI server like Gunicorn
        self.logger.info("Dashboard server stopping (may take a moment to complete)")


# Singleton instance for global access
_monitor_instance = None
_dashboard_instance = None

def get_monitor(data_dir="monitor_data"):
    """Get the global StrategyMonitor instance."""
    global _monitor_instance
    if _monitor_instance is None:
        _monitor_instance = StrategyMonitor(data_dir=data_dir)
    return _monitor_instance

def get_dashboard(host="0.0.0.0", port=5000):
    """Get the global DashboardServer instance."""
    global _dashboard_instance, _monitor_instance
    if _dashboard_instance is None:
        monitor = get_monitor()
        _dashboard_instance = DashboardServer(monitor, host=host, port=port)
    return _dashboard_instance

def start_dashboard(host="0.0.0.0", port=5000):
    """Start the dashboard server."""
    dashboard = get_dashboard(host=host, port=port)
    dashboard.start()
    return dashboard

def stop_dashboard():
    """Stop the dashboard server."""
    global _dashboard_instance, _monitor_instance
    if _dashboard_instance:
        _dashboard_instance.stop()
    if _monitor_instance:
        _monitor_instance.cleanup()