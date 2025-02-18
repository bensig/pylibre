#!/usr/bin/env python3
"""
Test script for pylibre CLI functionality.
Tests various CLI commands by executing them directly.
"""

import subprocess
import json
import sys
import os

def run_command(command):
    """Run a CLI command and return the result."""
    print(f"\nRunning command: {command}")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print("Command output:")
        print(result.stdout)
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Command failed with exit code {e.returncode}")
        print(f"Error output: {e.stderr}")
        return None

def main():
    # Define the base command
    base_cmd = "python -m pylibre.cli --network testnet --verbose"
    
    print("=" * 50)
    print("Testing pylibre CLI functionality")
    print("=" * 50)
    
    # Test 1: Check balance
    print("\n1. Testing 'balance' command")
    run_command(f"{base_cmd} balance bentester BTC")
    run_command(f"{base_cmd} balance bentest3 USDT")
    
    # Test 2: Get table data
    print("\n2. Testing 'table' command")
    run_command(f"{base_cmd} table dex.libre markets dex.libre --limit 5")
    
    # Test 3: Transfer tokens
    print("\n3. Testing 'transfer' command")
    run_command(f"{base_cmd} transfer bentester bentest3 \"0.00001000 BTC\" \"CLI test transfer\"")
    
    # Test 4: Check DEX orderbook
    print("\n4. Testing 'dex orderbook' command")
    run_command(f"{base_cmd} dex orderbook LIBRE BTC")
    
    # Test 5: Get all rows from a table
    print("\n5. Testing 'table-all' command")
    run_command(f"{base_cmd} table-all dex.libre markets dex.libre")
    
    print("\nCLI testing completed!")

if __name__ == "__main__":
    main() 