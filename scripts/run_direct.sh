#!/bin/bash
#
# Script to run the orderbook manager directly with output to a file
#

# Create a timestamp for the log file
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
LOGFILE="logs/direct_run_$TIMESTAMP.log"

# Ensure log directory exists
mkdir -p logs

# Kill any existing sessions
screen -S orderbook-manager -X quit > /dev/null 2>&1
screen -S order-animator -X quit > /dev/null 2>&1

# Set up pyenv
eval "$(pyenv init -)"
pyenv shell 3

echo "Running orderbook manager directly..."
echo "Output will be written to $LOGFILE"
echo "Press Ctrl+C to stop"

# Run the script directly with output to a file
python scripts/oracle_aligned_orderbook.py > "$LOGFILE" 2>&1 