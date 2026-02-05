"""
Centralized logging configuration for GeoEvent Application.

This module provides a standardized logging setup with:
- Console output for INFO and above
- Rotating file handler for DEBUG and above (10MB, 5 backups)
- Separate error log for ERROR and CRITICAL
- Formatted messages with timestamp, file, line number, function name

Usage:
    from app.logging_config import setup_logging
    logger = setup_logging()
    
    # Or get logger for specific module
    import logging
    logger = logging.getLogger(__name__)
"""

import logging
import logging.handlers
from pathlib import Path
from typing import Optional


def setup_logging(
    log_dir: str = "logs",
    level: int = logging.INFO,
    console_level: int = logging.INFO,
    file_level: int = logging.DEBUG,
    error_level: int = logging.ERROR
) -> logging.Logger:
    """
    Setup centralized logging configuration.
    
    Args:
        log_dir: Directory for log files (created if not exists)
        level: Root logger level (default: INFO)
        console_level: Console handler level (default: INFO)
        file_level: Main file handler level (default: DEBUG)
        error_level: Error file handler level (default: ERROR)
        
    Returns:
        logging.Logger: Configured root logger
        
    Example:
        >>> logger = setup_logging()
        >>> logger.info("Application started")
        >>> logging.getLogger(__name__).debug("Debug message")
    """
    
    # Create logs directory
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        fmt='%(asctime)s - %(name)s - %(levelname)s - '
            '%(filename)s:%(lineno)d - %(funcName)s() - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    simple_formatter = logging.Formatter(
        fmt='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Console handler - INFO and above, simple format
    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_level)
    console_handler.setFormatter(simple_formatter)
    
    # Main file handler with rotation - DEBUG and above, detailed format
    file_handler = logging.handlers.RotatingFileHandler(
        filename=log_path / 'geoevent.log',
        maxBytes=10 * 1024 * 1024,  # 10MB per file
        backupCount=5,  # Keep 5 backup files
        encoding='utf-8'
    )
    file_handler.setLevel(file_level)
    file_handler.setFormatter(detailed_formatter)
    
    # Error file handler - ERROR and above only, detailed format
    error_handler = logging.handlers.RotatingFileHandler(
        filename=log_path / 'geoevent_errors.log',
        maxBytes=5 * 1024 * 1024,  # 5MB per file
        backupCount=3,  # Keep 3 backup files
        encoding='utf-8'
    )
    error_handler.setLevel(error_level)
    error_handler.setFormatter(detailed_formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Remove existing handlers to avoid duplicates
    root_logger.handlers.clear()
    
    # Add handlers
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(error_handler)
    
    # Suppress verbose third-party loggers
    logging.getLogger('PIL').setLevel(logging.WARNING)
    logging.getLogger('PyQt6').setLevel(logging.WARNING)
    logging.getLogger('matplotlib').setLevel(logging.WARNING)
    
    # Log startup message
    root_logger.info("="*60)
    root_logger.info("GeoEvent Application - Logging System Initialized")
    root_logger.info(f"Log directory: {log_path.absolute()}")
    root_logger.info(f"Console level: {logging.getLevelName(console_level)}")
    root_logger.info(f"File level: {logging.getLevelName(file_level)}")
    root_logger.info(f"Error level: {logging.getLevelName(error_level)}")
    root_logger.info("="*60)
    
    return root_logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Get a logger instance for a specific module.
    
    Args:
        name: Logger name (usually __name__). If None, returns root logger.
        
    Returns:
        logging.Logger: Logger instance
        
    Example:
        >>> logger = get_logger(__name__)
        >>> logger.debug("Debug message from my module")
    """
    return logging.getLogger(name)


# Convenience function for migration from print() statements
def log_print(message: str, level: str = 'info'):
    """
    Temporary convenience function to replace print() statements.
    
    This function helps migrate from print() to logging during refactoring.
    Use get_logger(__name__) for proper module-level logging instead.
    
    Args:
        message: Message to log
        level: Log level ('debug', 'info', 'warning', 'error', 'critical')
        
    Example:
        >>> # Instead of: print(f"Error: {e}")
        >>> log_print(f"Error: {e}", 'error')
    """
    logger = logging.getLogger('app')
    level_map = {
        'debug': logger.debug,
        'info': logger.info,
        'warning': logger.warning,
        'error': logger.error,
        'critical': logger.critical
    }
    log_func = level_map.get(level.lower(), logger.info)
    log_func(message)
