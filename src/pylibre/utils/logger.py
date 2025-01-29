import logging
from typing import Optional
from enum import Enum
import os
from datetime import datetime

class LogLevel(Enum):
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR

class StrategyLogger:
    def __init__(self, strategy_name: str, level: LogLevel = LogLevel.INFO):
        # Create logs directory if it doesn't exist
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        
        # Create a logger
        self.logger = logging.getLogger(f"pylibre.{strategy_name}")
        self.logger.setLevel(level.value)
        
        # Prevent duplicate handlers
        if not self.logger.handlers:
            # File handler - detailed logging
            timestamp = datetime.now().strftime("%Y%m%d")
            file_handler = logging.FileHandler(
                f"{log_dir}/{strategy_name}_{timestamp}.log"
            )
            file_formatter = logging.Formatter(
                '%(asctime)s | %(levelname)s | %(message)s'
            )
            file_handler.setFormatter(file_formatter)
            file_handler.setLevel(logging.DEBUG)  # Log everything to file
            self.logger.addHandler(file_handler)
            
            # Console handler - minimal logging
            console_handler = logging.StreamHandler()
            console_formatter = logging.Formatter('%(message)s')
            console_handler.setFormatter(console_formatter)
            console_handler.setLevel(logging.WARNING)  # Only warnings and errors to console
            self.logger.addHandler(console_handler)
        
    def debug(self, msg: str) -> None:
        self.logger.debug(msg)
        
    def info(self, msg: str) -> None:
        self.logger.info(msg)
        
    def warning(self, msg: str) -> None:
        self.logger.warning(msg)
        
    def error(self, msg: str) -> None:
        self.logger.error(msg)

    def trade(self, msg: str) -> None:
        """Special method for trade-related messages - goes to both console and file"""
        self.logger.info(msg)
        print(msg)  # Always show trades in console
