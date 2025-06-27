#!/usr/bin/env python3

import asyncio
import sys
import subprocess
from pathlib import Path

def install_requirements():
    """Install required packages"""
    print("🔧 Installing Python packages...")
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])
        print("✅ Python packages installed successfully")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install packages: {e}")
        return False
    
    print("🌐 Installing Playwright browsers...")
    try:
        subprocess.check_call([sys.executable, '-m', 'playwright', 'install'])
        print("✅ Playwright browsers installed successfully")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install browsers: {e}")
        return False
    
    return True

def check_proxy_file():
    """Check if proxies.txt exists and has content"""
    proxy_file = Path('proxies.txt')
    if not proxy_file.exists():
        print("❌ proxies.txt not found!")
        print("Please create proxies.txt with your proxy credentials")
        print("Format: host:port:username:password (one per line)")
        return False
    
    with open(proxy_file, 'r') as f:
        lines = [line.strip() for line in f if line.strip()]
    
    if not lines:
        print("❌ proxies.txt is empty!")
        print("Please add your proxy credentials")
        return False
    
    print(f"✅ Found {len(lines)} proxies in proxies.txt")
    return True

def main():
    """Main setup function"""
    print("🤖 Web Automation Bot Setup")
    print("=" * 40)
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        print(f"Current version: {sys.version}")
        return False
    
    print(f"✅ Python {sys.version.split()[0]} detected")
    
    # Check proxy file
    if not check_proxy_file():
        return False
    
    # Install requirements
    if not install_requirements():
        return False
    
    print("\n🎉 Setup completed successfully!")
    print("\nTo run the bot:")
    print("  python bot.py")
    print("\nFor help:")
    print("  python bot.py --help")
    
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1)
