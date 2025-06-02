# Libre Trading Strategies Deployment Guide

This guide provides instructions for deploying the Libre trading strategies in a production environment.

## Prerequisites

- Linux server with systemd (Ubuntu 20.04+ or similar)
- Python 3.8+
- Git
- Libre account with API keys

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/libre-org/pylibre.git
cd pylibre
```

### 2. Create a Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure the Strategies

Copy the example configuration file and edit it to match your requirements:

```bash
mkdir -p config
cp config/strategies.example.yaml config/strategies.yaml
```

Edit the `config/strategies.yaml` file to configure your trading strategies:

```yaml
# API endpoint
api_endpoint: "https://testnet.libre.org"  # Change to mainnet for production

# Trading pairs configuration
trading_pairs:
  LIBREBTC:
    market_maker:
      num_orders: 30
      min_spread_percentage: 0.01
      max_spread_percentage: 0.15
      quantity_distribution: "random"
      update_interval_ms: 120000  # 2 minutes
    
    animator:
      activity_level: "high"
      orders_per_cycle: 5
      cycle_interval_ms: 3000  # 3 seconds
    
    price_tracker:
      source: "fixed"  # manually set price
      update_interval_ms: 60000  # 1 minute
      price_change_threshold: 0.01  # 1%
      fallback_price: 0.0000002  # Default price for LIBRE/BTC
      
    simulator:
      trade_frequency: "high"
      trade_size_variation: "high"
      price_range_percentage: 0.01
      cycle_interval_ms: 15000
      trades_per_cycle: 2
      trade_pattern: "trend"
      trend_direction: "up"
      trend_strength: 0.7

# Account configuration
accounts:
  main: "your_account_name"  # Replace with your account
  animator: "your_account_name"
  tracker: "your_account_name"
  simulator_primary: "your_account_name"
  simulator_secondary: "your_account_name"
```

### 4. Set Up Environment Variables

Create an environment file to store your API keys and other sensitive information:

```bash
sudo mkdir -p /etc/libre
sudo touch /etc/libre/env
sudo chmod 600 /etc/libre/env
```

Edit the environment file:

```bash
sudo nano /etc/libre/env
```

Add your API keys and other environment variables:

```
LIBRE_API_KEY=your_api_key
LIBRE_API_SECRET=your_api_secret
```

### 5. Install Systemd Services

Use the provided installation script to install the systemd services:

```bash
sudo ./scripts/install_services.sh --user $(whoami) --group $(whoami)
```

This will install all the services. To install specific services, use the appropriate flags:

```bash
sudo ./scripts/install_services.sh --install-coordinator --install-dashboard
```

## Starting and Managing Services

### Start All Services with the Coordinator

The coordinator service manages all the strategies for a specific trading pair. To start it:

```bash
sudo systemctl enable libre-strategy-coordinator.service
sudo systemctl start libre-strategy-coordinator.service
```

### Start Individual Services

If you prefer to run strategies individually:

```bash
# Market Price Tracker
sudo systemctl enable libre-market-price-tracker.service
sudo systemctl start libre-market-price-tracker.service

# OrderBook Maker
sudo systemctl enable libre-orderbook-maker.service
sudo systemctl start libre-orderbook-maker.service

# OrderBook Animator
sudo systemctl enable libre-orderbook-animator.service
sudo systemctl start libre-orderbook-animator.service

# Trade Simulator
sudo systemctl enable libre-trade-simulator.service
sudo systemctl start libre-trade-simulator.service
```

### Start the Dashboard

The dashboard provides a web interface to monitor your strategies:

```bash
sudo systemctl enable libre-dashboard.service
sudo systemctl start libre-dashboard.service
```

By default, the dashboard runs on port 5000. You can access it at `http://your_server_ip:5000`.

### Check Service Status

To check the status of a service:

```bash
sudo systemctl status libre-strategy-coordinator.service
```

### View Logs

To view the logs of a service:

```bash
sudo journalctl -u libre-strategy-coordinator.service -f
```

## Configuring Multiple Trading Pairs

To run strategies for multiple trading pairs, you can create multiple instances of the services with different configuration files.

1. Create a separate configuration file for each trading pair:

```bash
cp config/strategies.yaml config/strategies_librebtc.yaml
cp config/strategies.yaml config/strategies_libreusdt.yaml
```

2. Edit each configuration file to include only the relevant trading pair.

3. Install services for each trading pair:

```bash
sudo ./scripts/install_services.sh --config-dir /path/to/config --install-coordinator
```

## Monitoring and Maintenance

### Dashboard

The monitoring dashboard provides real-time information about your strategies, including:

- Strategy status (running, stopped, error)
- Order statistics (placed, filled, cancelled)
- Performance metrics
- Historical data visualization

