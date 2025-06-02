#!/bin/bash
# Script to manage orderbook services (animator and oracle-aligned)

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default action
ACTION=""
USE_SYSTEMD=false
USE_SCREEN=false

# Function to print usage
usage() {
    echo "Usage: $0 [--systemd|--screen] [start|stop|restart|status|logs]"
    echo ""
    echo "Options:"
    echo "  --systemd    Use systemd services (requires sudo)"
    echo "  --screen     Use screen sessions"
    echo ""
    echo "Actions:"
    echo "  start        Start both services"
    echo "  stop         Stop both services"
    echo "  restart      Restart both services"
    echo "  status       Show status of both services"
    echo "  logs         Show logs (systemd only)"
    echo ""
    echo "Examples:"
    echo "  $0 --screen start      # Start in screen sessions"
    echo "  $0 --systemd status    # Check systemd service status"
    exit 1
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --systemd)
            USE_SYSTEMD=true
            shift
            ;;
        --screen)
            USE_SCREEN=true
            shift
            ;;
        start|stop|restart|status|logs)
            ACTION="$1"
            shift
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            usage
            ;;
    esac
done

# Validate arguments
if [ -z "$ACTION" ]; then
    echo -e "${RED}Error: No action specified${NC}"
    usage
fi

if [ "$USE_SYSTEMD" = false ] && [ "$USE_SCREEN" = false ]; then
    echo -e "${RED}Error: Must specify either --systemd or --screen${NC}"
    usage
fi

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Systemd service names
ANIMATOR_SERVICE="libre-order-animator"
ORACLE_SERVICE="libre-oracle-aligned-orderbook"

# Screen session names
ANIMATOR_SCREEN="animator"
ORACLE_SCREEN="oracle-aligned"

# Function to manage systemd services
manage_systemd() {
    case $ACTION in
        start)
            echo -e "${GREEN}Starting orderbook services via systemd...${NC}"
            sudo systemctl start $ANIMATOR_SERVICE
            sudo systemctl start $ORACLE_SERVICE
            echo -e "${GREEN}Services started${NC}"
            ;;
        stop)
            echo -e "${YELLOW}Stopping orderbook services via systemd...${NC}"
            sudo systemctl stop $ANIMATOR_SERVICE
            sudo systemctl stop $ORACLE_SERVICE
            echo -e "${GREEN}Services stopped${NC}"
            ;;
        restart)
            echo -e "${YELLOW}Restarting orderbook services via systemd...${NC}"
            sudo systemctl restart $ANIMATOR_SERVICE
            sudo systemctl restart $ORACLE_SERVICE
            echo -e "${GREEN}Services restarted${NC}"
            ;;
        status)
            echo -e "${GREEN}=== Order Animator Service ===${NC}"
            sudo systemctl status $ANIMATOR_SERVICE --no-pager
            echo ""
            echo -e "${GREEN}=== Oracle Aligned Orderbook Service ===${NC}"
            sudo systemctl status $ORACLE_SERVICE --no-pager
            ;;
        logs)
            echo -e "${GREEN}Showing logs (Ctrl+C to exit)${NC}"
            echo "Following both services..."
            sudo journalctl -u $ANIMATOR_SERVICE -u $ORACLE_SERVICE -f
            ;;
    esac
}

# Function to manage screen sessions
manage_screen() {
    case $ACTION in
        start)
            echo -e "${GREEN}Starting orderbook services in screen sessions...${NC}"
            
            # Check if sessions already exist
            if screen -list | grep -q "$ANIMATOR_SCREEN"; then
                echo -e "${YELLOW}Warning: Animator screen session already exists${NC}"
            else
                echo "Starting animator..."
                cd "$PROJECT_DIR"
                screen -dmS "$ANIMATOR_SCREEN" python3 scripts/order_animator_monitored.py
                echo -e "${GREEN}Animator started in screen session '$ANIMATOR_SCREEN'${NC}"
            fi
            
            if screen -list | grep -q "$ORACLE_SCREEN"; then
                echo -e "${YELLOW}Warning: Oracle screen session already exists${NC}"
            else
                echo "Starting oracle-aligned orderbook..."
                cd "$PROJECT_DIR"
                screen -dmS "$ORACLE_SCREEN" python3 scripts/oracle_aligned_orderbook_monitored.py
                echo -e "${GREEN}Oracle orderbook started in screen session '$ORACLE_SCREEN'${NC}"
            fi
            ;;
        stop)
            echo -e "${YELLOW}Stopping orderbook services in screen sessions...${NC}"
            
            if screen -list | grep -q "$ANIMATOR_SCREEN"; then
                screen -S "$ANIMATOR_SCREEN" -X quit
                echo -e "${GREEN}Animator screen session stopped${NC}"
            else
                echo "Animator screen session not found"
            fi
            
            if screen -list | grep -q "$ORACLE_SCREEN"; then
                screen -S "$ORACLE_SCREEN" -X quit
                echo -e "${GREEN}Oracle screen session stopped${NC}"
            else
                echo "Oracle screen session not found"
            fi
            ;;
        restart)
            manage_screen stop
            sleep 2
            manage_screen start
            ;;
        status)
            echo -e "${GREEN}=== Screen Sessions ===${NC}"
            echo ""
            
            if screen -list | grep -q "$ANIMATOR_SCREEN"; then
                echo -e "${GREEN}✓ Animator${NC} is running in screen session '$ANIMATOR_SCREEN'"
                echo "  To attach: screen -r $ANIMATOR_SCREEN"
            else
                echo -e "${RED}✗ Animator${NC} is not running"
            fi
            
            if screen -list | grep -q "$ORACLE_SCREEN"; then
                echo -e "${GREEN}✓ Oracle Orderbook${NC} is running in screen session '$ORACLE_SCREEN'"
                echo "  To attach: screen -r $ORACLE_SCREEN"
            else
                echo -e "${RED}✗ Oracle Orderbook${NC} is not running"
            fi
            
            echo ""
            echo -e "${YELLOW}All screen sessions:${NC}"
            screen -list || true
            ;;
        logs)
            echo -e "${RED}Logs are not available for screen sessions${NC}"
            echo "To view output, attach to the screen sessions:"
            echo "  screen -r $ANIMATOR_SCREEN"
            echo "  screen -r $ORACLE_SCREEN"
            ;;
    esac
}

# Main execution
if [ "$USE_SYSTEMD" = true ]; then
    manage_systemd
else
    manage_screen
fi

# Show monitoring info
if [ "$ACTION" = "status" ] || [ "$ACTION" = "start" ]; then
    echo ""
    echo -e "${GREEN}=== Monitoring ===${NC}"
    echo "Dashboard URL: http://localhost:5100"
    echo "Monitor files:"
    echo "  - $PROJECT_DIR/monitor_data/strategies.json"
    echo "  - $PROJECT_DIR/monitor_data/metrics.json"
    echo "  - $PROJECT_DIR/monitor_data/last_update.json"
fi