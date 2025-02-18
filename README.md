# PyLibre Trading Strategies

A comprehensive suite of trading strategies for the Libre blockchain, designed to create liquidity and market activity.

## Overview

This project provides a set of trading strategies for the Libre blockchain, including:

- **OrderBookMakerStrategy**: Creates a spread of orders around a center price
- **MarketPriceTrackerStrategy**: Monitors external market prices and updates the center price
- **OrderBookAnimatorStrategy**: Creates the appearance of market activity by periodically canceling and replacing orders
- **TradeSimulatorStrategy**: Creates the appearance of trades being filled

These strategies can be run individually or together using the `StrategyCoordinator`.

## Features

- **Flexible Configuration**: Each strategy can be configured with a wide range of parameters
- **Monitoring Dashboard**: Web-based dashboard for monitoring strategy performance
- **Systemd Integration**: Run strategies as system services
- **Coordination**: Manage multiple strategies for a trading pair

## Installation

### Prerequisites

- Python 3.8+
- Git
- Libre account with API keys

### Setup

1. Clone the repository:

```bash
git clone https://github.com/libre-org/pylibre.git
cd pylibre
```

2. Create a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

3. Configure the strategies:

```bash
cp config/strategies.example.yaml config/strategies.yaml
```

Edit the `config/strategies.yaml` file to configure your trading strategies.

## Usage

### Running Individual Strategies

#### OrderBookMakerStrategy

```bash
python scripts/run_orderbook_maker.py --account your_account --base LIBRE --quote BTC
```

#### MarketPriceTrackerStrategy

```bash
python scripts/run_market_price_tracker.py --account your_account --base LIBRE --quote BTC
```

#### OrderBookAnimatorStrategy

```bash
python scripts/run_orderbook_animator.py --account your_account --base LIBRE --quote BTC
```

#### TradeSimulatorStrategy

```bash
python scripts/run_trade_simulator.py --account your_account --base LIBRE --quote BTC
```

### Running the Strategy Coordinator

```bash
python scripts/run_strategy_coordinator.py --account your_account --base LIBRE --quote BTC
```

### Running the Monitoring Dashboard

```bash
python scripts/run_dashboard.py
```

## Configuration

The `strategies.yaml` file contains the configuration for all strategies. Here's an example:

```yaml
# API endpoint
api_endpoint: "https://testnet.libre.org"

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
      source: "fixed"
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
```

## Production Deployment

For production deployment, see the [Deployment Guide](docs/deployment_guide.md).

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.