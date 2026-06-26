"""
Project Sentinel - Setup Verification Checklist

Run this script to verify the installation is correct:
    python verify_setup.py
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

def verify_imports():
    """Verify all core modules can be imported."""
    print("\n" + "="*80)
    print("VERIFYING IMPORTS")
    print("="*80)
    
    checks = []
    
    try:
        from config import get_config, initialize_config
        print("✅ config.settings - Configuration system")
        checks.append(True)
    except Exception as e:
        print(f"❌ config.settings - {e}")
        checks.append(False)
    
    try:
        from utils import get_logger, initialize_logging
        print("✅ utils.logger - Logging system")
        checks.append(True)
    except Exception as e:
        print(f"❌ utils.logger - {e}")
        checks.append(False)
    
    try:
        from utils.system import SystemInfo, PathManager, ResourceMonitor
        print("✅ utils.system - System utilities")
        checks.append(True)
    except Exception as e:
        print(f"❌ utils.system - {e}")
        checks.append(False)
    
    try:
        from database import get_database, initialize_database
        print("✅ database.models - Database layer")
        checks.append(True)
    except Exception as e:
        print(f"❌ database.models - {e}")
        checks.append(False)
    
    return all(checks)


def verify_configuration():
    """Verify configuration system works."""
    print("\n" + "="*80)
    print("VERIFYING CONFIGURATION")
    print("="*80)
    
    try:
        from config import initialize_config
        
        config = initialize_config()
        
        print(f"✅ Application: {config.app_name} v{config.version}")
        print(f"✅ Camera FPS: {config.camera.fps}")
        print(f"✅ Motion Sensitivity: {config.motion.sensitivity}")
        print(f"✅ Recording: {config.recording.post_motion_seconds}s post-motion")
        print(f"✅ Retention: {config.storage.retention_days} days")
        print(f"✅ Database: {config.database.path}")
        
        return True
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        return False


def verify_logging():
    """Verify logging system works."""
    print("\n" + "="*80)
    print("VERIFYING LOGGING")
    print("="*80)
    
    try:
        from utils import initialize_logging, get_logger
        
        initialize_logging("logs", "json")
        logger = get_logger("verify_setup", level="INFO")
        
        logger.info("Test log message from verification script")
        logger.warning("Test warning message")
        
        logs_dir = Path("logs")
        log_files = list(logs_dir.glob("*.log"))
        
        print(f"✅ Logging initialized to: {logs_dir.absolute()}")
        print(f"✅ Log files created: {len(log_files)}")
        for log_file in log_files:
            print(f"   - {log_file.name}")
        
        return True
    except Exception as e:
        print(f"❌ Logging error: {e}")
        return False


def verify_database():
    """Verify database system works."""
    print("\n" + "="*80)
    print("VERIFYING DATABASE")
    print("="*80)
    
    try:
        from database import initialize_database
        
        db = initialize_database("data/test_sentinel.db", echo=False)
        
        # Check health
        health = db.health_check()
        
        if health:
            print(f"✅ Database initialized: {db.db_path.absolute()}")
            print("✅ Database health check: PASSED")
            
            # Verify tables exist
            from database import (
                Application, Camera, MotionEvent, Recording,
                SystemMetric, ApplicationLog, Setting
            )
            print("✅ All database tables defined")
            
            return True
        else:
            print("❌ Database health check failed")
            return False
            
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False


def verify_system_info():
    """Verify system information gathering."""
    print("\n" + "="*80)
    print("VERIFYING SYSTEM INFORMATION")
    print("="*80)
    
    try:
        from utils.system import SystemInfo, ResourceMonitor
        
        system_info = SystemInfo.get_system_info()
        
        print(f"✅ Platform: {system_info['platform']}")
        print(f"✅ Architecture: {system_info['architecture']}")
        print(f"✅ CPU Cores: {system_info['cpu']['cpu_count']}")
        print(f"✅ Memory: {system_info['memory']['total_gb']:.1f} GB")
        print(f"✅ Disk: {system_info['disk']['total_gb']:.1f} GB")
        
        # Check resource health
        healthy, status = ResourceMonitor.full_health_check()
        
        print(f"\n✅ Resource Health Check:")
        print(f"   {status['cpu_status']}")
        print(f"   {status['memory_status']}")
        print(f"   {status['disk_status']}")
        
        return True
    except Exception as e:
        print(f"❌ System info error: {e}")
        return False


def verify_directory_structure():
    """Verify directory structure."""
    print("\n" + "="*80)
    print("VERIFYING DIRECTORY STRUCTURE")
    print("="*80)
    
    required_dirs = [
        "config", "camera", "motion", "recording", "streaming",
        "web", "database", "security", "ai", "alerts", "scheduler",
        "storage", "utils", "tests", "docs"
    ]
    
    all_exist = True
    
    for dir_name in required_dirs:
        dir_path = PROJECT_ROOT / dir_name
        if dir_path.exists() and dir_path.is_dir():
            print(f"✅ {dir_name}/")
        else:
            print(f"❌ {dir_name}/ - MISSING")
            all_exist = False
    
    return all_exist


def main():
    """Run all verification checks."""
    print("\n")
    print("╔" + "="*78 + "╗")
    print("║" + " "*78 + "║")
    print("║" + "PROJECT SENTINEL - SETUP VERIFICATION".center(78) + "║")
    print("║" + " "*78 + "║")
    print("╚" + "="*78 + "╝")
    
    results = {}
    
    results["Directory Structure"] = verify_directory_structure()
    results["Imports"] = verify_imports()
    results["Configuration"] = verify_configuration()
    results["Logging"] = verify_logging()
    results["Database"] = verify_database()
    results["System Info"] = verify_system_info()
    
    # Summary
    print("\n" + "="*80)
    print("VERIFICATION SUMMARY")
    print("="*80)
    
    for check, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{check:<30} {status}")
    
    all_passed = all(results.values())
    
    print("\n" + "="*80)
    if all_passed:
        print("✅ ALL CHECKS PASSED - Setup is complete!")
        print("\nNext steps:")
        print("1. Review config/settings.json for your setup")
        print("2. Run: python app.py        (development)")
        print("3. Or: python watchdog.py    (production)")
    else:
        print("❌ SOME CHECKS FAILED - Please review errors above")
    print("="*80 + "\n")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
