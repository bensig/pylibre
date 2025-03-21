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
    def __init__(self, strategy_name: str, level: LogLevel = LogLevel.INFO, 
                 console_level: LogLevel = None):
        # Create logs directory if it doesn't exist
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        
        # Set default console level if not provided
        if console_level is None:
            console_level = level
        
        # Create a logger
        self.logger = logging.getLogger(f"pylibre.{strategy_name}")
        self.logger.setLevel(min(level.value, console_level.value))  # Set to lowest level
        
        # Prevent propagation to avoid duplicate logs
        self.logger.propagate = False
        
        # Clear any existing handlers to prevent duplicates
        if self.logger.handlers:
            self.logger.handlers.clear()
            
        # File handler - detailed logs
        timestamp = datetime.now().strftime("%Y%m%d")
        file_handler = logging.FileHandler(
            f"{log_dir}/{strategy_name}_{timestamp}.log"
        )
        file_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)s | %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        file_handler.setLevel(level.value)
        self.logger.addHandler(file_handler)
        
        # Console handler - more concise logs
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter(
            '%(asctime)s | %(name)s | %(levelname)s | %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        console_handler.setLevel(console_level.value)  # Higher level for console
        self.logger.addHandler(console_handler)
    
    def debug(self, msg: str) -> None:
        self.logger.debug(msg)
        
    def info(self, msg: str) -> None:
        self.logger.info(msg)
        
    def warning(self, msg: str) -> None:
        self.logger.warning(msg)
        
    def error(self, msg: str) -> None:
        self.logger.error(msg)
