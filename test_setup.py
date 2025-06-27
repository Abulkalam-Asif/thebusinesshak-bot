#!/usr/bin/env python3

import sys
import asyncio
import json
from pathlib import Path

def test_imports():
    """Test if all required packages are installed"""
    print("🔍 Testing imports...")
    
    try:
        import playwright
        print("✅ Playwright imported successfully")
    except ImportError:
        print("❌ Playwright not found - run: pip install playwright")
        return False
    
    try:
        import requests
        print("✅ Requests imported successfully")
    except ImportError:
        print("❌ Requests not found - run: pip install requests")
        return False
    
    try:
        import reportlab
        print("✅ ReportLab imported successfully")
    except ImportError:
        print("❌ ReportLab not found - run: pip install reportlab")
        return False
    
    try:
        import fake_useragent
        print("✅ Fake UserAgent imported successfully")
    except ImportError:
        print("❌ Fake UserAgent not found - run: pip install fake-useragent")
        return False
    
    try:
        from playwright.async_api import async_playwright
        print("✅ Playwright async API imported successfully")
    except ImportError:
        print("❌ Playwright browsers not installed - run: python -m playwright install")
        return False
    
    return True

def test_config_file():
    """Test configuration file"""
    print("\n📋 Testing configuration...")
    
    config_file = Path('config.json')
    if not config_file.exists():
        print("❌ config.json not found")
        return False
    
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
        print("✅ Config file loaded successfully")
        
        # Check required sections
        required_sections = ['bot_settings', 'target_urls', 'search_keywords']
        for section in required_sections:
            if section in config:
                print(f"✅ {section} section found")
            else:
                print(f"❌ {section} section missing")
                return False
        
        return True
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in config file: {e}")
        return False

def test_proxy_file():
    """Test proxy file"""
    print("\n🌐 Testing proxy file...")
    
    proxy_file = Path('proxies.txt')
    if not proxy_file.exists():
        print("❌ proxies.txt not found")
        return False
    
    with open(proxy_file, 'r') as f:
        lines = [line.strip() for line in f if line.strip()]
    
    if not lines:
        print("❌ proxies.txt is empty")
        return False
    
    valid_proxies = 0
    for line in lines[:5]:  # Check first 5 proxies
        parts = line.split(':')
        if len(parts) >= 4:
            valid_proxies += 1
        else:
            print(f"⚠️  Invalid proxy format: {line}")
    
    print(f"✅ Found {len(lines)} total proxies, {valid_proxies} in valid format")
    return valid_proxies > 0

async def test_browser_launch():
    """Test browser launching"""
    print("\n🌐 Testing browser launch...")
    
    try:
        from playwright.async_api import async_playwright
        
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Simple test navigation
        await page.goto("https://httpbin.org/user-agent")
        content = await page.content()
        
        await browser.close()
        await playwright.stop()
        
        if "user-agent" in content.lower():
            print("✅ Browser test successful")
            return True
        else:
            print("❌ Browser test failed - unexpected content")
            return False
            
    except Exception as e:
        print(f"❌ Browser test failed: {e}")
        return False

def test_reports_directory():
    """Test reports directory creation"""
    print("\n📊 Testing reports directory...")
    
    reports_dir = Path("reports")
    try:
        reports_dir.mkdir(exist_ok=True)
        print(f"✅ Reports directory ready: {reports_dir}")
        return True
    except Exception as e:
        print(f"❌ Failed to create reports directory: {e}")
        return False

async def main():
    """Run all tests"""
    print("🧪 Web Automation Bot - System Test")
    print("=" * 50)
    
    tests = [
        ("Package Imports", test_imports),
        ("Configuration File", test_config_file),
        ("Proxy File", test_proxy_file),
        ("Reports Directory", test_reports_directory),
        ("Browser Launch", test_browser_launch),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            
            if result:
                passed += 1
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
    
    print(f"\n{'='*50}")
    print(f"🎯 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Bot is ready to run.")
        print("\nTo start the bot:")
        print("  • Windows: Double-click start.bat")
        print("  • Command line: python bot.py")
    else:
        print("❌ Some tests failed. Please fix issues before running the bot.")
        print("\nFor help:")
        print("  • Check QUICKSTART.md")
        print("  • Run install.bat")
        print("  • Ensure all requirements are installed")
    
    return passed == total

if __name__ == "__main__":
    success = asyncio.run(main())
    if not success:
        sys.exit(1)
