import json
import subprocess
from typing import List, Dict
from concurrent.futures import ThreadPoolExecutor
from ..utils.logger import StrategyLogger, LogLevel
import threading
from queue import Queue

class StrategyManager:
    def __init__(self, config_path: str = "config/manager.json"):
        self.logger = StrategyLogger("StrategyManager")
        self.config = self._load_config(config_path)
        self.processes: Dict[str, subprocess.Popen] = {}
        
    def _load_config(self, config_path: str) -> dict:
        with open(config_path, 'r') as f:
            return json.load(f)
    
    def _monitor_process(self, strategy_config: dict, process: subprocess.Popen) -> None:
        strategy_name = strategy_config['name']
        strategy_logger = StrategyLogger(strategy_name)

        while True:
            output = process.stdout.readline()
            if output:
                strategy_logger.info(output.strip())
            if process.poll() is not None:
                remaining_output = process.stdout.readlines()
                for line in remaining_output:
                    strategy_logger.info(line.strip())
                if process.returncode != 0:
                    self.logger.error(f"Strategy {strategy_name} exited with code {process.returncode}")
                break

    def _start_strategy(self, strategy_config: dict) -> None:
        if not strategy_config.get('enabled', True):
            return
            
        strategy_name = strategy_config['name']
        cmd = [
            "python",
            "-u",
            "scripts/run_strategy.py",
            "--account", strategy_config['account'],
            "--strategy", strategy_name,
            "--base", strategy_config['base'],
            "--quote", strategy_config['quote']
        ]
        
        self.logger.info(f"Running command: {' '.join(cmd)}")
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=1,
                universal_newlines=True,
                text=True
            )
            
            self.processes[strategy_name] = process
            self.logger.info(f"Started strategy: {strategy_name}")

            # Start monitoring thread for this process
            monitor_thread = threading.Thread(
                target=self._monitor_process,
                args=(strategy_config, process),
                daemon=True
            )
            monitor_thread.start()
            
        except Exception as e:
            self.logger.error(f"Failed to start {strategy_name}: {str(e)}")
    
    def start_all(self) -> None:
        """Start all enabled strategies in parallel"""
        with ThreadPoolExecutor() as executor:
            executor.map(self._start_strategy, self.config['strategies'])
    
    def stop_all(self) -> None:
        """Stop all running strategies"""
        for name, process in self.processes.items():
            process.terminate()
            self.logger.info(f"Stopped strategy: {name}")
        self.processes.clear() 