#!/usr/bin/env python3
"""
Strategy Dashboard - Real-time monitoring for DEX strategies
"""

import os
import sys
import yaml
import json
import time
import threading
from datetime import datetime, timedelta
from flask import Flask, render_template_string, jsonify

# Add the parent directory to Python path to import pylibre
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.pylibre import LibreClient
from src.pylibre.dex import DexClient

# Initialize Flask app
app = Flask(__name__)

# Global state for dashboard data
dashboard_data = {
    'last_update': None,
    'market_data': {},
    'order_stats': {},
    'price_chart_data': [],
    'order_chart_data': [],
    'system_status': {
        'coordinator_running': False,
        'monitor_running': False,
        'last_check': None
    }
}

# Configuration
CONFIG = {
    'refresh_interval': 30,  # Seconds between data refreshes
    'history_points': 100,   # Number of data points to keep in history
    'trading_pairs': ['BTCUSDT', 'LIBREBTC'],
    'chart_timeframes': ['1h', '6h', '24h']
}

# HTML template for the dashboard
DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>DEX Strategy Dashboard</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 0;
            background-color: #f5f5f5;
            color: #333;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            background-color: #fff;
            padding: 15px;
            border-radius: 5px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .header h1 {
            margin: 0;
            font-size: 24px;
            color: #333;
        }
        .status-indicator {
            display: flex;
            align-items: center;
        }
        .status-dot {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 5px;
        }
        .status-dot.green {
            background-color: #4CAF50;
        }
        .status-dot.red {
            background-color: #F44336;
        }
        .status-text {
            font-size: 14px;
        }
        .card {
            background-color: #fff;
            border-radius: 5px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            padding: 20px;
            margin-bottom: 20px;
        }
        .card-header {
            margin-top: 0;
            margin-bottom: 15px;
            font-size: 18px;
            color: #555;
            border-bottom: 1px solid #eee;
            padding-bottom: 10px;
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
        }
        .price-info {
            display: flex;
            justify-content: space-between;
            margin-bottom: 10px;
        }
        .price-label {
            font-weight: bold;
        }
        .price-value {
            font-family: monospace;
        }
        .highlight {
            color: #2196F3;
            font-weight: bold;
        }
        .chart-container {
            position: relative;
            height: 250px;
            margin-top: 20px;
        }
        .stat-box {
            text-align: center;
            padding: 15px;
            background-color: #f9f9f9;
            border-radius: 5px;
            margin-bottom: 10px;
        }
        .stat-value {
            font-size: 24px;
            font-weight: bold;
            margin: 5px 0;
        }
        .stat-label {
            font-size: 14px;
            color: #777;
        }
        .footer {
            text-align: center;
            margin-top: 20px;
            font-size: 12px;
            color: #999;
        }
        .warning {
            color: #FF9800;
        }
        .error {
            color: #F44336;
        }
        .success {
            color: #4CAF50;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>DEX Strategy Dashboard</h1>
            <div class="status-indicator">
                <div class="status-dot {{ 'green' if system_status.coordinator_running else 'red' }}"></div>
                <div class="status-text">Coordinator: {{ 'Running' if system_status.coordinator_running else 'Stopped' }}</div>
                &nbsp;&nbsp;
                <div class="status-dot {{ 'green' if system_status.monitor_running else 'red' }}"></div>
                <div class="status-text">Monitor: {{ 'Running' if system_status.monitor_running else 'Stopped' }}</div>
            </div>
            <div>
                Last updated: {{ last_update }}
            </div>
        </div>
        
        <div class="grid">
            {% for pair, data in market_data.items() %}
            <div class="card">
                <h2 class="card-header">{{ pair }} Market</h2>
                <div class="price-info">
                    <span class="price-label">Oracle Price:</span>
                    <span class="price-value">${{ "%.2f"|format(data.oracle_price) }}</span>
                </div>
                <div class="price-info">
                    <span class="price-label">DEX Price:</span>
                    <span class="price-value">${{ "%.2f"|format(data.dex_price) }}</span>
                </div>
                <div class="price-info">
                    <span class="price-label">Price Gap:</span>
                    <span class="price-value {{ 'success' if data.price_gap_percent|abs < 0.5 else 'warning' if data.price_gap_percent|abs < 1.0 else 'error' }}">
                        {{ "%.2f"|format(data.price_gap_percent|abs) }}% ({{ "Higher" if data.price_gap < 0 else "Lower" }})
                    </span>
                </div>
                <div class="chart-container">
                    <canvas id="priceChart{{ pair }}"></canvas>
                </div>
            </div>
            {% endfor %}
            
            {% for pair, data in order_stats.items() %}
            <div class="card">
                <h2 class="card-header">{{ pair }} Orders</h2>
                <div class="stat-box">
                    <div class="stat-value {{ 'success' if data.order_count <= data.max_orders else 'error' }}">{{ data.order_count }}</div>
                    <div class="stat-label">Current Orders (Max: {{ data.max_orders }})</div>
                </div>
                <div class="price-info">
                    <span class="price-label">Bids:</span>
                    <span class="price-value">{{ data.bid_count }}</span>
                </div>
                <div class="price-info">
                    <span class="price-label">Asks:</span>
                    <span class="price-value">{{ data.ask_count }}</span>
                </div>
                <div class="price-info">
                    <span class="price-label">Last Cancelled:</span>
                    <span class="price-value">{{ data.last_cancelled or 'None' }}</span>
                </div>
                <div class="chart-container">
                    <canvas id="orderChart{{ pair }}"></canvas>
                </div>
            </div>
            {% endfor %}
        </div>
        
        <div class="footer">
            DEX Strategy Dashboard v1.0 | Last system check: {{ system_status.last_check }}
        </div>
    </div>
    
    <script>
        // Initialize charts
        const charts = {};
        
        {% for pair, data in market_data.items() %}
        const priceCtx{{ pair }} = document.getElementById('priceChart{{ pair }}').getContext('2d');
        charts.price{{ pair }} = new Chart(priceCtx{{ pair }}, {
            type: 'line',
            data: {
                labels: {{ price_chart_data[pair].labels|tojson }},
                datasets: [
                    {
                        label: 'DEX Price',
                        data: {{ price_chart_data[pair].dex_prices|tojson }},
                        borderColor: 'rgb(54, 162, 235)',
                        tension: 0.1
                    },
                    {
                        label: 'Oracle Price',
                        data: {{ price_chart_data[pair].oracle_prices|tojson }},
                        borderColor: 'rgb(255, 99, 132)',
                        borderDash: [5, 5],
                        tension: 0.1
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: false
                    }
                }
            }
        });
        {% endfor %}
        
        {% for pair, data in order_stats.items() %}
        const orderCtx{{ pair }} = document.getElementById('orderChart{{ pair }}').getContext('2d');
        charts.orders{{ pair }} = new Chart(orderCtx{{ pair }}, {
            type: 'line',
            data: {
                labels: {{ order_chart_data[pair].labels|tojson }},
                datasets: [
                    {
                        label: 'Total Orders',
                        data: {{ order_chart_data[pair].total_orders|tojson }},
                        borderColor: 'rgb(75, 192, 192)',
                        tension: 0.1
                    },
                    {
                        label: 'Bid Orders',
                        data: {{ order_chart_data[pair].bid_orders|tojson }},
                        borderColor: 'rgb(54, 162, 235)',
                        borderDash: [5, 5],
                        tension: 0.1
                    },
                    {
                        label: 'Ask Orders',
                        data: {{ order_chart_data[pair].ask_orders|tojson }},
                        borderColor: 'rgb(255, 99, 132)',
                        borderDash: [5, 5],
                        tension: 0.1
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
        {% endfor %}
        
        // Auto refresh
        setInterval(function() {
            fetch('/api/data')
                .then(response => response.json())
                .then(data => {
                    // Update page content without reloading
                    document.querySelector('.container').innerHTML = data.html;
                    
                    // Reinitialize charts
                    Object.values(charts).forEach(chart => chart.destroy());
                    eval(data.charts_js);
                });
        }, {{ refresh_interval * 1000 }});
    </script>
</body>
</html>
"""

def check_service_status(service_name):
    """Check if a specific service is running using screen sessions"""
    try:
        import subprocess
        result = subprocess.run(['screen', '-ls'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return service_name in result.stdout
    except Exception as e:
        print(f"Error checking service status: {e}")
        return False

def update_system_status():
    """Update the system status information"""
    global dashboard_data
    
    dashboard_data['system_status'] = {
        'coordinator_running': check_service_status('strategy_coordinator_mainnet'),
        'monitor_running': check_service_status('strategy_monitor_mainnet'),
        'last_check': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }

class DataCollector:
    """Collects data from DEX and maintains dashboard state"""
    
    def __init__(self):
        # Load config
        try:
            with open('config/strategies.mainnet.yaml', 'r') as f:
                self.config = yaml.safe_load(f)
        except Exception as e:
            print(f"Error loading config: {e}")
            self.config = {}
            
        # Initialize clients
        try:
            self.client = LibreClient(
                api_url=self.config.get('api_endpoint', 'https://lb.libre.org'),
                network='mainnet',
                config_path='config/config.yaml',
                verbose=False
            )
            self.dex = DexClient(self.client)
        except Exception as e:
            print(f"Error initializing clients: {e}")
            self.client = None
            self.dex = None
            
        # Set up data structures for each trading pair
        self.initialize_data_structures()
            
    def initialize_data_structures(self):
        """Initialize the data structures for each trading pair"""
        global dashboard_data
        
        for pair in CONFIG['trading_pairs']:
            # Initialize market data
            if pair not in dashboard_data['market_data']:
                dashboard_data['market_data'][pair] = {
                    'oracle_price': 0,
                    'dex_price': 0,
                    'price_gap': 0,
                    'price_gap_percent': 0
                }
                
            # Initialize order stats
            strategy_group = pair  # e.g., BTCUSDT
            if pair not in dashboard_data['order_stats']:
                dashboard_data['order_stats'][pair] = {
                    'order_count': 0,
                    'max_orders': self.config.get('strategy_groups', {}).get(strategy_group, {}).get('num_orders', 100),
                    'bid_count': 0,
                    'ask_count': 0,
                    'last_cancelled': None
                }
                
            # Initialize chart data
            if pair not in dashboard_data['price_chart_data']:
                dashboard_data['price_chart_data'][pair] = {
                    'labels': [],
                    'dex_prices': [],
                    'oracle_prices': []
                }
                
            if pair not in dashboard_data['order_chart_data']:
                dashboard_data['order_chart_data'][pair] = {
                    'labels': [],
                    'total_orders': [],
                    'bid_orders': [],
                    'ask_orders': []
                }
    
    def get_oracle_price(self, symbol):
        """Get oracle price for a symbol"""
        try:
            # Extract base symbol
            base_symbol = symbol[:3].lower()  # e.g., btc
            
            # Query oracle
            response = self.client.get_table_rows(
                code="chainlink",
                scope="chainlink",
                table="feed",
                limit=100
            )
            
            if not response.get('success', False):
                print(f"Oracle data retrieval failed: {response.get('error', 'Unknown error')}")
                return None
            
            # Find the relevant price feed
            target_pair = f"{base_symbol}usd"  # e.g., btcusd
            
            for feed in response.get('rows', []):
                pair = feed.get('pair', '')
                if pair == target_pair:
                    # Extract price from the feed
                    price_value = float(feed.get('price', 0))
                    if price_value > 0:
                        return price_value
            
            return None
        except Exception as e:
            print(f"Error fetching oracle price: {e}")
            return None
    
    def get_dex_market_data(self, symbol):
        """Get market data from DEX for a symbol"""
        try:
            # Split symbol into base and quote
            base_symbol = symbol[:3]  # e.g., BTC
            quote_symbol = symbol[3:]  # e.g., USDT
            
            # Get orderbook
            orderbook = self.dex.fetch_order_book(
                quote_symbol=quote_symbol,
                base_symbol=base_symbol
            )
            
            # Process bids and asks
            bids = orderbook.get('bids', [])
            asks = orderbook.get('offers', [])
            
            # Check if we have orders
            if not bids or not asks:
                return None, 0, 0
                
            # Calculate market price as mid-point of best bid and ask
            best_bid = float(bids[0]['price']) if bids else 0
            best_ask = float(asks[0]['price']) if asks else 0
            
            if best_bid <= 0 or best_ask <= 0:
                return None, 0, 0
                
            dex_price = (best_bid + best_ask) / 2
            
            # Count our orders
            account = self.config.get('accounts', {}).get(symbol, {}).get('liquidity_provider')
            bid_count = sum(1 for bid in bids if bid.get('account') == account)
            ask_count = sum(1 for ask in asks if ask.get('account') == account)
            
            return dex_price, bid_count, ask_count
        except Exception as e:
            print(f"Error fetching DEX market data: {e}")
            return None, 0, 0
            
    def update_data(self):
        """Update all dashboard data"""
        global dashboard_data
        
        try:
            if not self.client or not self.dex:
                print("Clients not initialized, skipping data update")
                return
                
            # Update time
            current_time = datetime.now()
            time_str = current_time.strftime('%Y-%m-%d %H:%M:%S')
            dashboard_data['last_update'] = time_str
            
            # Update for each trading pair
            for pair in CONFIG['trading_pairs']:
                # Get oracle price
                oracle_price = self.get_oracle_price(pair)
                
                # Get DEX market data
                dex_price, bid_count, ask_count = self.get_dex_market_data(pair)
                
                # Skip if we couldn't get prices
                if not oracle_price or not dex_price:
                    continue
                    
                # Calculate price gap
                price_gap = oracle_price - dex_price
                price_gap_percent = (price_gap / oracle_price) * 100
                
                # Update market data
                dashboard_data['market_data'][pair] = {
                    'oracle_price': oracle_price,
                    'dex_price': dex_price,
                    'price_gap': price_gap,
                    'price_gap_percent': price_gap_percent
                }
                
                # Update order stats
                order_count = bid_count + ask_count
                dashboard_data['order_stats'][pair] = {
                    'order_count': order_count,
                    'max_orders': self.config.get('strategy_groups', {}).get(pair, {}).get('num_orders', 100),
                    'bid_count': bid_count,
                    'ask_count': ask_count,
                    'last_cancelled': dashboard_data['order_stats'].get(pair, {}).get('last_cancelled')
                }
                
                # Add data point to charts
                dashboard_data['price_chart_data'][pair]['labels'].append(time_str)
                dashboard_data['price_chart_data'][pair]['dex_prices'].append(dex_price)
                dashboard_data['price_chart_data'][pair]['oracle_prices'].append(oracle_price)
                
                dashboard_data['order_chart_data'][pair]['labels'].append(time_str)
                dashboard_data['order_chart_data'][pair]['total_orders'].append(order_count)
                dashboard_data['order_chart_data'][pair]['bid_orders'].append(bid_count)
                dashboard_data['order_chart_data'][pair]['ask_orders'].append(ask_count)
                
                # Trim data to keep only the last N points
                max_points = CONFIG['history_points']
                if len(dashboard_data['price_chart_data'][pair]['labels']) > max_points:
                    dashboard_data['price_chart_data'][pair]['labels'] = dashboard_data['price_chart_data'][pair]['labels'][-max_points:]
                    dashboard_data['price_chart_data'][pair]['dex_prices'] = dashboard_data['price_chart_data'][pair]['dex_prices'][-max_points:]
                    dashboard_data['price_chart_data'][pair]['oracle_prices'] = dashboard_data['price_chart_data'][pair]['oracle_prices'][-max_points:]
                    
                if len(dashboard_data['order_chart_data'][pair]['labels']) > max_points:
                    dashboard_data['order_chart_data'][pair]['labels'] = dashboard_data['order_chart_data'][pair]['labels'][-max_points:]
                    dashboard_data['order_chart_data'][pair]['total_orders'] = dashboard_data['order_chart_data'][pair]['total_orders'][-max_points:]
                    dashboard_data['order_chart_data'][pair]['bid_orders'] = dashboard_data['order_chart_data'][pair]['bid_orders'][-max_points:]
                    dashboard_data['order_chart_data'][pair]['ask_orders'] = dashboard_data['order_chart_data'][pair]['ask_orders'][-max_points:]
            
            # Update system status
            update_system_status()
            
        except Exception as e:
            print(f"Error updating dashboard data: {e}")
            import traceback
            traceback.print_exc()

def data_collector_thread():
    """Background thread to collect data"""
    collector = DataCollector()
    
    while True:
        try:
            collector.update_data()
            time.sleep(CONFIG['refresh_interval'])
        except Exception as e:
            print(f"Error in data collector thread: {e}")
            time.sleep(10)  # Wait before trying again

@app.route('/')
def index():
    """Render the dashboard"""
    return render_template_string(
        DASHBOARD_TEMPLATE,
        last_update=dashboard_data['last_update'],
        market_data=dashboard_data['market_data'],
        order_stats=dashboard_data['order_stats'],
        price_chart_data=dashboard_data['price_chart_data'],
        order_chart_data=dashboard_data['order_chart_data'],
        system_status=dashboard_data['system_status'],
        refresh_interval=CONFIG['refresh_interval']
    )

@app.route('/api/data')
def api_data():
    """API endpoint to get the latest data for AJAX updates"""
    html = render_template_string(
        DASHBOARD_TEMPLATE,
        last_update=dashboard_data['last_update'],
        market_data=dashboard_data['market_data'],
        order_stats=dashboard_data['order_stats'],
        price_chart_data=dashboard_data['price_chart_data'],
        order_chart_data=dashboard_data['order_chart_data'],
        system_status=dashboard_data['system_status'],
        refresh_interval=CONFIG['refresh_interval']
    )
    
    # Extract just the JavaScript portion for chart initialization
    charts_js = ""
    start_marker = "<script>"
    end_marker = "// Auto refresh"
    
    try:
        script_start = html.find(start_marker)
        script_end = html.find(end_marker, script_start)
        
        if script_start > 0 and script_end > script_start:
            charts_js = html[script_start + len(start_marker):script_end].strip()
    except Exception as e:
        print(f"Error extracting charts JS: {e}")
    
    return jsonify({
        'html': html,
        'charts_js': charts_js,
        'last_update': dashboard_data['last_update']
    })

def main():
    """Main function"""
    # Start data collector thread
    collector_thread = threading.Thread(target=data_collector_thread, daemon=True)
    collector_thread.start()
    
    # Set up Flask
    host = os.environ.get('DASHBOARD_HOST', '0.0.0.0')
    port = int(os.environ.get('DASHBOARD_PORT', 5000))
    debug = os.environ.get('DASHBOARD_DEBUG', 'false').lower() == 'true'
    
    print(f"Starting DEX Strategy Dashboard on http://{host}:{port}")
    app.run(host=host, port=port, debug=debug)

if __name__ == "__main__":
    main() 