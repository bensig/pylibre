# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PyLibre is a Python SDK and trading bot framework for the Libre blockchain's decentralized exchange (DEX). It provides automated trading, market making, and order book management capabilities.

## Essential Commands

```bash
# Install development environment
pip install -e ".[dev]"

# Run tests
pytest

# Code formatting and linting
black src/pylibre
isort src/pylibre
mypy src/pylibre

# Run individual strategies
python scripts/run_orderbook_maker.py
python scripts/run_market_price_tracker.py
python scripts/run_trade_simulator.py

# Run all strategies via coordinator
python scripts/run_strategy_coordinator.py

# Deploy as systemd services
sudo bash scripts/install_services.sh
```

## Architecture Overview

### Core Components
- **LibreClient** (`src/pylibre/client.py`): Blockchain interaction using pyntelope
- **DexClient** (`src/pylibre/dex.py`): DEX operations (place/cancel orders)
- **StrategyCoordinator** (`src/pylibre/strategies/coordinator.py`): Manages multiple strategies per trading pair

### Strategy System
All strategies inherit from `BaseStrategy` and run in separate threads:
- **OrderBookMakerStrategy**: Creates bid/ask spreads around a price target
- **MarketPriceTrackerStrategy**: Tracks external prices and places orders
- **TradeSimulatorStrategy**: Generates artificial trading volume
- **OrderBookAnimatorStrategy**: Creates visual order book activity

### Key Design Patterns
- Thread-safe shared data via `SharedDataManager` for price feeds
- Factory pattern for price sources (Binance, fixed price)
- Decimal precision handling (BTC: 8 decimals, USDT: 8, LIBRE: 4)
- Standardized response format: `{"success": bool, "error": str, "data": any}`

## Configuration

Strategies are configured via YAML files in `config/`:
- `strategies.yaml`: Testnet configuration
- `strategies.mainnet.yaml`: Mainnet configuration

Key configuration sections:
- `network`: RPC endpoints and chain ID
- `accounts`: Private keys and roles (maker/tracker/simulator)
- `trading_pairs`: Token contracts and decimal places
- `strategies`: Strategy-specific parameters

## Development Guidelines

1. **Adding New Strategies**: Inherit from `BaseStrategy`, implement `initialize()` and `execute_round()`
2. **Price Handling**: Always use Decimal for financial calculations
3. **Error Handling**: Log errors and return standardized response format
4. **Testing**: Test strategies individually before coordinator integration
5. **Monitoring**: Use the Flask dashboard at http://localhost:5100 for real-time monitoring

## Deployment

The project uses Git branches for deployment:
- **main**: Development branch
- **deployed**: Production branch running on servers
- **strategy-deply**: Previous deployment branch (deprecated)

### Deployment Process
1. Make changes in feature branches
2. Merge to main for testing
3. Cherry-pick or merge stable changes to deployed branch
4. On server: pull deployed branch and restart services

### Production Services
Services are managed via systemd:
```bash
# Install all services (requires root)
sudo bash scripts/install_services.sh

# Control services
sudo systemctl status libre-strategy-coordinator.service
sudo systemctl restart libre-strategy-coordinator.service
sudo journalctl -u libre-strategy-coordinator.service -f
```

The coordinator service runs all strategies for configured trading pairs as defined in `config/strategies.mainnet.yaml`.

### Standalone Orderbook Services

In addition to the coordinator-based strategies, there are two standalone services for specialized orderbook management:

#### 1. Order Animator (`scripts/order_animator.py`)
- Creates visual activity by periodically canceling and replacing orders
- Prioritizes highest bid/lowest ask to influence mid-market price
- Runs every 5 seconds with 2-8 orders per cycle
- Focuses on market appearance and liquidity

#### 2. Oracle Aligned Orderbook (`scripts/oracle_aligned_orderbook.py`)
- Maintains exactly 15 bids and 15 offers aligned with Chainlink oracle prices
- Ensures DEX mid-price stays close to oracle price
- Implements sophisticated order management with batch processing
- Critical for price accuracy and arbitrage prevention

### Managing Standalone Services

Use the management script for easy control:
```bash
# Start services in screen sessions (current method)
./scripts/manage_orderbook_services.sh --screen start

# Or use systemd (production recommended)
sudo ./scripts/manage_orderbook_services.sh --systemd start

# Check status
./scripts/manage_orderbook_services.sh --screen status

# View logs (systemd only)
sudo ./scripts/manage_orderbook_services.sh --systemd logs
```

Enhanced monitored versions (`*_monitored.py`) integrate with the PyLibre monitoring system and update the same monitoring files used by the dashboard.

## Important Files to Know

- `src/pylibre/strategies/templates/base_strategy.py`: Strategy template
- `scripts/run_strategy_coordinator.py`: Main entry point for production
- `systemd/`: Service definitions for deployment
- `monitor_data/`: Real-time strategy state (auto-generated)
- `shared_data/`: Price feed data (auto-generated)