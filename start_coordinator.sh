#!/bin/bash
# Script to start the strategy coordinator and monitor in screen sessions

# Set up Python environment
export PATH="/home/ben/.pyenv/shims:$PATH"
eval "$(pyenv init -)"
pyenv shell 3

# Navigate to the project directory (in case script is run from elsewhere)
cd "$(dirname "$0")"

# Define screen session names
COORDINATOR_SESSION="strategy_coordinator_mainnet"
MONITOR_SESSION="strategy_monitor_mainnet"

# Kill existing sessions if they exist
if screen -list | grep -q "$COORDINATOR_SESSION"; then
    echo "Killing existing coordinator session..."
    screen -S "$COORDINATOR_SESSION" -X quit
fi

if screen -list | grep -q "$MONITOR_SESSION"; then
    echo "Killing existing monitor session..."
    screen -S "$MONITOR_SESSION" -X quit
fi

# Make scripts executable
chmod +x scripts/monitor_strategy.py
chmod +x scripts/run_strategy_coordinator.py

# Start the coordinator in a screen session
echo "Starting strategy coordinator in screen session $COORDINATOR_SESSION..."
screen -dmS "$COORDINATOR_SESSION" python scripts/run_strategy_coordinator.py --base BTC --quote USDT --log-level WARNING --config config/strategies.mainnet.yaml --cancel-all

# Wait a moment to let the coordinator initialize
sleep 5

# Start the monitor in a separate screen session
echo "Starting strategy monitor in screen session $MONITOR_SESSION..."
screen -dmS "$MONITOR_SESSION" python scripts/monitor_strategy.py

echo "Both services started in background screen sessions"
echo "To view coordinator logs: screen -r $COORDINATOR_SESSION"
echo "To view monitor logs: screen -r $MONITOR_SESSION"
echo "To detach from a screen: Ctrl+A, then press D" 