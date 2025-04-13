#!/bin/bash
# Run both coordinator and price watcher in a tmux session

# Parse command-line arguments
DRY_RUN=0
while [[ $# -gt 0 ]]; do
  case $1 in
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    *)
      echo "Unknown option: $1"
      echo "Usage: $0 [--dry-run]"
      exit 1
      ;;
  esac
done

# Ensure tmux is installed
if ! command -v tmux &> /dev/null; then
    echo "tmux is not installed. Please install it first."
    exit 1
fi

# Kill any existing session with the same name
tmux kill-session -t price_watch 2>/dev/null

# Create a new session
tmux new-session -d -s price_watch

# Split the window horizontally
tmux split-window -h -t price_watch

# Build the command based on whether we're in dry-run mode
if [ $DRY_RUN -eq 1 ]; then
    echo "Running in DRY-RUN mode (no real orders will be placed)"
    COORDINATOR_CMD="cd $(pwd) && pyenv shell 3 && python scripts/run_strategy_coordinator.py --base BTC --quote USDT --config config/strategies.mainnet.yaml --log-level INFO --dry-run"
else
    echo "Running in REAL mode (LIVE ORDERS WILL BE PLACED)"
    COORDINATOR_CMD="cd $(pwd) && pyenv shell 3 && python scripts/run_strategy_coordinator.py --base BTC --quote USDT --config config/strategies.mainnet.yaml --log-level INFO"
fi

# Run coordinator in the left pane
tmux send-keys -t price_watch:0.0 "$COORDINATOR_CMD" C-m

# Wait a moment for the coordinator to start
sleep 2

# Run price watcher in the right pane
tmux send-keys -t price_watch:0.1 "cd $(pwd) && pyenv shell 3 && python scripts/check_price.py --base BTC --quote USDT --watch --interval 2" C-m

# Attach to the session
tmux attach-session -t price_watch

# When the user detaches, clean up
echo "Shutting down price watch session..."
tmux kill-session -t price_watch 