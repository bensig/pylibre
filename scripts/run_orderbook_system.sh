#!/bin/bash
#
# Script to run the orderbook management system
# This runs both the Oracle-aligned orderbook manager and the order animator
# as background processes with logging

# Configuration
LOGDIR="logs"
MANAGER_SCRIPT="scripts/oracle_aligned_orderbook.py"
ANIMATOR_SCRIPT="scripts/order_animator.py"
MANAGER_LOG="$LOGDIR/orderbook_manager.log"
ANIMATOR_LOG="$LOGDIR/order_animator.log"
PID_FILE="$LOGDIR/orderbook_system.pid"

# Create logs directory if it doesn't exist
mkdir -p "$LOGDIR"

# Check if running in test mode
TEST_MODE=0
if [[ "$1" == "--test" ]]; then
    TEST_MODE=1
    echo "Running in test mode (one cycle only)"
fi

# Check if we have existing processes running
if [ -f "$PID_FILE" ]; then
    echo "Existing orderbook system processes found. Stopping them..."
    while read -r pid; do
        if ps -p "$pid" > /dev/null; then
            echo "Killing process $pid"
            kill "$pid"
            sleep 1
        else
            echo "Process $pid is not running"
        fi
    done < "$PID_FILE"
    rm -f "$PID_FILE"
    echo "Old processes stopped"
    sleep 2
fi

# Create new PID file
touch "$PID_FILE"

echo "Starting orderbook management system..."

# Start the Oracle-aligned orderbook manager
echo "Starting Oracle-aligned orderbook manager..."
if [ $TEST_MODE -eq 1 ]; then
    chmod +x "$MANAGER_SCRIPT"
    nohup python3 "$MANAGER_SCRIPT" --once > "$MANAGER_LOG" 2>&1 &
else
    chmod +x "$MANAGER_SCRIPT"
    nohup python3 "$MANAGER_SCRIPT" > "$MANAGER_LOG" 2>&1 &
fi
MANAGER_PID=$!
echo "Oracle-aligned orderbook manager started with PID $MANAGER_PID"
echo $MANAGER_PID >> "$PID_FILE"

# Brief pause to allow manager to start
sleep 2

# Start the order animator
echo "Starting order animator..."
if [ $TEST_MODE -eq 1 ]; then
    chmod +x "$ANIMATOR_SCRIPT"
    nohup python3 "$ANIMATOR_SCRIPT" --once > "$ANIMATOR_LOG" 2>&1 &
else
    chmod +x "$ANIMATOR_SCRIPT"
    nohup python3 "$ANIMATOR_SCRIPT" --min-orders 2 --max-orders 8 --interval 5 > "$ANIMATOR_LOG" 2>&1 &
fi
ANIMATOR_PID=$!
echo "Order animator started with PID $ANIMATOR_PID"
echo $ANIMATOR_PID >> "$PID_FILE"

echo ""
echo "Orderbook management system started successfully"
echo "Manager PID: $MANAGER_PID (logs: $MANAGER_LOG)"
echo "Animator PID: $ANIMATOR_PID (logs: $ANIMATOR_LOG)"
echo ""
echo "To check the running processes, use:"
echo "ps -p $MANAGER_PID $ANIMATOR_PID"
echo ""
echo "To view the logs in real time, use:"
echo "tail -f $MANAGER_LOG"
echo "tail -f $ANIMATOR_LOG"
echo ""
echo "To stop the system, use:"
echo "./scripts/stop_orderbook_system.sh" 