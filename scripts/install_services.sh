#!/bin/bash
# Script to install Libre trading strategy systemd services

set -e  # Exit on error

# Default installation paths
SYSTEMD_DIR="/etc/systemd/system"
CONFIG_DIR="/opt/libre/pylibre/config"
ENV_FILE="/etc/libre/env"

# Print usage information
function print_usage {
    echo "Usage: $0 [options]"
    echo "Options:"
    echo "  --help                 Show this help message"
    echo "  --systemd-dir DIR      Systemd directory (default: $SYSTEMD_DIR)"
    echo "  --config-dir DIR       Configuration directory (default: $CONFIG_DIR)"
    echo "  --env-file FILE        Environment file (default: $ENV_FILE)"
    echo "  --user USER            User to run services as (default: libre)"
    echo "  --group GROUP          Group to run services as (default: libre)"
    echo "  --install-all          Install all services"
    echo "  --install-coordinator  Install only the coordinator service"
    echo "  --install-dashboard    Install only the dashboard service"
    echo "  --install-price-tracker Install only the price tracker service"
    echo "  --install-maker        Install only the orderbook maker service"
    echo "  --install-animator     Install only the orderbook animator service"
    echo "  --install-simulator    Install only the trade simulator service"
}

# Parse command line arguments
INSTALL_ALL=false
INSTALL_COORDINATOR=false
INSTALL_DASHBOARD=false
INSTALL_PRICE_TRACKER=false
INSTALL_MAKER=false
INSTALL_ANIMATOR=false
INSTALL_SIMULATOR=false
USER="libre"
GROUP="libre"

while [[ $# -gt 0 ]]; do
    case $1 in
        --help)
            print_usage
            exit 0
            ;;
        --systemd-dir)
            SYSTEMD_DIR="$2"
            shift 2
            ;;
        --config-dir)
            CONFIG_DIR="$2"
            shift 2
            ;;
        --env-file)
            ENV_FILE="$2"
            shift 2
            ;;
        --user)
            USER="$2"
            shift 2
            ;;
        --group)
            GROUP="$2"
            shift 2
            ;;
        --install-all)
            INSTALL_ALL=true
            shift
            ;;
        --install-coordinator)
            INSTALL_COORDINATOR=true
            shift
            ;;
        --install-dashboard)
            INSTALL_DASHBOARD=true
            shift
            ;;
        --install-price-tracker)
            INSTALL_PRICE_TRACKER=true
            shift
            ;;
        --install-maker)
            INSTALL_MAKER=true
            shift
            ;;
        --install-animator)
            INSTALL_ANIMATOR=true
            shift
            ;;
        --install-simulator)
            INSTALL_SIMULATOR=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            print_usage
            exit 1
            ;;
    esac
done

# If no specific service was selected, install all
if [[ "$INSTALL_ALL" == "false" && \
      "$INSTALL_COORDINATOR" == "false" && \
      "$INSTALL_DASHBOARD" == "false" && \
      "$INSTALL_PRICE_TRACKER" == "false" && \
      "$INSTALL_MAKER" == "false" && \
      "$INSTALL_ANIMATOR" == "false" && \
      "$INSTALL_SIMULATOR" == "false" ]]; then
    INSTALL_ALL=true
fi

# Check if running as root
if [[ $EUID -ne 0 ]]; then
    echo "This script must be run as root"
    exit 1
fi

# Create directories if they don't exist
mkdir -p "$SYSTEMD_DIR"
mkdir -p "$CONFIG_DIR"
mkdir -p "$(dirname "$ENV_FILE")"

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Function to install a service
function install_service {
    local service_name="$1"
    local service_file="$PROJECT_DIR/systemd/$service_name.service"
    local target_file="$SYSTEMD_DIR/$service_name.service"
    
    echo "Installing $service_name service..."
    
    # Check if service file exists
    if [[ ! -f "$service_file" ]]; then
        echo "Error: Service file $service_file not found"
        return 1
    fi
    
    # Copy service file to systemd directory
    cp "$service_file" "$target_file"
    
    # Update user and group in service file
    sed -i "s/User=libre/User=$USER/g" "$target_file"
    sed -i "s/Group=libre/Group=$GROUP/g" "$target_file"
    
    # Update paths in service file
    sed -i "s|WorkingDirectory=/opt/libre/pylibre|WorkingDirectory=$PROJECT_DIR|g" "$target_file"
    sed -i "s|ExecStart=/opt/libre/pylibre/.venv/bin/python|ExecStart=$PROJECT_DIR/.venv/bin/python|g" "$target_file"
    sed -i "s|CONFIG_PATH=/opt/libre/pylibre/config/strategies.yaml|CONFIG_PATH=$CONFIG_DIR/strategies.yaml|g" "$target_file"
    
    # Uncomment EnvironmentFile if it exists
    if [[ -f "$ENV_FILE" ]]; then
        sed -i "s|#EnvironmentFile=/etc/libre/env|EnvironmentFile=$ENV_FILE|g" "$target_file"
    fi
    
    echo "Service $service_name installed successfully"
}

# Install selected services
if [[ "$INSTALL_ALL" == "true" || "$INSTALL_COORDINATOR" == "true" ]]; then
    install_service "libre-strategy-coordinator"
fi

if [[ "$INSTALL_ALL" == "true" || "$INSTALL_DASHBOARD" == "true" ]]; then
    install_service "libre-dashboard"
fi

if [[ "$INSTALL_ALL" == "true" || "$INSTALL_PRICE_TRACKER" == "true" ]]; then
    install_service "libre-market-price-tracker"
fi

if [[ "$INSTALL_ALL" == "true" || "$INSTALL_MAKER" == "true" ]]; then
    install_service "libre-orderbook-maker"
fi

if [[ "$INSTALL_ALL" == "true" || "$INSTALL_ANIMATOR" == "true" ]]; then
    install_service "libre-orderbook-animator"
fi

if [[ "$INSTALL_ALL" == "true" || "$INSTALL_SIMULATOR" == "true" ]]; then
    install_service "libre-trade-simulator"
fi

# Reload systemd
systemctl daemon-reload

echo "Installation complete. To enable and start services, run:"
echo "  systemctl enable libre-strategy-coordinator.service"
echo "  systemctl start libre-strategy-coordinator.service"
echo ""
echo "Or for individual services:"
echo "  systemctl enable libre-market-price-tracker.service"
echo "  systemctl start libre-market-price-tracker.service"
echo ""
echo "To check service status:"
echo "  systemctl status libre-strategy-coordinator.service"
echo ""
echo "To view logs:"
echo "  journalctl -u libre-strategy-coordinator.service -f" 