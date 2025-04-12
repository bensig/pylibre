#!/bin/bash
# Script to check the status of strategy services

# Define screen session names
COORDINATOR_SESSION="strategy_coordinator_mainnet"
MONITOR_SESSION="strategy_monitor_mainnet"

# Function to check if a screen session exists
check_session() {
    local session_name="$1"
    if screen -list | grep -q "$session_name"; then
        echo "✅ $session_name is running"
        return 0
    else
        echo "❌ $session_name is NOT running"
        return 1
    fi
}

# Print header
echo "===== Strategy Services Status ====="
echo "Time: $(date)"
echo

# Check each service
check_session "$COORDINATOR_SESSION"
check_session "$MONITOR_SESSION"

echo
echo "===== Recent Logs ====="

# Show recent logs if sessions are running
if screen -list | grep -q "$COORDINATOR_SESSION"; then
    echo
    echo "--- Last 5 lines from coordinator ---"
    screen -S "$COORDINATOR_SESSION" -X hardcopy /tmp/coordinator_log.txt
    tail -5 /tmp/coordinator_log.txt 2>/dev/null || echo "No logs available"
fi

if screen -list | grep -q "$MONITOR_SESSION"; then
    echo
    echo "--- Last 5 lines from monitor ---"
    screen -S "$MONITOR_SESSION" -X hardcopy /tmp/monitor_log.txt
    tail -5 /tmp/monitor_log.txt 2>/dev/null || echo "No logs available"
fi

echo
echo "===== Commands ====="
echo "View coordinator: screen -r $COORDINATOR_SESSION"
echo "View monitor:     screen -r $MONITOR_SESSION"
echo "Restart services: ./start_coordinator.sh"
echo "Detach from screen: Ctrl+A, then press D" 