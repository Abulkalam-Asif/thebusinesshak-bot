import asyncio
import random
import time
import json
import os
import sys
from datetime import datetime, timedelta
import pytz
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import logging
from dataclasses import dataclass, asdict
from enum import Enum
import requests
from fake_useragent import UserAgent
from colorama import init, Fore, Back, Style
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors

# Initialize colorama for colored terminal output
init(autoreset=True)


class BrowserType(Enum):
  CHROME = "chrome"
  FIREFOX = "firefox"
  EDGE = "edge"


class VisitMode(Enum):
  DIRECT = "direct"
  SEARCH = "search"


@dataclass
class ProxyInfo:
  host: str
  port: str
  username: str
  password: str

  @property
  def url(self) -> str:
    return f"http://{self.username}:{self.password}@{self.host}:{self.port}"


@dataclass
class SessionResult:
  session_number: int
  total_sessions: int
  browser: str
  ip_address: str
  ip_location: str
  web_route: str
  url_or_keywords: str
  search_engine: Optional[str]  # Track which search engine was used (for search mode)
  # The final target URL that was actually visited
  target_url_reached: Optional[str]
  other_urls_visited: List[str]
  time_on_target_url: float
  clicks: int
  success: bool
  failure_reason: Optional[str]
  timestamp: datetime


