#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path
import subprocess
import signal
from pylibre.manager.config_manager import ConfigManager
from pylibre.utils.logger import StrategyLogger, LogLevel

def main():
    parser = argparse.ArgumentParser(description='Run multiple trading strategies')
    parser.add_argument('strategy_group', help='Strategy group to run')
    parser.add_argument('--config', default='config/config.yaml', help='Path to config file')
    args = parser.parse_args()

    logger = StrategyLogger("TradingManager", level=LogLevel.INFO)
    processes = []

    try:
        # Load configuration
        config_manager = ConfigManager(args.config)
        group_config = config_manager.get_strategy_group(args.strategy_group)
        
        if not group_config:
            logger.error(f"Strategy group {args.strategy_group} not found")
            sys.exit(1)

        # Start each strategy using run_strategy.py
        for pair in group_config["pairs"]:
            base_symbol, quote_symbol = pair.split("/")
            
            for strategy_config in group_config["strategies"]:
                account = strategy_config["account"]
                strategy_name = strategy_config["name"]
                
                cmd = [
                    sys.executable,
                    "scripts/run_strategy.py",
                    "--account", account,
                    "--strategy", strategy_name,
                    "--base", base_symbol,
                    "--quote", quote_symbol,
                    "--config", args.config
                ]
                
                process = subprocess.Popen(cmd)
                processes.append(process)
                logger.info(f"Started {strategy_name} for {account} on {pair}")

        def handle_shutdown(signum, frame):
            logger.info("Shutting down all strategies...")
            for p in processes:
                p.terminate()
            sys.exit(0)

        signal.signal(signal.SIGINT, handle_shutdown)
        signal.signal(signal.SIGTERM, handle_shutdown)

        # Wait for all processes
        for p in processes:
            p.wait()

    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
        for p in processes:
            p.terminate()
    except Exception as e:
        logger.error(f"Error: {e}")
        for p in processes:
            p.terminate()
        sys.exit(1)

if __name__ == "__main__":
    main()