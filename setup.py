"""
Setup Script
Initialize the trading bot environment
"""
import os
import sys
import subprocess


def create_directories():
    """Create necessary directories"""
    directories = [
        "logs",
        "data",
        "config",
        "src",
        "backtesting",
        "tests",
    ]

    print("Creating directories...")
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"  ✓ {directory}/")


def create_env_file():
    """Create .env file if it doesn't exist"""
    if os.path.exists(".env"):
        print("\n.env file already exists. Skipping...")
        return

    print("\nCreating .env file...")
    with open(".env", "w") as f:
        f.write("""# Zerodha API Credentials
ZERODHA_API_KEY=your_api_key_here
ZERODHA_API_SECRET=your_api_secret_here
ZERODHA_USER_ID=your_user_id_here

# Telegram Notifications (Optional)
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

# Trading Mode
TRADING_MODE=paper

# Database
DATABASE_URL=sqlite:///data/trading.db

# Logging
LOG_LEVEL=INFO
""")
    print("  ✓ .env file created")
    print("\n⚠️  Please edit .env and add your credentials!")


def install_dependencies():
    """Install Python dependencies"""
    print("\nInstalling dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("  ✓ Dependencies installed successfully")
    except subprocess.CalledProcessError as e:
        print(f"  ✗ Error installing dependencies: {e}")
        return False
    return True


def initialize_database():
    """Initialize database"""
    print("\nInitializing database...")
    try:
        from src.database.db_manager import DatabaseManager

        db = DatabaseManager()
        print("  ✓ Database initialized")
        return True
    except Exception as e:
        print(f"  ✗ Error initializing database: {e}")
        return False


def run_tests():
    """Run basic tests"""
    print("\nRunning basic tests...")
    try:
        # Test imports
        from src.data.indicators import IndicatorEngine
        from src.brokers.zerodha_broker import ZerodhaBroker
        from src.utils.logger import setup_logger

        print("  ✓ All imports successful")
        return True
    except Exception as e:
        print(f"  ✗ Error in tests: {e}")
        return False


def main():
    """Main setup function"""
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║         OPTIONS TRADING BOT - SETUP                       ║
    ╚═══════════════════════════════════════════════════════════╝
    """)

    # Step 1: Create directories
    create_directories()

    # Step 2: Create .env file
    create_env_file()

    # Step 3: Install dependencies
    if not install_dependencies():
        print("\n❌ Setup failed at dependency installation")
        return

    # Step 4: Initialize database
    if not initialize_database():
        print("\n❌ Setup failed at database initialization")
        return

    # Step 5: Run tests
    if not run_tests():
        print("\n⚠️  Setup completed with warnings")
    else:
        print("\n✅ Setup completed successfully!")

    print("""
    Next steps:
    1. Edit .env file with your credentials
    2. Run: python main.py
    3. Start trading!
    """)


if __name__ == "__main__":
    main()
