# Web Automation Bot

A web automation bot that visits target websites using French proxies with human-like behavior simulation and anti-detection measures.

## Installation

1. Run `install.bat` to install all dependencies
2. Add your French proxy credentials to `proxies.txt` (format: `host:port:username:password`)

## Usage

**Quick Start:**
- Run `start.bat` and choose your mode
- Or directly: `python bot.py` (visible) or `python bot.py --headless` (background)

**Features:**
- 550-700 sessions per day with random distribution
- Visits 7 target URLs either directly or via Bing search
- Generates PDF reports every 50 sessions
- Operates during French business hours (8 AM - 10 PM)
- Advanced anti-detection and human behavior simulation

**Session Display:**
Each session shows: Number, Browser, IP, Location, Route, URLs, Time, Clicks, Success/Failure status
