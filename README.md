# Web Automation Bot

A sophisticated web automation bot that mimics human behavior to visit target websites through direct access or Google searches, using rotating French proxies and anti-detection measures.

## Features

- **Multi-Browser Support**: Randomly uses Chrome, Firefox, and Edge browsers
- **Proxy Rotation**: Uses French proxies from Oxylabs with automatic rotation
- **Anti-Detection**: Advanced measures to avoid digital fingerprints
- **Human-Like Behavior**: 
  - Random mouse movements
  - Natural scrolling patterns
  - Random clicks (0-4 per session)
  - Variable session durations (25-90 seconds)
- **Visit Modes**:
  - Direct: Visit target URLs directly
  - Search: Search on Google and click through to target sites
- **Automated Reporting**: PDF reports generated every 50 sessions
- **French Time Zone Support**: Operates during French business hours (8 AM - 10 PM)
- **Session Management**: 550-700 sessions per day with random distribution

## Target URLs

1. https://www.thebusinesshack.com/hire-a-pro-france
2. https://www.mindyourbiz.online/find-a-pro_france
3. https://www.arcsaver.com/find-a-pro
4. https://www.le-trades.com/find-trades
5. https://www.batiexperts.com/trouver-des-artisans
6. https://www.trouveun.pro/
7. https://www.cherche-artisan.com

## Installation

### Prerequisites
- Python 3.8 or higher
- Windows operating system
- Active internet connection

### Quick Installation
1. Double-click `install.bat` to automatically install all dependencies
2. Or manually run:
   ```
   pip install -r requirements.txt
   python -m playwright install
   ```

### Manual Installation Steps
```bash
# Install Python packages
pip install playwright requests reportlab fake-useragent pytz colorama asyncio-throttle python-dateutil

# Install Playwright browsers
python -m playwright install
```

## Usage

### Starting the Bot
```bash
python bot.py
```

### Interactive Options
- **French Hours Override**: Bot will ask if you want to run outside 8 AM - 10 PM French time
- **Daily Sessions**: Automatically generates 550-700 sessions per day

### Session Information Display
For each session, the bot displays:
- Session Number (001/700)
- Browser type (Chrome, Firefox, Edge)
- IP Address and Location
- Web Route (Direct or Search)
- URL or Keywords used
- Other URLs visited during session
- Time spent on target URL
- Number of clicks performed
- Success/Failure status

## Configuration

### Proxy Configuration
- Edit `proxies.txt` with your Oxylabs proxy credentials
- Format: `host:port:username:password` (one per line)

### Customizing Target URLs
Edit the `target_urls` list in `bot.py`:
```python
self.target_urls = [
    "https://your-website1.com",
    "https://your-website2.com",
    # Add more URLs...
]
```

### Customizing Search Keywords
Edit the `search_keywords` list in `bot.py`:
```python
self.search_keywords = [
    "your keyword 1",
    "your keyword 2",
    # Add more keywords...
]
```

## Reports

### Automatic PDF Reports
- Generated every 50 completed sessions
- Saved to `reports/` folder in the project directory
- Include detailed session information:
  - Success/failure rates
  - Browser distribution
  - IP locations
  - Time spent on sites
  - Click statistics

### Report Contents
- **Summary**: Total sessions, success rate, time period
- **Session Details**: Individual session breakdowns with all metrics
- **Timestamps**: All activities are timestamped

## Anti-Detection Features

### Browser Fingerprint Masking
- Random viewport sizes
- Rotating user agents
- French locale settings
- Geolocation spoofing (Paris area)
- Timezone set to Europe/Paris

### Human Behavior Simulation
- **Mouse Movements**: Random, natural-looking cursor paths
- **Scrolling**: Variable speed and direction patterns
- **Timing**: Random delays between actions
- **Clicking**: Random elements with realistic interaction patterns

### Technical Anti-Detection
- WebDriver property masking
- Plugin enumeration spoofing
- Language preference setting
- Runtime environment masking
- Notification permission mocking

## Troubleshooting

### Common Issues

1. **Import Errors**: Run `install.bat` or install packages manually
2. **Proxy Connection Errors**: Check proxy credentials in `proxies.txt`
3. **Browser Launch Errors**: Ensure Playwright browsers are installed
4. **Permission Errors**: Run as administrator if needed

### Log Files
- `bot.log`: Detailed logging of all bot activities
- Console output: Real-time session information

### Debug Mode
To enable debug logging, modify the logging level in `bot.py`:
```python
logging.basicConfig(level=logging.DEBUG, ...)
```

## Security & Compliance

- All sessions are logged for audit purposes
- No sensitive data is stored permanently
- Browser data is cleared after each session
- Proxy rotation ensures IP diversity
- Respects robots.txt and rate limiting

## Performance

### System Requirements
- **RAM**: 4GB minimum, 8GB recommended
- **CPU**: Dual-core processor minimum
- **Storage**: 1GB free space for reports and logs
- **Network**: Stable internet connection

### Optimization Tips
- Close unnecessary applications while running
- Ensure sufficient disk space for logs and reports
- Use SSD storage for better performance
- Monitor CPU and memory usage

## Support

For issues or questions:
1. Check the `bot.log` file for error details
2. Verify proxy connectivity
3. Ensure all dependencies are installed
4. Check Python version compatibility

## Legal Notice

This bot is designed for legitimate website testing and traffic simulation purposes. Users are responsible for:
- Complying with target website terms of service
- Respecting rate limits and server resources
- Following applicable laws and regulations
- Using proxies in accordance with provider terms

Always ensure you have permission to test the target websites and use the automation responsibly.
