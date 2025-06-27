#!/usr/bin/env python3

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime
import subprocess

def load_config():
    """Load configuration from config.json"""
    try:
        with open('config.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print("❌ config.json not found!")
        return None
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in config.json: {e}")
        return None

def save_config(config):
    """Save configuration to config.json"""
    try:
        with open('config.json', 'w') as f:
            json.dump(config, f, indent=4)
        print("✅ Configuration saved successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to save configuration: {e}")
        return False

def show_status():
    """Show current bot status and configuration"""
    config = load_config()
    if not config:
        return
    
    print("🤖 Web Automation Bot Status")
    print("=" * 50)
    
    # Bot settings
    settings = config['bot_settings']
    print(f"📊 Daily Sessions: {settings['daily_sessions_min']}-{settings['daily_sessions_max']}")
    print(f"⏰ Operating Hours: {settings['french_hours_start']}:00-{settings['french_hours_end']}:00 (French time)")
    print(f"⏱️  Session Duration: {settings['session_duration_min']}-{settings['session_duration_max']} seconds")
    print(f"🖱️  Max Clicks/Session: {settings['max_clicks_per_session']}")
    print(f"📈 Report Frequency: Every {settings['report_frequency']} sessions")
    
    # Target URLs
    print(f"\n🎯 Target URLs ({len(config['target_urls'])}):")
    for i, url in enumerate(config['target_urls'], 1):
        print(f"  {i}. {url}")
    
    # Search keywords
    print(f"\n🔍 Search Keywords ({len(config['search_keywords'])}):")
    for i, keyword in enumerate(config['search_keywords'], 1):
        print(f"  {i}. {keyword}")
    
    # Proxy status
    proxy_file = Path('proxies.txt')
    if proxy_file.exists():
        with open(proxy_file, 'r') as f:
            proxy_count = len([line for line in f if line.strip()])
        print(f"\n🌐 Proxies: {proxy_count} loaded from proxies.txt")
    else:
        print("\n❌ No proxies.txt file found")
    
    # Reports directory
    reports_dir = Path.home() / "Desktop" / "Bot_Reports"
    if reports_dir.exists():
        report_files = list(reports_dir.glob("*.pdf"))
        print(f"📋 Reports: {len(report_files)} PDF reports in {reports_dir}")
    else:
        print("📋 Reports: No reports directory found")

def update_config():
    """Interactive configuration update"""
    config = load_config()
    if not config:
        return
    
    print("🔧 Configuration Update")
    print("=" * 30)
    
    # Update daily sessions
    current_min = config['bot_settings']['daily_sessions_min']
    current_max = config['bot_settings']['daily_sessions_max']
    print(f"\nCurrent daily sessions: {current_min}-{current_max}")
    
    try:
        new_min = input(f"New minimum ({current_min}): ").strip()
        if new_min:
            config['bot_settings']['daily_sessions_min'] = int(new_min)
        
        new_max = input(f"New maximum ({current_max}): ").strip()
        if new_max:
            config['bot_settings']['daily_sessions_max'] = int(new_max)
    except ValueError:
        print("❌ Invalid number entered")
        return
    
    # Update session duration
    current_min_dur = config['bot_settings']['session_duration_min']
    current_max_dur = config['bot_settings']['session_duration_max']
    print(f"\nCurrent session duration: {current_min_dur}-{current_max_dur} seconds")
    
    try:
        new_min_dur = input(f"New minimum duration ({current_min_dur}): ").strip()
        if new_min_dur:
            config['bot_settings']['session_duration_min'] = int(new_min_dur)
        
        new_max_dur = input(f"New maximum duration ({current_max_dur}): ").strip()
        if new_max_dur:
            config['bot_settings']['session_duration_max'] = int(new_max_dur)
    except ValueError:
        print("❌ Invalid number entered")
        return
    
    # Save configuration
    save_config(config)

def add_url():
    """Add a new target URL"""
    config = load_config()
    if not config:
        return
    
    print("🎯 Add Target URL")
    print("=" * 20)
    
    new_url = input("Enter new URL: ").strip()
    if not new_url:
        print("❌ No URL entered")
        return
    
    if not new_url.startswith(('http://', 'https://')):
        new_url = 'https://' + new_url
    
    if new_url in config['target_urls']:
        print("❌ URL already exists")
        return
    
    config['target_urls'].append(new_url)
    print(f"✅ Added: {new_url}")
    save_config(config)

def add_keyword():
    """Add a new search keyword"""
    config = load_config()
    if not config:
        return
    
    print("🔍 Add Search Keyword")
    print("=" * 25)
    
    new_keyword = input("Enter new keyword: ").strip()
    if not new_keyword:
        print("❌ No keyword entered")
        return
    
    if new_keyword in config['search_keywords']:
        print("❌ Keyword already exists")
        return
    
    config['search_keywords'].append(new_keyword)
    print(f"✅ Added: {new_keyword}")
    save_config(config)

def test_proxies():
    """Test proxy connectivity"""
    print("🌐 Testing Proxy Connectivity")
    print("=" * 35)
    
    proxy_file = Path('proxies.txt')
    if not proxy_file.exists():
        print("❌ proxies.txt not found")
        return
    
    import requests
    import random
    
    with open(proxy_file, 'r') as f:
        proxies = [line.strip() for line in f if line.strip()]
    
    if not proxies:
        print("❌ No proxies found in file")
        return
    
    # Test 5 random proxies
    test_proxies = random.sample(proxies, min(5, len(proxies)))
    
    for i, proxy_line in enumerate(test_proxies, 1):
        try:
            parts = proxy_line.split(':')
            if len(parts) >= 4:
                host, port, username, password = parts[:4]
                proxy_url = f"http://{username}:{password}@{host}:{port}"
                
                print(f"Testing proxy {i}/5: {host}:{port}")
                
                response = requests.get(
                    "https://httpbin.org/ip", 
                    proxies={"http": proxy_url, "https": proxy_url},
                    timeout=10
                )
                
                if response.status_code == 200:
                    ip_info = response.json()
                    print(f"✅ Success - IP: {ip_info.get('origin', 'Unknown')}")
                else:
                    print(f"❌ Failed - Status: {response.status_code}")
                    
        except Exception as e:
            print(f"❌ Error: {str(e)[:50]}...")
    
    print("\n✅ Proxy test completed")

def run_bot():
    """Run the main bot"""
    print("🚀 Starting Web Automation Bot...")
    try:
        subprocess.run([sys.executable, 'bot.py'], check=True)
    except subprocess.CalledProcessError:
        print("❌ Bot execution failed")
    except KeyboardInterrupt:
        print("\n⏹️  Bot stopped by user")

def main():
    parser = argparse.ArgumentParser(description='Web Automation Bot Manager')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Status command
    subparsers.add_parser('status', help='Show bot status and configuration')
    
    # Config command
    subparsers.add_parser('config', help='Update bot configuration')
    
    # Add URL command
    subparsers.add_parser('add-url', help='Add a new target URL')
    
    # Add keyword command
    subparsers.add_parser('add-keyword', help='Add a new search keyword')
    
    # Test proxies command
    subparsers.add_parser('test-proxies', help='Test proxy connectivity')
    
    # Run command
    subparsers.add_parser('run', help='Run the bot')
    
    args = parser.parse_args()
    
    if args.command == 'status':
        show_status()
    elif args.command == 'config':
        update_config()
    elif args.command == 'add-url':
        add_url()
    elif args.command == 'add-keyword':
        add_keyword()
    elif args.command == 'test-proxies':
        test_proxies()
    elif args.command == 'run':
        run_bot()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
