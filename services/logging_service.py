# Copyright (C) 2026 BPS
# This file is part of BPS Fishing Macro.
#
# V5: Services Module - Logging Service
# Pure extraction from main file - NO behavior changes

import logging
import os
import sys

class LoggingService:
    """
    Centralized logging service
    
    EXACT COPY of logging setup from main file - NO behavior changes
    """
    
    def __init__(self, log_file: str = None, log_level: int = logging.INFO):
        """
        Initialize logging service
        
        Args:
            log_file: Path to log file
            log_level: Logging level (default: INFO)
        """
        if log_file is None:
            # Default log file location (same logic as main)
            log_file = os.path.join(
                os.path.dirname(os.path.abspath(__file__)) if not getattr(sys, 'frozen', False) 
                else os.path.dirname(sys.executable), 
                'fishing_macro.log'
            )
        
        self.log_file = log_file
        self.log_level = log_level
        self.logger = None
        self._setup_logging()
    
    def _setup_logging(self):
        """Setup logging with file and console handlers"""
        logging.basicConfig(
            level=self.log_level,
            format='%(asctime)s | %(levelname)s | %(message)s',
            handlers=[
                logging.FileHandler(self.log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('FishingMacro')
    
    def get_logger(self):
        """Get the logger instance"""
        return self.logger
    
    def info(self, message: str):
        """Log info message"""
        if self.logger:
            self.logger.info(message)
    
    def warning(self, message: str):
        """Log warning message"""
        if self.logger:
            self.logger.warning(message)
    
    def error(self, message: str, exc_info: bool = False):
        """Log error message"""
        if self.logger:
            self.logger.error(message, exc_info=exc_info)
    
    def debug(self, message: str):
        """Log debug message"""
        if self.logger:
            self.logger.debug(message)
