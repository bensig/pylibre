import os
import json
import time
import threading
from typing import Dict, Any, List
from datetime import datetime
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
        
        # Create data directory if it doesn't exist
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Load existing data if available
        self._load_data()
        
        # Start background thread to periodically save data
        self.running = True
        self.save_thread = threading.Thread(target=self._periodic_save)
        self.save_thread.daemon = True
        self.save_thread.start()
        
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
                
            self.logger.debug("Saved monitor data to disk")
            
        except Exception as e:
            self.logger.error(f"Error saving monitor data: {e}")
    
    def _periodic_save(self):
        """Periodically save data to disk."""
        while self.running:
            time.sleep(60)  # Save every minute
            self._save_data()
    
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
        return list(self.strategies.values())
    
    def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get metrics for all strategies."""
        return self.metrics
    
    def cleanup(self):
        """Clean up resources used by the monitor."""
        self.running = False
        if self.save_thread.is_alive():
            self.save_thread.join(timeout=2)
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

def get_monitor() -> StrategyMonitor:
    """Get the global StrategyMonitor instance."""
    global _monitor_instance
    if _monitor_instance is None:
        _monitor_instance = StrategyMonitor()
    return _monitor_instance

def get_dashboard(host="0.0.0.0", port=5000) -> DashboardServer:
    """Get the global DashboardServer instance."""
    global _dashboard_instance, _monitor_instance
    if _dashboard_instance is None:
        monitor = get_monitor()
        _dashboard_instance = DashboardServer(monitor, host, port)
    return _dashboard_instance

def start_dashboard(host="0.0.0.0", port=5000):
    """Start the dashboard server."""
    dashboard = get_dashboard(host, port)
    dashboard.start()
    return dashboard

def stop_dashboard():
    """Stop the dashboard server."""
    global _dashboard_instance
    if _dashboard_instance:
        _dashboard_instance.stop()
        _dashboard_instance = None 