class WebAutomationBot:
  def __init__(self, debug_mode=True):  # Default to visible mode
    self.debug_mode = debug_mode  # Add debug mode flag
    # Load configuration
    self.config = self._load_config()
    self.target_sites = self.config['target_sites']
    self.target_urls = list(self.target_sites.keys())  # Keep for backward compatibility

    self.proxies = self._load_proxies()
    self.ua = UserAgent()
    self.session_results: List[SessionResult] = []

    # Create results directory
    self.results_dir = Path("results")
    self.results_dir.mkdir(exist_ok=True)

    # Create timestamped results files
    self.run_timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    self.results_file = self.results_dir / \
        f"session_results_{self.run_timestamp}.json"
    self.summary_file = self.results_dir / \
        f"session_summary_{self.run_timestamp}.json"

    # Create reports directory
    self.reports_dir = Path("reports")
    self.reports_dir.mkdir(exist_ok=True)

    # Create logs directory
    self.logs_dir = Path("logs")
    self.logs_dir.mkdir(exist_ok=True)

    # Setup per-run logging with timestamp
    self.log_file = self.logs_dir / f"{self.run_timestamp}.log"

    # Setup logging with both file and console handlers
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(self.log_file),
            logging.StreamHandler()
        ]
    )
    self.logger = logging.getLogger(__name__)

    # Log the start of the bot run
    self.logger.info(f"Bot run started - Log file: {self.log_file}")
    self.logger.info(f"Results file: {self.results_file}")
    self.logger.info(f"Summary file: {self.summary_file}")
    self.logger.info(f"Loaded {len(self.proxies)} proxies from proxies.txt")
    self.logger.info(f"Target sites: {len(self.target_sites)}")
    total_keywords = sum(len(keywords) for keywords in self.target_sites.values())
    self.logger.info(f"Total keywords: {total_keywords}")

  def _load_config(self):
    """Load configuration from config.json"""
    try:
      with open('config.json', 'r') as f:
        return json.load(f)
    except FileNotFoundError:
      # Default configuration
      return {
          "bot_settings": {
              "daily_sessions_min": 550,
              "daily_sessions_max": 700,
              "french_hours_start": 8,
              "french_hours_end": 22,
              "session_duration_min": 25,
              "session_duration_max": 90,
              "max_clicks_per_session": 4,
              "report_frequency": 50
          },
          "target_sites": {
              "https://www.thebusinesshack.com/hire-a-pro-france": [
                  "business hack",
                  "hire professional France",
                  "business services France"
              ],
              "https://www.mindyourbiz.online/find-a-pro_france": [
                  "mind your biz",
                  "find professional France",
                  "business expert France"
              ],
              "https://www.arcsaver.com/find-a-pro": [
                  "arc saver",
                  "find professional",
                  "expert services"
              ],
              "https://www.le-trades.com/find-trades": [
                  "le trades",
                  "find trades",
                  "trouver métiers"
              ],
              "https://www.batiexperts.com/trouver-des-artisans": [
                  "bati experts",
                  "expert bâtiment",
                  "trouver des artisans"
              ],
              "https://www.trouveun.pro/": [
                  "trouve un pro",
                  "trouver professionnel",
                  "expert France"
              ],
              "https://www.cherche-artisan.com": [
                  "cherche artisan",
                  "trouver artisan",
                  "artisan qualifié"
              ]
          }
      }

  def _load_proxies(self) -> List[ProxyInfo]:
    """Load proxy list from proxies.txt file"""
    proxies = []
    try:
      with open('proxies.txt', 'r') as f:
        for line in f:
          line = line.strip()
          if line and ':' in line:
            parts = line.split(':')
            if len(parts) >= 4:
              proxies.append(ProxyInfo(
                  host=parts[0],
                  port=parts[1],
                  username=parts[2],
                  password=parts[3]
              ))
    except FileNotFoundError:
      self.logger.error("proxies.txt file not found!")
      sys.exit(1)

    if not proxies:
      self.logger.error("No valid proxies found in proxies.txt!")
      sys.exit(1)

    return proxies

  def _get_random_proxy(self) -> ProxyInfo:
    """Get a random French proxy"""
    return random.choice(self.proxies)

  def _get_french_timezone(self) -> pytz.timezone:
    """Get French timezone"""
    return pytz.timezone('Europe/Paris')

  def _is_french_hours(self) -> bool:
    """Check if current time is within configured French business hours"""
    french_tz = self._get_french_timezone()
    french_time = datetime.now(french_tz)
    settings = self.config['bot_settings']
    return settings['french_hours_start'] <= french_time.hour <= settings['french_hours_end']

  def _get_daily_session_count(self) -> int:
    """Generate random daily session count between configured min-max"""
    settings = self.config['bot_settings']
    return random.randint(settings['daily_sessions_min'], settings['daily_sessions_max'])

  async def _get_ip_info(self, page: Page) -> Tuple[str, str]:
    """Get current IP address and location"""
    try:
      # Try multiple IP check services
      ip_services = [
          "https://httpbin.org/ip",
          "https://api.ipify.org?format=json",
          "https://jsonip.com"
      ]

      for service in ip_services:
        try:
          await page.goto(service, timeout=30000)
          content = await page.content()

          if "httpbin.org" in service:
            ip_data = json.loads(await page.evaluate("() => document.body.innerText"))
            ip_address = ip_data.get('origin', 'Unknown')
          elif "ipify" in service:
            ip_data = json.loads(await page.evaluate("() => document.body.innerText"))
            ip_address = ip_data.get('ip', 'Unknown')
          else:  # jsonip.com
            ip_data = json.loads(await page.evaluate("() => document.body.innerText"))
            ip_address = ip_data.get('ip', 'Unknown')

          if ip_address and ip_address != 'Unknown':
            break
        except:
          continue
      else:
        ip_address = "Unknown"

      # Get location info
      try:
        response = requests.get(
          f"http://ip-api.com/json/{ip_address}", timeout=10)
        location_data = response.json()
        if location_data.get('status') == 'success':
          location = f"{location_data.get('city', 'Unknown')}, {location_data.get('country', 'Unknown')}"
        else:
          location = "Unknown Location"
      except:
        location = "Unknown Location"

      return ip_address, location
    except Exception as e:
      self.logger.error(f"Failed to get IP info: {e}")
      return "Unknown IP", "Unknown Location"

  async def _create_browser_context(self, browser: Browser, proxy: ProxyInfo, browser_type: BrowserType) -> BrowserContext:
    """Create browser context with anti-detection measures (proxy set at browser level)"""
    # Random viewport sizes
    viewports = [
        {"width": 1920, "height": 1080},
        {"width": 1366, "height": 768},
        {"width": 1536, "height": 864},
        {"width": 1440, "height": 900},
        {"width": 1280, "height": 720}
    ]

    viewport = random.choice(viewports)

    # Browser-specific user agents
    if browser_type == BrowserType.FIREFOX:
      user_agents = [
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101 Firefox/91.0",
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:92.0) Gecko/20100101 Firefox/92.0",
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:93.0) Gecko/20100101 Firefox/93.0"
      ]
    elif browser_type == BrowserType.EDGE:
      user_agents = [
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.864.59",
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36 Edg/92.0.902.55",
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.63 Safari/537.36 Edg/93.0.961.38"
      ]
    else:  # Chrome
      user_agents = [
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.63 Safari/537.36"
      ]

    user_agent = random.choice(user_agents)

    context = await browser.new_context(
        viewport=viewport,
        user_agent=user_agent,
        locale='fr-FR',
        timezone_id='Europe/Paris',
        permissions=['geolocation'],
        geolocation={'latitude': 48.8566 + random.uniform(-0.1, 0.1),
                     'longitude': 2.3522 + random.uniform(-0.1, 0.1)},
        # Anti-detection measures
        extra_http_headers={
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
    )

    # Add stealth scripts
    await context.add_init_script("""
            // Override the navigator.webdriver property
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
            
            // Override the navigator.plugins property
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });
            
            // Override the navigator.languages property
            Object.defineProperty(navigator, 'languages', {
                get: () => ['fr-FR', 'fr', 'en-US', 'en'],
            });
            
            // Remove traces of headless
            Object.defineProperty(navigator, 'platform', {
                get: () => 'Win32',
            });
            
            // Mock chrome runtime
            window.chrome = {
                runtime: {},
            };
            
            // Mock notification permission
            Object.defineProperty(Notification, 'permission', {
                get: () => 'default',
            });
        """)

    return context

  async def _human_like_mouse_movement(self, page: Page):
    """Simulate human-like mouse movements"""
    try:
      viewport = page.viewport_size
      if not viewport:
        return

      # Random mouse movements
      for _ in range(random.randint(2, 5)):
        x = random.randint(0, viewport['width'])
        y = random.randint(0, viewport['height'])
        await page.mouse.move(x, y)
        await asyncio.sleep(random.uniform(0.1, 0.3))
    except Exception as e:
      self.logger.debug(f"Mouse movement error: {e}")

  async def _human_like_scrolling(self, page: Page):
    """Simulate human-like scrolling behavior"""
    try:
      # Random scrolling patterns
      scroll_patterns = [
          # Slow continuous scroll down
          {"direction": "down", "speed": "slow",
           "distance": random.randint(500, 1500)},
          # Quick scroll up
          {"direction": "up", "speed": "fast",
           "distance": random.randint(200, 800)},
          # Medium scroll down
          {"direction": "down", "speed": "medium",
           "distance": random.randint(800, 2000)},
      ]

      pattern = random.choice(scroll_patterns)

      if pattern["speed"] == "slow":
        scroll_step = 50
        delay = random.uniform(0.1, 0.2)
      elif pattern["speed"] == "medium":
        scroll_step = 100
        delay = random.uniform(0.05, 0.1)
      else:  # fast
        scroll_step = 200
        delay = random.uniform(0.02, 0.05)

      distance = pattern["distance"]
      direction = 1 if pattern["direction"] == "down" else -1

      for i in range(0, distance, scroll_step):
        await page.evaluate(f"window.scrollBy(0, {scroll_step * direction})")
        await asyncio.sleep(delay)

    except Exception as e:
      self.logger.debug(f"Scrolling error: {e}")

  async def _random_clicks(self, page: Page) -> Tuple[int, List[str]]:
    """Perform random clicks on the page and return click count and visited URLs"""
    clicks = 0
    visited_urls = []
    max_clicks = random.randint(
      0, self.config['bot_settings']['max_clicks_per_session'])

    try:
      # Get clickable elements
      clickable_selectors = [
          'a:not([href*="mailto:"]):not([href*="tel:"])',
          'button:not([type="submit"])',
          '.btn:not([type="submit"])',
          '[role="button"]',
          '.link',
          '.menu-item a',
          '.nav-link',
          '.footer a'
      ]

      for _ in range(max_clicks):
        try:
          # Try different selectors
          for selector in clickable_selectors:
            elements = await page.query_selector_all(selector)
            if elements:
              # Filter visible elements
              visible_elements = []
              for elem in elements[:10]:  # Check only first 10 for performance
                if await elem.is_visible():
                  visible_elements.append(elem)

              if visible_elements:
                element = random.choice(visible_elements)

                # Get current URL before click
                current_url = page.url

                # Scroll element into view
                await element.scroll_into_view_if_needed()
                await asyncio.sleep(random.uniform(0.5, 1.5))

                # Click with human-like delay
                await element.click()
                clicks += 1

                # Wait for potential navigation
                await asyncio.sleep(random.uniform(1, 3))

                # Check if URL changed
                new_url = page.url
                if new_url != current_url and new_url not in visited_urls:
                  visited_urls.append(new_url)

                break

          # Random delay between clicks
          await asyncio.sleep(random.uniform(2, 5))

        except Exception as e:
          self.logger.debug(f"Click error: {e}")
          continue

    except Exception as e:
      self.logger.debug(f"Random clicks error: {e}")

    return clicks, visited_urls

  async def _visit_direct(self, page: Page) -> str:
    """Visit a target URL directly"""
    target_url = random.choice(self.target_urls)
    await page.goto(target_url, timeout=60000, wait_until='domcontentloaded')
    return target_url

  async def _visit_via_search(self, page: Page) -> Tuple[str, str, str]:
    """Visit target URL via search using random search engine - returns (search_query, target_url, search_engine)"""
    # First select a target URL
    target_url = random.choice(self.target_urls)
    
    # Get a random keyword entry for that specific target URL
    available_keywords = self.target_sites[target_url]
    keyword_entry = random.choice(available_keywords)
    
    # Parse the keyword entry format: "keyword, domain.com"
    if ', ' in keyword_entry:
      keyword, search_domain = keyword_entry.split(', ', 1)
    else:
      # Fallback to old format if comma not found
      keyword = keyword_entry
      search_domain = target_url.split('/')[2].replace('www.', '')
    
    # Clean up the search domain (remove any www. prefix)
    search_domain = search_domain.replace('www.', '')
    
    # Create search query: "keyword domain.com"
    search_query = f"{keyword} {search_domain}"

    # Randomly select search engine
    search_engines = ['duckduckgo', 'bing', 'yahoo']
    selected_engine = random.choice(search_engines)
    
    if self.debug_mode:
      print(f"🔍 Using {selected_engine.title()} search engine")
    
    if selected_engine == 'duckduckgo':
      actual_url = await self._search_duckduckgo(page, search_query, search_domain)
    elif selected_engine == 'bing':
      actual_url = await self._search_bing(page, search_query, search_domain)
    else:  # yahoo
      actual_url = await self._search_yahoo(page, search_query, search_domain)
    
    return search_query, actual_url, selected_engine

  async def _search_duckduckgo(self, page: Page, search_query: str, search_domain: str) -> str:
    """Search using DuckDuckGo"""
    await page.goto("https://duckduckgo.com", timeout=60000)
    await asyncio.sleep(random.uniform(1, 3))

    # Accept cookies if present
    try:
      cookie_button = await page.wait_for_selector('button:has-text("Accept"), .js-cookie-consent-action', timeout=5000)
      if cookie_button:
        await cookie_button.click()
        await asyncio.sleep(1)
    except:
      pass

    # DuckDuckGo search box
    search_box = await page.wait_for_selector('input[name="q"], #search_form_input', timeout=10000)
    await search_box.type(search_query, delay=random.randint(50, 150))
    await asyncio.sleep(random.uniform(0.5, 1.5))
    await page.keyboard.press('Enter')

    # Wait for results
    await page.wait_for_load_state('domcontentloaded')
    await asyncio.sleep(random.uniform(3, 5))

    return await self._find_and_click_target_link(page, search_domain, 'duckduckgo.com', 'DuckDuckGo', search_query)

  async def _search_bing(self, page: Page, search_query: str, search_domain: str) -> str:
    """Search using Bing"""
    await page.goto("https://www.bing.com", timeout=60000)
    await asyncio.sleep(random.uniform(1, 3))

    # Accept cookies if present
    try:
      cookie_button = await page.wait_for_selector('#bnp_btn_accept, button:has-text("Accept"), .cookie-banner button', timeout=5000)
      if cookie_button:
        await cookie_button.click()
        await asyncio.sleep(1)
    except:
      pass

    # Bing search box
    search_box = await page.wait_for_selector('input[name="q"], #sb_form_q', timeout=10000)
    await search_box.type(search_query, delay=random.randint(50, 150))
    await asyncio.sleep(random.uniform(0.5, 1.5))
    await page.keyboard.press('Enter')

    # Wait for results
    await page.wait_for_load_state('domcontentloaded')
    await asyncio.sleep(random.uniform(3, 5))

    return await self._find_and_click_target_link(page, search_domain, 'bing.com', 'Bing', search_query)

  async def _search_yahoo(self, page: Page, search_query: str, search_domain: str) -> str:
    """Search using Yahoo"""
    await page.goto("https://search.yahoo.com", timeout=60000)
    await asyncio.sleep(random.uniform(1, 3))

    # Accept cookies if present
    try:
      cookie_button = await page.wait_for_selector('button[name="agree"], .consent-form button, button:has-text("Accept")', timeout=5000)
      if cookie_button:
        await cookie_button.click()
        await asyncio.sleep(1)
    except:
      pass

    # Yahoo search box
    search_box = await page.wait_for_selector('input[name="p"], #yschsp', timeout=10000)
    await search_box.type(search_query, delay=random.randint(50, 150))
    await asyncio.sleep(random.uniform(0.5, 1.5))
    await page.keyboard.press('Enter')

    # Wait for results
    await page.wait_for_load_state('domcontentloaded')
    await asyncio.sleep(random.uniform(3, 5))

    return await self._find_and_click_target_link(page, search_domain, 'yahoo.com', 'Yahoo', search_query)

  async def _find_and_click_target_link(self, page: Page, search_domain: str, engine_domain: str, engine_name: str, search_query: str) -> str:
    """Generic method to find and click target links across different search engines"""
    try:
      if self.debug_mode:
        print(f"🔍 Looking for domain '{search_domain}' in {engine_name} search results...")
      
      # Generic selectors that work across search engines
      selectors = [
          f'a[href*="{search_domain}"]',                                 # Any link containing domain
          f'h2 a[href*="{search_domain}"], h3 a[href*="{search_domain}"]', # Header links
          f'a[href*="https://{search_domain}"]',                         # HTTPS links
          f'a[href*="http://{search_domain}"]',                          # HTTP links
          f'a[href*="www.{search_domain}"]',                             # www links
          f'[href*="{search_domain}"]:not([href*="{engine_domain}"])',   # Exclude search engine internals
      ]
      
      link_found = None
      for selector in selectors:
        if self.debug_mode:
          print(f"  Trying selector: {selector}")
        
        links = await page.query_selector_all(selector)
        
        if self.debug_mode and links:
          print(f"  Found {len(links)} potential links with this selector")
          for i, link in enumerate(links[:3]):  # Show first 3
            try:
              href = await link.get_attribute('href')
              text = await link.text_content()
              print(f"    Link {i+1}: {href} - '{text[:50]}...'")
            except:
              pass
        
        # Look for visible links that are actual website links
        for link in links:
          try:
            if await link.is_visible():
              href = await link.get_attribute('href')
              # Make sure it's a real website link, not a search engine internal link
              if (href and search_domain in href and 
                  not any(engine_term in href.lower() for engine_term in [engine_domain, '/search?', 'cache:', 'translate.'])):
                link_found = link
                if self.debug_mode:
                  print(f"  ✅ Found matching visible link: {href}")
                break
          except:
            continue
        
        if link_found:
          break
      
      if link_found:
        await link_found.scroll_into_view_if_needed()
        await asyncio.sleep(random.uniform(1, 2))
        
        if self.debug_mode:
          print(f"  🖱️ Clicking on the link...")
          await asyncio.sleep(2)  # Give time to see in debug mode
        
        # Get the link URL before clicking
        target_href = await link_found.get_attribute('href')
        
        await link_found.click()
        
        # Wait for navigation to complete with retries
        max_wait_attempts = 3
        for wait_attempt in range(max_wait_attempts):
          try:
            await page.wait_for_load_state('domcontentloaded', timeout=8000)
            await asyncio.sleep(random.uniform(2, 3))
            
            current_url = page.url
            
            # Check if we actually navigated to the target domain
            if search_domain in current_url and engine_domain not in current_url:
              break
            elif wait_attempt < max_wait_attempts - 1:
              if self.debug_mode:
                print(f"  ⏳ Still on {engine_name}, waiting longer... (attempt {wait_attempt + 1})")
              await asyncio.sleep(3)
            
          except:
            await asyncio.sleep(2)
        
        # Get the actual page we landed on
        actual_url = page.url
        
        if self.debug_mode:
          print(f"  🎯 Landed on: {actual_url}")
          
        # If we're still on search engine, try direct navigation as fallback
        if engine_domain in actual_url and target_href:
          if self.debug_mode:
            print(f"  🔄 Still on {engine_name}, trying direct navigation to: {target_href}")
          try:
            await page.goto(target_href, timeout=10000, wait_until='domcontentloaded')
            await asyncio.sleep(2)
            actual_url = page.url
            if self.debug_mode:
              print(f"  🎯 Direct navigation result: {actual_url}")
          except Exception as nav_error:
            if self.debug_mode:
              print(f"  ❌ Direct navigation failed: {nav_error}")
        
        return actual_url
      else:
        # If target domain not found, provide debug info
        if self.debug_mode:
          print(f"  ❌ No matching links found for domain '{search_domain}'")
          print(f"  📄 Page title: {await page.title()}")
          
          # Get all links on the page for debugging
          all_links = await page.query_selector_all('a[href]')
          print(f"  📊 Total links on page: {len(all_links)}")
          
          # Show first 10 links
          print(f"  🔗 First 10 links found:")
          for i, link in enumerate(all_links[:10]):
            try:
              href = await link.get_attribute('href')
              text = await link.text_content()
              if href:
                print(f"    {i+1}. {href} - '{text[:30]}...'")
            except:
              pass
          
          await asyncio.sleep(5)  # Pause to examine in debug mode
        
        raise Exception(f"Target domain '{search_domain}' not found in {engine_name} search results for query: '{search_query}'")
        
    except Exception as e:
      if "not found in search results" in str(e):
        raise e
      else:
        if self.debug_mode:
          print(f"  ❌ Error during link clicking: {str(e)}")
          await asyncio.sleep(3)
        raise Exception(f"Failed to click target link for '{search_domain}': {str(e)}")

  async def _run_single_session(self, session_num: int, total_sessions: int, browser_type: BrowserType) -> SessionResult:
    """Run a single automation session"""
    # Try up to 3 different proxies only for connection/browser issues, not search failures
    max_proxy_attempts = 3

    for attempt in range(max_proxy_attempts):
      proxy = self._get_random_proxy()
      visit_mode = random.choice([VisitMode.DIRECT, VisitMode.SEARCH])

      # Initialize session result
      result = SessionResult(
          session_number=session_num,
          total_sessions=total_sessions,
          browser=browser_type.value,
          ip_address="Unknown",
          ip_location="Unknown",
          web_route=visit_mode.value,
          url_or_keywords="",
          search_engine=None,  # Will be set for search mode
          target_url_reached=None,
          other_urls_visited=[],
          time_on_target_url=0.0,
          clicks=0,
          success=False,
          failure_reason=None,
          timestamp=datetime.now()
      )

      playwright = None
      browser = None
      context = None

      try:
        print(f"\n{Fore.CYAN}{'='*50}")
        print(f"{Fore.YELLOW}Session {session_num:03d}/{total_sessions} (Attempt {attempt + 1}/{max_proxy_attempts})")
        print(f"{Fore.GREEN}Browser: {browser_type.value.title()}")
        print(f"{Fore.BLUE}Proxy: {proxy.host}:{proxy.port}")
        print(f"{Fore.MAGENTA}Route: {visit_mode.value.title()} ({'Search Engine' if visit_mode == VisitMode.SEARCH else 'Direct'})")

        playwright = await async_playwright().start()

        # Launch browser based on type with proxy
        proxy_config = {
            "server": f"http://{proxy.host}:{proxy.port}",
            "username": proxy.username,
            "password": proxy.password
        }

        if browser_type == BrowserType.FIREFOX:
          browser = await playwright.firefox.launch(
              headless=not self.debug_mode,  # Use visible mode if debug is enabled
              proxy=proxy_config
          )
        elif browser_type == BrowserType.EDGE:
          browser = await playwright.chromium.launch(
              headless=not self.debug_mode,  # Use visible mode if debug is enabled
              proxy=proxy_config,
              channel="msedge"  # Use Edge specifically
          )
        else:  # Chrome
          browser = await playwright.chromium.launch(
              headless=not self.debug_mode,  # Use visible mode if debug is enabled
              proxy=proxy_config
              # Default chromium (Google Chrome)
          )

        # Create context with anti-detection measures (proxy already set at browser level)
        context = await self._create_browser_context(browser, proxy, browser_type)
        page = await context.new_page()

        # Get IP information
        result.ip_address, result.ip_location = await self._get_ip_info(page)
        print(f"{Fore.CYAN}IP: {result.ip_address}")
        print(f"{Fore.CYAN}Location: {result.ip_location}")

        # Visit target based on mode
        start_time = time.time()

        if visit_mode == VisitMode.DIRECT:
          target_url = await self._visit_direct(page)
          result.url_or_keywords = target_url
          result.target_url_reached = target_url
          print(f"{Fore.WHITE}Direct URL: {target_url}")
        else:
          try:
            keyword, target_url, search_engine = await self._visit_via_search(page)
            result.url_or_keywords = keyword
            result.target_url_reached = target_url
            result.search_engine = search_engine
            print(f"{Fore.WHITE}{search_engine.title()} Search: {keyword}")
            print(f"{Fore.WHITE}Target: {target_url}")
          except Exception as search_error:
            # Extract search query and engine from error message if possible
            error_msg = str(search_error)
            if "search results for query:" in error_msg:
              # Extract the query from error message like "...for query: 'keyword domain.com'"
              import re
              query_match = re.search(r"for query: '([^']+)'", error_msg)
              if query_match:
                result.url_or_keywords = query_match.group(1)
              else:
                result.url_or_keywords = "Search failed"
              
              # Extract search engine from error message
              if "DuckDuckGo" in error_msg:
                result.search_engine = "duckduckgo"
              elif "Bing" in error_msg:
                result.search_engine = "bing"
              elif "Yahoo" in error_msg:
                result.search_engine = "yahoo"
              else:
                result.search_engine = "unknown"
            else:
              result.url_or_keywords = "Search failed"
              result.search_engine = "unknown"
            # Re-raise the exception to be handled by outer try-catch
            raise search_error

        # Wait for page to fully load
        await page.wait_for_load_state('domcontentloaded')
        await asyncio.sleep(random.uniform(2, 5))

        # Human-like interactions
        await self._human_like_mouse_movement(page)
        await asyncio.sleep(random.uniform(1, 2))

        await self._human_like_scrolling(page)
        await asyncio.sleep(random.uniform(1, 3))

        # Random clicks and collect visited URLs
        clicks, visited_urls = await self._random_clicks(page)
        result.clicks = clicks
        result.other_urls_visited = visited_urls

        # Stay on page for random time (configured duration)
        settings = self.config['bot_settings']
        stay_time = random.uniform(
          settings['session_duration_min'], settings['session_duration_max'])
        print(f"{Fore.GREEN}Staying for {stay_time:.1f} seconds...")

        # During stay time, perform additional human-like actions
        end_time = time.time() + stay_time
        while time.time() < end_time:
          action = random.choice(['scroll', 'mouse', 'wait'])
          if action == 'scroll':
            await self._human_like_scrolling(page)
          elif action == 'mouse':
            await self._human_like_mouse_movement(page)
          else:
            await asyncio.sleep(random.uniform(5, 15))

        total_time = time.time() - start_time
        result.time_on_target_url = total_time
        result.success = True

        print(f"{Fore.GREEN}✓ Session completed successfully")
        print(f"{Fore.WHITE}Clicks: {clicks}")
        print(f"{Fore.WHITE}Time on site: {total_time:.1f}s")
        if visited_urls:
          print(f"{Fore.WHITE}Other URLs visited: {len(visited_urls)}")

        # Success! Break out of retry loop
        break

      except Exception as e:
        result.failure_reason = str(e)
        result.success = False
        print(f"{Fore.RED}✗ Session failed: {e}")

        # Only retry for connection/browser issues, not search failures
        if "not found in search results" in str(e) or "Failed to click target link" in str(e):
          self.logger.warning(f"Session {session_num} failed due to search issue: {e}")
          print(f"{Fore.YELLOW}Moving to next session (search-related failure)...")
          break  # Don't retry for search failures
        elif attempt < max_proxy_attempts - 1:
          print(f"{Fore.YELLOW}Retrying with different proxy...")
          await asyncio.sleep(random.uniform(2, 5))
        else:
          self.logger.error(
            f"Session {session_num} failed after {max_proxy_attempts} attempts: {e}")

      finally:
        # Cleanup
        try:
          if context:
            await context.close()
          if browser:
            await browser.close()
          if playwright:
            await playwright.stop()
        except Exception as e:
          self.logger.error(f"Cleanup error: {e}")

    return result

  def _generate_pdf_report(self, sessions: List[SessionResult], start_session: int):
    """Generate PDF report for sessions"""
    try:
      # Ensure reports directory exists
      self.reports_dir.mkdir(exist_ok=True)

      filename = f"Bot_Report_{start_session}-{start_session + len(sessions) - 1}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
      filepath = self.reports_dir / filename

      doc = SimpleDocTemplate(str(filepath), pagesize=A4)
      story = []
      styles = getSampleStyleSheet()

      # Title
      title_style = ParagraphStyle(
          'CustomTitle',
          parent=styles['Heading1'],
          fontSize=18,
          spaceAfter=30,
          alignment=1  # Center
      )
      story.append(Paragraph("Web Automation Bot Report", title_style))
      story.append(Spacer(1, 12))

      # Summary
      successful_sessions = sum(1 for s in sessions if s.success)
      failed_sessions = len(sessions) - successful_sessions

      summary_data = [
          ['Report Period',
           f"Sessions {start_session} - {start_session + len(sessions) - 1}"],
          ['Total Sessions', str(len(sessions))],
          ['Successful', str(successful_sessions)],
          ['Failed', str(failed_sessions)],
          ['Success Rate',
           f"{(successful_sessions/len(sessions)*100):.1f}%" if len(sessions) > 0 else "0%"],
          ['Generated', datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
      ]

      summary_table = Table(summary_data, colWidths=[2 * inch, 3 * inch])
      summary_table.setStyle(TableStyle([
          ('BACKGROUND', (0, 0), (-1, -1), colors.lightgrey),
          ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
          ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
          ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
          ('FONTSIZE', (0, 0), (-1, -1), 10),
          ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
          ('GRID', (0, 0), (-1, -1), 1, colors.black)
      ]))

      story.append(summary_table)
      story.append(Spacer(1, 20))

      # Sessions details
      story.append(Paragraph("Session Details", styles['Heading2']))
      story.append(Spacer(1, 12))

      for session in sessions:
        session_data = [
            [f"Session {session.session_number}", ""],
            ["Browser", session.browser],
            ["IP Address", session.ip_address],
            ["Location", session.ip_location],
            ["Route", session.web_route],
            ["Search Engine", session.search_engine.title() if session.search_engine else "N/A (Direct)"],
            ["URL/Keywords", session.url_or_keywords],
            ["Target URL Reached", session.target_url_reached or "N/A"],
            ["Time on Site", f"{session.time_on_target_url:.1f}s"],
            ["Clicks", str(session.clicks)],
            ["Other URLs", str(len(session.other_urls_visited))],
            ["Status",
             "✓ Success" if session.success else f"✗ Failed: {session.failure_reason}"],
            ["Timestamp", session.timestamp.strftime('%Y-%m-%d %H:%M:%S')]
        ]

        session_table = Table(session_data, colWidths=[1.5 * inch, 3.5 * inch])
        session_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (1, 0), colors.darkblue),
            ('TEXTCOLOR', (0, 0), (1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BACKGROUND', (0, 1), (-1, -1),
             colors.beige if session.success else colors.lightpink)
        ]))

        story.append(session_table)
        story.append(Spacer(1, 10))

      # Build PDF
      doc.build(story)
      print(f"\n{Fore.GREEN}📊 Report generated: {filepath}")
      self.logger.info(f"Report generated: {filepath}")
      return True

    except Exception as e:
      print(f"\n{Fore.RED}❌ Failed to generate PDF report: {e}")
      self.logger.error(f"Failed to generate PDF report: {e}")
      return False

  async def _test_proxy_connection(self, proxy: ProxyInfo) -> bool:
    """Test if proxy is working"""
    try:
      playwright = await async_playwright().start()

      proxy_config = {
          "server": f"http://{proxy.host}:{proxy.port}",
          "username": proxy.username,
          "password": proxy.password
      }

      # Use Chrome for proxy testing (most compatible)
      browser = await playwright.chromium.launch(
          headless=True,
          proxy=proxy_config
      )

      context = await browser.new_context()
      page = await context.new_page()

      # Try to access a simple page
      await page.goto("https://httpbin.org/ip", timeout=15000)
      content = await page.content()

      await browser.close()
      await playwright.stop()

      return "origin" in content.lower()

    except Exception as e:
      self.logger.debug(
        f"Proxy test failed for {proxy.host}:{proxy.port} - {e}")
      return False

  def _save_session_result(self, result: SessionResult):
    """Save session result to JSON file immediately after completion"""
    try:
      # Convert result to dictionary
      result_dict = {
          "session_number": result.session_number,
          "total_sessions": result.total_sessions,
          "browser": result.browser,
          "ip_address": result.ip_address,
          "ip_location": result.ip_location,
          "web_route": result.web_route,
          "url_or_keywords": result.url_or_keywords,
          "target_url_reached": result.target_url_reached,
          "other_urls_visited": result.other_urls_visited,
          "time_on_target_url": round(result.time_on_target_url, 2),
          "clicks": result.clicks,
          "success": result.success,
          "failure_reason": result.failure_reason,
          "timestamp": result.timestamp.isoformat()
      }

      # Load existing results or create new list
      if self.results_file.exists():
        try:
          with open(self.results_file, 'r') as f:
            all_results = json.load(f)
        except (json.JSONDecodeError, Exception):
          all_results = []
      else:
        all_results = []

      # Add new result
      all_results.append(result_dict)

      # Save back to file
      with open(self.results_file, 'w') as f:
        json.dump(all_results, f, indent=2)

      # Also update summary stats
      successful = sum(1 for r in all_results if r['success'])
      total = len(all_results)
      success_rate = (successful / total * 100) if total > 0 else 0

      summary = {
          "last_updated": datetime.now().isoformat(),
          "total_sessions_completed": total,
          "successful_sessions": successful,
          "failed_sessions": total - successful,
          "success_rate_percent": round(success_rate, 1),
          "latest_session": result_dict
      }

      # Save summary file
      with open(self.summary_file, 'w') as f:
        json.dump(summary, f, indent=2)

      print(f"{Fore.CYAN}📄 Results saved to {self.results_file}")
      print(
        f"{Fore.CYAN}📊 Progress: {total} sessions, {success_rate:.1f}% success rate")

    except Exception as e:
      self.logger.error(f"Failed to save session result: {e}")

  def _load_existing_results(self):
    """Load existing session results on startup"""
    try:
      # Look for the most recent results file in the results directory
      if self.results_dir.exists():
        result_files = list(self.results_dir.glob("session_results_*.json"))
        if result_files:
          # Get the most recent results file
          latest_results_file = max(
            result_files, key=lambda x: x.stat().st_mtime)

          with open(latest_results_file, 'r') as f:
            existing_data = json.load(f)

          # Update old format data to include new fields
          updated_data = []
          for result in existing_data:
            # Add missing target_url_reached field for backward compatibility
            if 'target_url_reached' not in result:
              # For old results, use the url_or_keywords as target_url_reached for direct visits
              # For search visits, we don't have the target URL info, so set it to None
              if result.get('web_route') == 'direct':
                result['target_url_reached'] = result.get('url_or_keywords')
              else:
                result['target_url_reached'] = None
            updated_data.append(result)

          total = len(updated_data)
          successful = sum(1 for r in updated_data if r['success'])

          if total > 0:
            print(
              f"{Fore.GREEN}📄 Found {total} existing session results in {latest_results_file.name}")
            print(
              f"{Fore.GREEN}📊 Previous success rate: {(successful/total*100):.1f}%")
            # Auto-continue with previous sessions (non-blocking)
            print(f"{Fore.GREEN}📈 Continuing from previous session...")

            # Copy updated data to current run's file
            with open(self.results_file, 'w') as f:
              json.dump(updated_data, f, indent=2, default=str)

            # Create updated summary
            summary = {
                "last_updated": datetime.now().isoformat(),
                "total_sessions_completed": total,
                "successful_sessions": successful,
                "failed_sessions": total - successful,
                "success_rate_percent": round((successful / total * 100), 1),
                "continued_from": latest_results_file.name
            }

            with open(self.summary_file, 'w') as f:
              json.dump(summary, f, indent=2)

    except Exception as e:
      self.logger.error(f"Error loading existing results: {e}")

  async def run_bot(self):
    """Main bot execution function"""
    print(f"{Fore.CYAN}{Style.BRIGHT}🤖 Web Automation Bot Starting...")
    print(f"{Fore.WHITE}📅 Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{Fore.YELLOW}🔗 Loaded {len(self.proxies)} proxies")
    print(f"{Fore.BLUE}📂 Reports directory: {self.reports_dir}")
    print(f"{Fore.BLUE}📂 Results directory: {self.results_dir}")
    print(f"{Fore.BLUE}📂 Logs directory: {self.logs_dir}")
    print(f"{Fore.WHITE}{'='*60}")

    # Load existing results
    self._load_existing_results()

    # Check French hours and ask user permission if outside hours
    override_hours = False
    if not self._is_french_hours():
      print(f"\n{Fore.YELLOW}⏰ Currently outside French business hours (8AM-10PM)")
      print(f"{Fore.YELLOW}The bot is configured to run only during French hours by default.")
      while True:
        response = input(f"\n{Fore.CYAN}Do you wish to run outside of French hours? (Y/N): ").upper().strip()
        if response in ['Y', 'YES']:
          override_hours = True
          print(f"{Fore.GREEN}✅ Bot will run outside normal hours")
          break
        elif response in ['N', 'NO']:
          override_hours = False
          print(f"{Fore.RED}❌ Bot will respect French hours and exit")
          print(f"{Fore.YELLOW}Please run the bot between 8AM-10PM French time")
          return
        else:
          print(f"{Fore.RED}Invalid input. Please enter Y or N.")
    else:
      print(f"{Fore.GREEN}✅ Running during French business hours (8AM-10PM)")
      override_hours = True  # Already in valid hours

    # Get daily session count
    daily_sessions = self._get_daily_session_count()
    print(f"{Fore.GREEN}Daily target: {daily_sessions} sessions")

    browser_types = [BrowserType.CHROME, BrowserType.FIREFOX, BrowserType.EDGE]

    try:
      for session_num in range(1, daily_sessions + 1):
        # Check if we should stop due to hours (only if not overridden)
        if not override_hours and not self._is_french_hours():
          print(f"\n{Fore.YELLOW}⏰ Now outside French hours. Stopping bot...")
          print(f"{Fore.WHITE}Sessions completed: {session_num - 1}/{daily_sessions}")
          break

        # Random browser selection
        browser_type = random.choice(browser_types)

        # Run session
        result = await self._run_single_session(session_num, daily_sessions, browser_type)
        self.session_results.append(result)

        # Save result immediately to file
        self._save_session_result(result)

        # Generate report every configured frequency
        report_freq = self.config['bot_settings']['report_frequency']
        if len(self.session_results) % report_freq == 0:
          start_session = len(self.session_results) - report_freq + 1
          report_sessions = self.session_results[-report_freq:]
          print(
            f"\n{Fore.CYAN}📊 Generating report for sessions {start_session}-{len(self.session_results)}...")
          success = self._generate_pdf_report(report_sessions, start_session)
          if not success:
            print(f"{Fore.RED}❌ Report generation failed")

        # Random delay between sessions
        delay = random.uniform(10, 60)  # 10-60 seconds
        if session_num < daily_sessions:
          print(f"{Fore.YELLOW}⏱️  Waiting {delay:.1f}s before next session...")
          await asyncio.sleep(delay)

    except KeyboardInterrupt:
      print(f"\n{Fore.YELLOW}Bot stopped by user")
    except Exception as e:
      print(f"\n{Fore.RED}Bot error: {e}")
      self.logger.error(f"Bot error: {e}")
    finally:
      # Generate final report if there are remaining sessions or any sessions at all
      if len(self.session_results) > 0:
        report_freq = self.config['bot_settings']['report_frequency']
        remaining_sessions = len(self.session_results) % report_freq

        if remaining_sessions != 0:
          # Generate report for remaining sessions
          start_session = len(self.session_results) - remaining_sessions + 1
          report_sessions = self.session_results[-remaining_sessions:]
          print(
            f"\n{Fore.CYAN}📊 Generating final report for remaining {remaining_sessions} sessions...")
          self._generate_pdf_report(report_sessions, start_session)
        elif len(self.session_results) < report_freq:
          # If total sessions is less than report frequency, generate report for all sessions
          print(
            f"\n{Fore.CYAN}📊 Generating final report for all {len(self.session_results)} sessions...")
          self._generate_pdf_report(self.session_results, 1)

      # Final summary
      successful = sum(1 for r in self.session_results if r.success)
      total = len(self.session_results)
      print(f"\n{Fore.CYAN}{'='*50}")
      print(f"{Fore.GREEN}🎯 Final Summary:")
      print(f"{Fore.WHITE}Total Sessions: {total}")
      print(f"{Fore.GREEN}Successful: {successful}")
      print(f"{Fore.RED}Failed: {total - successful}")
      print(
        f"{Fore.YELLOW}Success Rate: {(successful/total*100):.1f}%" if total > 0 else "")
      print(f"{Fore.CYAN}{'='*50}")


if __name__ == "__main__":
  try:
    # Check for mode arguments
    debug_mode = '--debug' in sys.argv or '--visible' in sys.argv
    headless_mode = '--headless' in sys.argv
    
    # Default to visible mode unless explicitly headless
    visible_mode = debug_mode or not headless_mode
    
    if visible_mode:
      print(f"{Fore.YELLOW}[VISIBLE] Browser will be visible")
    else:
      print(f"{Fore.CYAN}[HEADLESS] Browser will run in background")
    
    bot = WebAutomationBot(debug_mode=visible_mode)
    asyncio.run(bot.run_bot())
  except KeyboardInterrupt:
    print(f"\n{Fore.YELLOW}Bot stopped by user (Ctrl+C)")
  except Exception as e:
    print(f"\n{Fore.RED}Fatal error: {e}")
    print(f"{Fore.YELLOW}Check the logs for more details")
    if '--debug' not in sys.argv:
      print(f"{Fore.CYAN}Try running with --debug flag to see browser actions")
