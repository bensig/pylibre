import logging
from typing import Dict, Any, Optional
import asyncio
from pathlib import Path
from datetime import datetime
import subprocess
import sys
from ..manager.config_manager import ConfigManager
from ..utils.logger import StrategyLogger, LogLevel
import os
import signal

class TradingManager:
    """Manages trading strategies and their execution."""
    
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
        self.logger = StrategyLogger("TradingManager", LogLevel.INFO)
        self.strategies = {}
        self.running = True
        
    async def start_strategy(self, strategy_name: str, config: Dict[str, Any]):
        """Start a trading strategy."""
        strategy_logger = self._setup_logging(strategy_name)
        
        strategy_logger.info(f"Starting strategy: {strategy_name}")
        
        # Start strategy process for each account
        processes = []
        for account in config["accounts"]:
            account_config = self.config_manager.get_account_config(account)
            strategy_logger.info(f"Starting {strategy_name} for account {account}")
            
            # Build command with only the required parameters
            cmd = [
                sys.executable,
                "-u",  # Unbuffered output
                "scripts/run_strategy.py",
                "--account", account,
                "--strategy", strategy_name,  # Use the actual strategy name
                "--base", "BTC",
                "--quote", "USDT"
            ]
            
            strategy_logger.info(f"Running command: {' '.join(cmd)}")
            
            # Start the process
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            processes.append(process)
            
        # Store strategy info
        self.strategies[strategy_name] = {
            "config": config,
            "status": "running",
            "logger": strategy_logger,
            "processes": processes
        }
        
        # Monitor processes
        while self.running:
            for process in processes:
                # Read and log output
                while True:
                    output = process.stdout.readline()
                    if not output:
                        break
                        
                    # Log the output
                    strategy_logger.info(output.strip())
                    
                # Check if process is still running
                if process.poll() is not None:
                    strategy_logger.error(f"Strategy process exited with code {process.returncode}")
                    return
                    
            await asyncio.sleep(0.1)  # Short sleep to prevent CPU spinning
        
    async def stop_strategy(self, strategy_name: str):
        """Stop a trading strategy."""
        if strategy_name in self.strategies:
            strategy_info = self.strategies[strategy_name]
            strategy_info["logger"].info(f"Stopping strategy: {strategy_name}")
            
            # Stop all processes
            for process in strategy_info["processes"]:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    
            strategy_info["status"] = "stopped"
        
    async def start_all(self, strategy_group: str):
        """Start all strategies in a strategy group."""
        group_config = self.config_manager.get_strategy_group(strategy_group)
        if not group_config:
            self.logger.error(f"Strategy group not found: {strategy_group}")
            return
            
        print(f"\n🚀 Starting strategy group: {strategy_group}")
        
        # Start all processes simultaneously
        processes = []
        for strategy in group_config["strategies"]:
            for account in strategy["accounts"]:
                strategy_id = f"{strategy['name']}_{account}"
                
                cmd = [
                    sys.executable,
                    "-u",  # Unbuffered output
                    str(Path("scripts/run_strategy.py").absolute()),
                    "--account", account,
                    "--strategy", strategy["name"],
                    "--base", "BTC",
                    "--quote", "USDT"
                ]
                
                try:
                    process = subprocess.Popen(
                        cmd,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.PIPE,
                        env=os.environ.copy()
                    )
                    
                    print(f"📊 Started {strategy_id} (PID: {process.pid})")
                    self.logger.info(f"Process started with PID: {process.pid}")
                    
                    # Get current log file size to only show new entries
                    log_file = f"logs/{strategy_id}_{datetime.now().strftime('%Y%m%d')}.log"
                    try:
                        with open(log_file, 'r') as f:
                            f.seek(0, 2)  # Seek to end
                            last_position = f.tell()
                    except FileNotFoundError:
                        last_position = 0
                    
                    processes.append({
                        "name": strategy["name"],
                        "account": account,
                        "process": process,
                        "active": True,
                        "log_file": log_file,
                        "last_position": last_position  # Track position from startup
                    })
                    
                except Exception as e:
                    self.logger.error(f"Failed to start process: {e}")
                    print(f"❌ Failed to start {strategy_id}: {e}")
        
        if not processes:
            self.logger.error("No processes were started successfully!")
            return
            
        print("\n📈 Trading activity:")
        print("=" * 80)
        
        # Monitor processes and their log files
        try:
            while self.running and any(p["active"] for p in processes):
                for proc in processes:
                    if not proc["active"]:
                        continue
                        
                    # Read and display new log entries
                    try:
                        with open(proc["log_file"], 'r') as f:
                            f.seek(proc["last_position"])
                            new_lines = f.readlines()
                            if new_lines:
                                proc["last_position"] = f.tell()
                                for line in new_lines:
                                    # Show all INFO lines that contain emojis
                                    if "INFO" in line and any(emoji in line for emoji in ['💸', '💰', '🚀', '✨']):
                                        # Strip timestamp and log level for cleaner output
                                        clean_line = line.split(" | ")[-1].strip()
                                        # Remove duplicate account name
                                        clean_line = clean_line.replace(f"{proc['account']}: ", "")
                                        print(f"{proc['account']}: {clean_line}")
                                    
                    except FileNotFoundError:
                        pass
                        
                    # Check if process has exited
                    if proc["process"].poll() is not None:
                        print(f"\n❌ Strategy {proc['name']} for {proc['account']} exited")
                        proc["active"] = False
                        
                await asyncio.sleep(0.1)
                
        except asyncio.CancelledError:
            print("\n👋 Shutting down strategies...")
        finally:
            print("\nCleaning up processes...")
            for proc in processes:
                if proc["process"].poll() is None:
                    proc["process"].terminate()
                    try:
                        proc["process"].wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        proc["process"].kill()
            print("✨ All processes stopped")
        
    async def stop_all(self):
        """Stop all running strategies."""
        self.running = False
        tasks = []
        for strategy_name in list(self.strategies.keys()):
            task = asyncio.create_task(self.stop_strategy(strategy_name))
            tasks.append(task)
        await asyncio.gather(*tasks) 