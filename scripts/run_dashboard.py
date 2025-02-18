#!/usr/bin/env python3
"""
Script to run the strategy monitoring dashboard.
"""

import sys
import os
import argparse
import time
import signal

# Add the parent directory to the path so we can import the pylibre module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.pylibre.monitoring.dashboard import start_dashboard, stop_dashboard, get_monitor

# Global variable to track if the dashboard is running
running = True

def signal_handler(sig, frame):
    """Handle Ctrl+C to gracefully stop the dashboard."""
    global running
    print("\nStopping dashboard (this may take a moment)...")
    running = False

def main():
    """Main function to run the dashboard."""
    parser = argparse.ArgumentParser(description='Run the strategy monitoring dashboard')
    
    # Optional arguments
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind the dashboard server to')
    parser.add_argument('--port', type=int, default=5000, help='Port to run the dashboard server on')
    parser.add_argument('--data-dir', default='monitor_data', help='Directory to store monitoring data')
    
    args = parser.parse_args()
    
    # Register signal handler for Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)
    
    # Start the dashboard
    print(f"Starting dashboard on http://{args.host}:{args.port}")
    dashboard = start_dashboard(host=args.host, port=args.port)
    
    # Keep the main thread alive
    try:
        while running:
            time.sleep(1)
    finally:
        # Stop the dashboard
        print("Stopping dashboard...")
        stop_dashboard()
        print("Dashboard stopped")

if __name__ == "__main__":
    main() 