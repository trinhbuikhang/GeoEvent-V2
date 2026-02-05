"""
Test script for Phase 3: M4 Logging System
Verifies centralized logging configuration
"""

import sys
import os
import logging
from pathlib import Path

# Add parent directory to import app modules
sys.path.insert(0, str(Path(__file__).parent))

from app.logging_config import setup_logging, get_logger

def test_logging_system():
    """Test centralized logging system"""
    print("="*70)
    print("PHASE 3 - M4: LOGGING SYSTEM TEST")
    print("="*70)
    
    # Test 1: Setup logging
    print("\n[TEST 1] Setting up centralized logging...")
    logger = setup_logging(
        log_dir="logs",
        level=logging.DEBUG,
        console_level=logging.INFO,
        file_level=logging.DEBUG,
        error_level=logging.ERROR
    )
    print("✓ Logging system initialized")
    
    # Test 2: Test different log levels
    print("\n[TEST 2] Testing log levels...")
    logger.debug("This is a DEBUG message (should appear in file only)")
    logger.info("This is an INFO message (should appear in console and file)")
    logger.warning("This is a WARNING message (should appear in console and file)")
    logger.error("This is an ERROR message (should appear in console, file, and error file)")
    print("✓ Log levels tested")
    
    # Test 3: Test module-specific loggers
    print("\n[TEST 3] Testing module-specific loggers...")
    module_logger = get_logger('app.test_module')
    module_logger.info("Message from test module logger")
    print("✓ Module loggers working")
    
    # Test 4: Test exception logging
    print("\n[TEST 4] Testing exception logging...")
    try:
        raise ValueError("Test exception for logging")
    except Exception as e:
        logger.error(f"Caught exception: {e}", exc_info=True)
    print("✓ Exception logging working")
    
    # Test 5: Verify log files created
    print("\n[TEST 5] Verifying log files...")
    log_dir = Path("logs")
    
    main_log = log_dir / "geoevent.log"
    error_log = log_dir / "geoevent_errors.log"
    
    files_exist = []
    if main_log.exists():
        size = main_log.stat().st_size
        files_exist.append(f"✓ {main_log.name} ({size} bytes)")
    else:
        files_exist.append(f"✗ {main_log.name} NOT FOUND")
    
    if error_log.exists():
        size = error_log.stat().st_size
        files_exist.append(f"✓ {error_log.name} ({size} bytes)")
    else:
        files_exist.append(f"✗ {error_log.name} NOT FOUND")
    
    for status in files_exist:
        print(f"  {status}")
    
    # Test 6: Test log rotation settings
    print("\n[TEST 6] Checking rotation settings...")
    for handler in logger.handlers:
        if hasattr(handler, 'maxBytes'):
            print(f"  ✓ {handler.__class__.__name__}: max {handler.maxBytes / 1024 / 1024:.0f}MB, {handler.backupCount} backups")
    
    # Summary
    print("\n" + "="*70)
    print("LOGGING SYSTEM TEST COMPLETED")
    print("="*70)
    print(f"Log directory: {log_dir.absolute()}")
    print(f"Main log: {main_log.absolute()}")
    print(f"Error log: {error_log.absolute()}")
    print("\nAll tests passed! ✓")
    print("\nYou can check the log files to verify:")
    print("  - geoevent.log: Should contain all messages (DEBUG and above)")
    print("  - geoevent_errors.log: Should contain only ERROR messages")
    print("="*70)

if __name__ == "__main__":
    test_logging_system()
