#!/usr/bin/env python3
"""
Script to run all the strategy roles for a specific trading pair.
This script will launch multiple instances of the strategy coordinator,
each with a different role (liquidity provider, trade simulator).
"""

import sys
import os
import argparse
import subprocess
import time
import yaml
import signal
import threading

# Add the parent directory to the path so we can import the pylibre module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Global variables to track processes
processes = []
running = True

def load_config(config_path='config/strategies.yaml'):
    """Load configuration from YAML file."""
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"Error loading config from {config_path}: {e}")
        return {}

def signal_handler(sig, frame):
    """Handle Ctrl+C to gracefully stop all processes."""
    global running
    print("\nStopping all strategy processes (this may take a moment)...")
    running = False
    stop_all_processes()

def stop_all_processes():
    """Stop all running processes."""
    for process in processes:
        if process.poll() is None:  # If process is still running
            print(f"Stopping process {process.pid}...")
            try:
                process.terminate()
                # Wait for process to terminate
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                print(f"Process {process.pid} did not terminate gracefully, killing...")
                process.kill()
            except Exception as e:
                print(f"Error stopping process {process.pid}: {e}")

def run_strategy(base, quote, role, dashboard=False, dashboard_port=5000, config_path='config/strategies.yaml'):
    """Run a strategy coordinator with the specified role."""
    cmd = [
        "python3", 
        os.path.join(os.path.dirname(__file__), "run_strategy_coordinator.py"),
        "--base", base,
        "--quote", quote,
        "--role", role,
        "--config", config_path
    ]
    
    if dashboard:
        cmd.append("--dashboard")
        cmd.append("--dashboard-port")
        cmd.append(str(dashboard_port))
    
    print(f"Starting {role} for {base}/{quote}...")
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
        bufsize=1
    )
    
    processes.append(process)
    
    # Start a thread to read and display output
    def output_reader():
        for line in process.stdout:
            print(f"[{role}] {line.strip()}")
    
    thread = threading.Thread(target=output_reader)
    thread.daemon = True
    thread.start()
    
    return process

def main():
    """Main function to run all strategy roles."""
    parser = argparse.ArgumentParser(description='Run all strategy roles for a trading pair')
    
    # Required arguments
    parser.add_argument('--pair', required=True, help='Trading pair (e.g., BTCUSDT, LIBREBTC)')
    
    # Optional arguments
    parser.add_argument('--config', default='config/strategies.yaml', help='Path to config file')
    parser.add_argument('--dashboard', action='store_true', help='Start the monitoring dashboard')
    parser.add_argument('--dashboard-port', type=int, default=5000, help='Port for the dashboard server')
    
    args = parser.parse_args()
    
    # Load configuration
    config = load_config(args.config)
    
    # Parse trading pair
    if args.pair.find('/') != -1:
        base, quote = args.pair.split('/')
    else:
        # Try to split the pair (e.g., BTCUSDT -> BTC and USDT)
        for i in range(len(args.pair) - 1, 0, -1):
            base = args.pair[:i]
            quote = args.pair[i:]
            # Check if this is a valid pair in the config
            if f"{base}{quote}" in config.get('trading_pairs', {}):
                break
        else:
            print(f"Could not parse trading pair: {args.pair}")
            return
    
    pair_key = f"{base}{quote}"
    
    # Check if the pair exists in the config
    if pair_key not in config.get('trading_pairs', {}):
        print(f"Trading pair {pair_key} not found in configuration")
        return
    
    # Check if the pair has account configuration
    if pair_key not in config.get('accounts', {}):
        print(f"No account configuration found for pair {pair_key}")
        return
    
    # Get account configuration for this pair
    pair_accounts = config['accounts'][pair_key]
    
    # Print banner
    print("\n" + "=" * 80)
    print(f"Starting all strategy roles for {base}/{quote}")
    print("=" * 80 + "\n")
    
    # Register signal handler for Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)
    
    # Start liquidity provider (with dashboard)
    if 'liquidity_provider' in pair_accounts:
        lp_process = run_strategy(
            base, 
            quote, 
            'liquidity_provider', 
            dashboard=args.dashboard, 
            dashboard_port=args.dashboard_port,
            config_path=args.config
        )
        
        # Wait a bit to let the liquidity provider start up
        time.sleep(5)
    
    # Start trade simulators
    if 'trade_simulator_1' in pair_accounts:
        ts1_process = run_strategy(
            base, 
            quote, 
            'trade_simulator_1', 
            dashboard=False,
            config_path=args.config
        )
    
    if 'trade_simulator_2' in pair_accounts:
        ts2_process = run_strategy(
            base, 
            quote, 
            'trade_simulator_2', 
            dashboard=False,
            config_path=args.config
        )
    
    print(f"\nAll strategy roles started for {base}/{quote}")
    print("Press Ctrl+C to stop all processes")
    
    # Keep the main thread alive
    while running:
        time.sleep(1)
        
        # Check if any process has terminated
        for process in processes[:]:
            if process.poll() is not None:
                print(f"Process {process.pid} terminated with exit code {process.returncode}")
                processes.remove(process)
        
        # If all processes have terminated, exit
        if not processes:
            print("All processes have terminated, exiting...")
            break

if __name__ == "__main__":
    try:
        main()
    finally:
        stop_all_processes()
