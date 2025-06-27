# 🚀 Quick Start Guide

## Installation (Choose One Method)

### Method 1: Automatic Installation (Recommended)
1. Double-click `install.bat`
2. Wait for all packages to install
3. Double-click `start.bat` to open control panel

### Method 2: Manual Installation
1. Open Command Prompt in this folder
2. Run: `pip install -r requirements.txt`
3. Run: `python -m playwright install`
4. Run: `python bot.py`

## First Time Setup

1. **Check your proxy file**: Ensure `proxies.txt` contains your Oxylabs credentials
2. **Test proxies**: Run `python manage.py test-proxies`
3. **Review configuration**: Run `python manage.py status`

## Running the Bot

### Easy Way (Windows)
- Double-click `start.bat` and select option 1

### Command Line
```bash
python bot.py
```

### With Management Interface
```bash
python manage.py run
```

## Configuration

Edit `config.json` to customize:
- Daily session counts (550-700 default)
- Session duration (25-90 seconds default)
- Operating hours (8 AM - 10 PM French time)
- Target URLs and search keywords

## Quick Commands

```bash
# Show status
python manage.py status

# Update configuration
python manage.py config

# Add new target URL
python manage.py add-url

# Add search keyword
python manage.py add-keyword

# Test proxy connectivity
python manage.py test-proxies
```

## Reports

- Generated every 50 sessions automatically
- Saved to `reports/` folder in the project directory
- PDF format with detailed session information

## Troubleshooting

### Common Issues:
1. **Import errors**: Run `install.bat` or `pip install -r requirements.txt`
2. **No proxies**: Check `proxies.txt` format (host:port:user:pass)
3. **Browser errors**: Run `python -m playwright install`

### Getting Help:
- Check `bot.log` for detailed error information
- Ensure Python 3.8+ is installed
- Verify internet connection and proxy access

## File Structure

```
📁 thebusinesshak-bot/
├── 🤖 bot.py              # Main bot script
├── ⚙️ manage.py           # Management utilities
├── 📄 config.json         # Configuration file
├── 🌐 proxies.txt         # Proxy credentials
├── 📋 requirements.txt    # Python dependencies
├── 🚀 start.bat          # Windows control panel
├── 💾 install.bat        # Auto installer
├── 📖 README.md          # Full documentation
└── 📝 bot.log            # Runtime logs
```

## Safety Features

- ✅ Headless browser operation
- ✅ Anti-detection measures
- ✅ Proxy rotation
- ✅ Human-like behavior simulation
- ✅ French timezone compliance
- ✅ Automatic session logging
- ✅ Error handling and recovery

## Support

Check the full `README.md` for detailed documentation and troubleshooting.
