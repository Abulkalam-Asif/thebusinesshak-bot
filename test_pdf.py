#!/usr/bin/env python3
"""
Test PDF Report Generation
This script tests if PDF reports can be generated successfully.
"""

import sys
from pathlib import Path

# Add the current directory to the path so we can import bot.py
sys.path.append(str(Path(__file__).parent))

from bot import WebAutomationBot

def test_pdf_generation():
    """Test PDF report generation"""
    print("🧪 Testing PDF Report Generation...")
    print("=" * 50)
    
    try:
        # Initialize bot
        bot = WebAutomationBot()
        
        # Test PDF generation
        success = bot.generate_test_report()
        
        if success:
            print("\n✅ PDF generation test PASSED!")
            print("📁 Check the 'reports' folder for the generated test report.")
        else:
            print("\n❌ PDF generation test FAILED!")
            
    except Exception as e:
        print(f"\n❌ Error during test: {e}")
        return False
    
    return success

if __name__ == "__main__":
    test_pdf_generation()
