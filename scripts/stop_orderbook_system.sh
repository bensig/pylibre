#!/bin/bash
#
# Script to stop the orderbook management system processes

PID_FILE="logs/orderbook_system.pid"

if [ ! -f "$PID_FILE" ]; then
    echo "No PID file found. The orderbook system may not be running."
    
    # Check for any running Python processes related to the orderbook
    PIDS=$(ps aux | grep -E 'oracle_aligned_orderbook.py|order_animator.py' | grep -v grep | awk '{print $2}')
    
    if [ -n "$PIDS" ]; then
        echo "Found possible orderbook system processes:"
        ps aux | grep -E 'oracle_aligned_orderbook.py|order_animator.py' | grep -v grep
        
        echo "Killing these processes..."
        for pid in $PIDS; do
            echo "Killing process $pid"
            kill $pid
        done
    else
        echo "No orderbook system processes found."
    fi
    
    exit 0
fi

echo "Stopping orderbook management system..."
while read -r pid; do
    if ps -p "$pid" > /dev/null; then
        echo "Killing process $pid"
        kill "$pid"
    else
        echo "Process $pid is not running"
    fi
done < "$PID_FILE"

echo "Removing PID file"
rm -f "$PID_FILE"

echo "Orderbook management system stopped" 