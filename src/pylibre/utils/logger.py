import logging
from typing import Optional
from enum import Enum

class LogLevel(Enum):
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR

class StrategyLogger:
    def __init__(self, strategy_name: str, level: LogLevel = LogLevel.INFO):
        self.logger = logging.getLogger(f"pylibre.{strategy_name}")
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(message)s', 
                                    datefmt='%H:%M:%S')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(level.value)
        
    def debug(self, msg: str) -> None:
        self.logger.debug(msg)
        
    def info(self, msg: str) -> None:
        self.logger.info(msg)
        
    def warning(self, msg: str) -> None:
        self.logger.warning(msg)
        
    def error(self, msg: str) -> None:
        self.logger.error(msg)