### Backup and Recovery

It's recommended to regularly backup your configuration files and environment variables:

```bash
# Backup configuration
cp -r config /path/to/backup/config

# Backup environment variables
sudo cp /etc/libre/env /path/to/backup/env
```

### Updating the Software

To update the software:

1. Stop all services:

```bash
sudo systemctl stop libre-strategy-coordinator.service
```

2. Pull the latest changes:

```bash
git pull
```

3. Update dependencies:

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

4. Restart services:

```bash
sudo systemctl start libre-strategy-coordinator.service
```

## Standalone Orderbook Services

In addition to the coordinator-based strategies, there are two standalone services for specialized orderbook management:

### Order Animator

The Order Animator creates visual activity by periodically canceling and replacing orders:
- Prioritizes highest bid/lowest ask to influence mid-market price
- Runs every 5 seconds with 2-8 orders per cycle
- Focuses on market appearance and liquidity

### Oracle Aligned Orderbook

The Oracle Aligned Orderbook maintains precise price alignment:
- Maintains exactly 15 bids and 15 offers aligned with Chainlink oracle prices
- Ensures DEX mid-price stays close to oracle price
- Implements sophisticated order management with batch processing
- Critical for price accuracy and arbitrage prevention

### Running Standalone Services

#### Method 1: Screen Sessions (Development/Testing)

For quick testing or development, you can run services in screen sessions:

```bash
# Start services in screen sessions
./scripts/manage_orderbook_services.sh --screen start

# Check status
./scripts/manage_orderbook_services.sh --screen status

# Stop services
./scripts/manage_orderbook_services.sh --screen stop

# Or run manually
screen -S animator python scripts/order_animator.py
screen -S oracle-aligned python scripts/oracle_aligned_orderbook.py

# List all screens
screen -ls

# Attach to a screen
screen -r animator
```

#### Method 2: Systemd Services (Production)

For production deployment, use systemd services:

```bash
# Install systemd services
sudo ./scripts/install_services.sh --install-order-animator --install-oracle-aligned

# Start services
sudo systemctl start libre-order-animator.service
sudo systemctl start libre-oracle-aligned-orderbook.service

# Enable auto-start on boot
sudo systemctl enable libre-order-animator.service
sudo systemctl enable libre-oracle-aligned-orderbook.service

# Check status
sudo systemctl status libre-order-animator.service
sudo systemctl status libre-oracle-aligned-orderbook.service

# View logs
sudo journalctl -u libre-order-animator.service -f
sudo journalctl -u libre-oracle-aligned-orderbook.service -f
```

### Monitoring Integration

Enhanced monitored versions of these scripts integrate with the PyLibre monitoring system:
- `order_animator_monitored.py` - Tracks cycles, orders animated, and uptime
- `oracle_aligned_orderbook_monitored.py` - Monitors orders placed/cancelled and oracle price tracking

These monitored versions update the same monitoring files used by the dashboard, allowing you to view their status alongside other strategies.

### Complete System Setup

To run everything together:

```bash
# 1. Start the monitoring dashboard
screen -S dashboard python scripts/run_dashboard.py --port 5100
# Or as a service
sudo systemctl start libre-dashboard.service

# 2. Start the strategy coordinator
screen -S coordinator python scripts/run_strategy_coordinator.py
# Or as a service
sudo systemctl start libre-strategy-coordinator.service

# 3. Start standalone orderbook services (monitored versions recommended)
./scripts/manage_orderbook_services.sh --screen start

# 4. Access the dashboard at http://localhost:5100
```

The dashboard will automatically display monitoring data from:
- Coordinator-managed strategies
- Standalone orderbook services (if using monitored versions)
- Any other strategies writing to the `monitor_data/` directory

This provides a single web interface to monitor all your trading strategies and orderbook management services.

## Troubleshooting

### Common Issues

1. **Service fails to start**:
   - Check the logs: `sudo journalctl -u libre-strategy-coordinator.service -n 100`
   - Verify configuration: Ensure your `strategies.yaml` file is correctly formatted
   - Check permissions: Ensure the user running the service has access to the required files

2. **API connection errors**:
   - Verify API endpoint: Check that the API endpoint in your configuration is correct
   - Check API keys: Ensure your API keys are valid and have the necessary permissions
   - Network issues: Check your server's network connection

3. **Dashboard not accessible**:
   - Check service status: `sudo systemctl status libre-dashboard.service`
   - Firewall issues: Ensure port 5000 is open in your firewall
   - Check logs: `sudo journalctl -u libre-dashboard.service -n 100`

### Getting Help

If you encounter issues not covered in this guide, please:

1. Check the project's GitHub issues
2. Join the Libre community Discord
3. Contact the development team at support@libre.org 