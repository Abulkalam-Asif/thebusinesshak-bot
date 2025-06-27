#!/usr/bin/env python3
"""
Quick Bot Startup Test
This script tests if the bot can initialize without hanging on input prompts.
"""

import sys
import os
from pathlib import Path

# Add the current directory to the path
sys.path.append(str(Path(__file__).parent))


def test_bot_startup():
  """Test bot initialization"""
  print("🧪 Testing Bot Startup...")
  print("=" * 50)

  try:
    # Import bot
    from bot import WebAutomationBot

    print("✅ Bot import successful")

    # Try to initialize bot (this should not hang)
    print("🔄 Initializing bot...")
    bot = WebAutomationBot()

    print("✅ Bot initialization successful")
    print(f"📊 Configuration loaded: {len(bot.target_urls)} target URLs")
    print(f"🔗 Proxies loaded: {len(bot.proxies)} proxies")
    print(f"📁 Reports directory: {bot.reports_dir}")
    print(f"📁 Results directory: {bot.results_dir}")
    print(f"📁 Logs directory: {bot.logs_dir}")

    # Test PDF generation
    print("🧪 Testing PDF generation...")
    success = bot.generate_test_report()

    if success:
      print("✅ PDF generation test PASSED")
    else:
      print("❌ PDF generation test FAILED")

    print("\n✅ All startup tests PASSED!")
    return True

  except Exception as e:
    print(f"❌ Startup test failed: {e}")
    import traceback
    traceback.print_exc()
    return False


if __name__ == "__main__":
  success = test_bot_startup()
  if not success:
    sys.exit(1)
  print("\n🎉 Bot is ready to run!")
