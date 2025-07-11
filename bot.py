import asyncio
import random
import time
import json
import os
import sys
import re
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
import gc
import psutil

# Initialize colorama for colored terminal output
init(autoreset=True)


class BrowserType(Enum):
  CHROME = "chrome"
  FIREFOX = "firefox"
  EDGE = "edge"
  WEBKIT = "webkit"  # Playwright's Safari/WebKit engine
  BRAVE = "brave"    # Chromium-based, custom executable


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
      with open('config.json', 'r', encoding='utf-8') as f:
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
              "session_timeout": 300,  # 5 minutes default
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
          },
          "browser_weights": {
              "chromium": 40,
              "firefox": 35,
              "edge": 25
          },
          "visit_mode_weights": {
              "direct": 50,
              "search": 50
          },
          "anti_detection": {
              "viewports": [
                  { "width": 1024, "height": 768 }
              ],
              "mouse_movement_frequency": 3,
              "scroll_patterns": 4
          },
          "proxy_settings": {
              "rotation_enabled": True,
              "connection_timeout": 30,
              "retry_attempts": 3
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
    # Reintroduce anti_detection settings in browser context creation
    viewports = self.config['anti_detection']['viewports']
    viewport = random.choice(viewports)

    context = await browser.new_context(
        viewport=viewport,
        user_agent=self.ua.random,
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
      # Reintroduce anti_detection settings in scrolling behavior
      scroll_patterns = self.config['anti_detection']['scroll_patterns']

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
        # Ensure proper encoding of keywords (handle French characters)
        search_query = f"{keyword} {search_domain}"
        if isinstance(search_query, bytes):
            search_query = search_query.decode('utf-8')
        else:
            search_query = str(search_query)

        # Randomly select search engine
        search_engines = ['duckduckgo', 'bing', 'yahoo']
        selected_engine = random.choice(search_engines)

        if self.debug_mode:
            print(f"🔍 Using {selected_engine.title()} search engine")
            print(f"🔍 Search query: {search_query}")

        if selected_engine == 'duckduckgo':
            actual_url = await self._search_duckduckgo(page, search_query, search_domain)
        elif selected_engine == 'bing':
            actual_url = await self._search_bing(page, search_query, search_domain)
        else:  # yahoo
            actual_url = await self._search_yahoo(page, search_query, search_domain)

        return search_query, actual_url, selected_engine

  async def _type_unicode(self, element, text):
    """Type unicode text into an input element, character by character, to ensure correct encoding."""
    for char in text:
      await element.type(char)
      await asyncio.sleep(random.uniform(0.05, 0.15))

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
    await self._type_unicode(search_box, search_query)
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
    await self._type_unicode(search_box, search_query)
    await asyncio.sleep(random.uniform(0.5, 1.5))
    await page.keyboard.press('Enter')

    # Wait for Bing search results to appear (not just DOM loaded)
    try:
      # Wait for either the results container or at least one result item
      await page.wait_for_selector('#b_results, li.b_algo', timeout=15000)
      if self.debug_mode:
        print("  ✅ Bing results container loaded.")
    except Exception as e:
      if self.debug_mode:
        print(f"  ⚠️ Bing results did not appear in time: {e}")
      # Still try to proceed, but likely to fail
      await asyncio.sleep(2)

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
    await self._type_unicode(search_box, search_query)
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
    """Run a single automation session with timeout"""
    max_proxy_attempts = 3
    # Use session_timeout from config (default to 300 if not set)
    session_timeout = self.config['bot_settings'].get('session_timeout', 300)

    for attempt in range(max_proxy_attempts):
        # Reintroduce proxy_settings in proxy handling
        proxy = self._get_random_proxy()
        visit_mode = random.choices(
            [VisitMode.DIRECT, VisitMode.SEARCH],
            weights=[self.config['visit_mode_weights']['direct'], self.config['visit_mode_weights']['search']]
        )[0]

        result = SessionResult(
            session_number=session_num,
            total_sessions=total_sessions,
            browser=browser_type.value,
            ip_address="Unknown",
            ip_location="Unknown",
            web_route=visit_mode.value,
            url_or_keywords="",
            search_engine=None,
            target_url_reached=None,
            other_urls_visited=[],
            time_on_target_url=0.0,
            clicks=0,
            success=False,
            failure_reason=None,
            timestamp=datetime.now()
        )

        try:
            print(f"\n{Fore.CYAN}{'='*50}")
            print(f"{Fore.YELLOW}Session {session_num:03d}/{total_sessions} (Attempt {attempt + 1}/{max_proxy_attempts})")

            # Run session logic with timeout
            result = await asyncio.wait_for(
                self._execute_session(session_num, total_sessions, browser_type, proxy, visit_mode, result),
                timeout=session_timeout
            )

            # Log success or failure
            if result.success:
                self.logger.info(f"Session {session_num} completed successfully.")
            else:
                self.logger.warning(f"Session {session_num} failed: {result.failure_reason}")

            return result

        except asyncio.TimeoutError:
            result.failure_reason = f"Session timed out after {session_timeout} seconds."
            result.success = False
            self.logger.error(f"Session {session_num} timed out.")
            return result

        except Exception as e:
            result.failure_reason = str(e)
            result.success = False
            self.logger.error(f"Session {session_num} encountered an error: {e}")
            return result

    return result

  async def _execute_session(self, session_num: int, total_sessions: int, browser_type: BrowserType, proxy: ProxyInfo, visit_mode: VisitMode, result: SessionResult) -> SessionResult:
    """Execute the session logic"""
    playwright = None
    browser = None
    context = None

    try:
        playwright = await async_playwright().start()
        browser = await self._launch_browser(playwright, browser_type, proxy)
        context = await self._create_browser_context(browser, proxy, browser_type)
        page = await context.new_page()

        result.ip_address, result.ip_location = await self._get_ip_info(page)

        if visit_mode == VisitMode.DIRECT:
            target_url = await self._visit_direct(page)
            result.url_or_keywords = target_url
            result.target_url_reached = target_url
        else:
            try:
                keyword, target_url, search_engine = await self._visit_via_search(page)
                result.url_or_keywords = keyword
                result.target_url_reached = target_url
                result.search_engine = search_engine
            except Exception as search_error:
                error_msg = str(search_error)
                if "search results for query:" in error_msg:
                    query_match = re.search(r"for query: '([^']+)'", error_msg)
                    if query_match:
                        result.url_or_keywords = query_match.group(1)
                    else:
                        result.url_or_keywords = "Search failed"

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
                raise search_error

        await self._perform_human_interactions(page, result)

        result.success = True

    except Exception as e:
        result.failure_reason = str(e)
        result.success = False

    finally:
        if context:
            await context.close()
        if browser:
            await browser.close()
        if playwright:
            await playwright.stop()

    return result

  async def _perform_human_interactions(self, page: Page, result: SessionResult):
    """Perform human-like interactions on the page"""
    await asyncio.sleep(random.uniform(2, 5))
    await self._human_like_mouse_movement(page)
    await asyncio.sleep(random.uniform(1, 2))
    await self._human_like_scrolling(page)
    await asyncio.sleep(random.uniform(1, 3))

    clicks, visited_urls = await self._random_clicks(page)
    result.clicks = clicks
    result.other_urls_visited = visited_urls

    settings = self.config['bot_settings']
    stay_time = random.uniform(settings['session_duration_min'], settings['session_duration_max'])
    end_time = time.time() + stay_time

    while time.time() < end_time:
        action = random.choice(['scroll', 'mouse', 'wait'])
        if action == 'scroll':
            await self._human_like_scrolling(page)
        elif action == 'mouse':
            await self._human_like_mouse_movement(page)
        else:
            await asyncio.sleep(random.uniform(5, 15))

  def _display_session_results(self, result: SessionResult):
    """Display session results in a well-organized format in the terminal"""
    print(f"\n{Fore.CYAN}{'='*80}")
    print(f"{Fore.YELLOW}📊 SESSION RESULTS")
    print(f"{Fore.CYAN}{'='*80}")
    
    # Status color coding
    status_color = Fore.GREEN if result.success else Fore.RED
    status_icon = "✅" if result.success else "❌"
    status_text = "SUCCESS" if result.success else "FAILED"
    
    print(f"{Fore.WHITE}📋 Session Number:     {Fore.CYAN}{result.session_number:03d}/{result.total_sessions}")
    print(f"{Fore.WHITE}🌐 Browser:           {Fore.CYAN}{result.browser.title()}")
    print(f"{Fore.WHITE}🔗 IP Address:        {Fore.CYAN}{result.ip_address}")
    print(f"{Fore.WHITE}📍 IP Location:       {Fore.CYAN}{result.ip_location}")
    print(f"{Fore.WHITE}🛣️  Web Route:         {Fore.CYAN}{result.web_route.title()}")
    
    if result.search_engine:
        print(f"{Fore.WHITE}🔍 Search Engine:     {Fore.CYAN}{result.search_engine.title()}")
    
    print(f"{Fore.WHITE}🎯 URL/Keywords:      {Fore.CYAN}{result.url_or_keywords}")
    
    if result.target_url_reached:
        print(f"{Fore.WHITE}🎯 Target URL:        {Fore.CYAN}{result.target_url_reached}")
    else:
        print(f"{Fore.WHITE}🎯 Target URL:        {Fore.YELLOW}Not Reached")
    
    if result.other_urls_visited:
        print(f"{Fore.WHITE}🔗 Other URLs:        {Fore.CYAN}{', '.join(result.other_urls_visited)}")
    else:
        print(f"{Fore.WHITE}🔗 Other URLs:        {Fore.YELLOW}None")
    
    print(f"{Fore.WHITE}⏱️  Time on Target:    {Fore.CYAN}{result.time_on_target_url:.1f} seconds")
    print(f"{Fore.WHITE}🖱️  Clicks:            {Fore.CYAN}{result.clicks}")
    print(f"{Fore.WHITE}📅 Timestamp:         {Fore.CYAN}{result.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Status with color coding
    print(f"{Fore.WHITE}📊 Status:            {status_color}{status_icon} {status_text}")
    
    if not result.success and result.failure_reason:
        print(f"{Fore.WHITE}❌ Failure Reason:    {Fore.RED}{result.failure_reason}")
    
    print(f"{Fore.CYAN}{'='*80}")
    
    # Quick summary stats
    total_sessions = len(self.session_results)
    successful_sessions = sum(1 for r in self.session_results if r.success)
    success_rate = (successful_sessions / total_sessions * 100) if total_sessions > 0 else 0
    
    print(f"{Fore.WHITE}📈 Running Total: {Fore.CYAN}{total_sessions} sessions | {Fore.GREEN}{successful_sessions} successful | {Fore.RED}{total_sessions - successful_sessions} failed | {Fore.YELLOW}{success_rate:.1f}% success rate")
    print(f"{Fore.CYAN}{'='*80}")

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
          "search_engine": result.search_engine,
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
          with open(self.results_file, 'r', encoding='utf-8') as f:
            all_results = json.load(f)
        except (json.JSONDecodeError, Exception):
          all_results = []
      else:
        all_results = []

      # Add new result
      all_results.append(result_dict)

      # Save back to file
      with open(self.results_file, 'w', encoding='utf-8') as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)

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
      with open(self.summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

      print(f"{Fore.CYAN}📄 Results saved to {self.results_file}")
      print(
        f"{Fore.CYAN}📊 Progress: {total} sessions, {success_rate:.1f}% success rate")

    except Exception as e:
      self.logger.error(f"Failed to save session result: {e}")

  def _load_existing_results(self):
    """Load existing session results on startup and ask user if they want to continue from previous session."""
    try:
      # Look for the most recent results file in the results directory
      if self.results_dir.exists():
        result_files = list(self.results_dir.glob("session_results_*.json"))
        if result_files:
          # Get the most recent results file
          latest_results_file = max(
            result_files, key=lambda x: x.stat().st_mtime)

          with open(latest_results_file, 'r', encoding='utf-8') as f:
            existing_data = json.load(f)

          # Update old format data to include new fields
          updated_data = []
          for result in existing_data:
            # Add missing target_url_reached field for backward compatibility
            if 'target_url_reached' not in result:
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
            # Ask user if they want to continue from previous session
            while True:
              response = input(f"{Fore.CYAN}Do you want to continue from the previous session? (Y/N): ").strip().upper()
              if response in ['Y', 'YES']:
                print(f"{Fore.GREEN}📈 Continuing from previous session...")
                # Copy updated data to current run's file
                with open(self.results_file, 'w', encoding='utf-8') as f:
                  json.dump(updated_data, f, indent=2, default=str, ensure_ascii=False)
                # Create updated summary
                summary = {
                    "last_updated": datetime.now().isoformat(),
                    "total_sessions_completed": total,
                    "successful_sessions": successful,
                    "failed_sessions": total - successful,
                    "success_rate_percent": round((successful / total * 100), 1),
                    "continued_from": latest_results_file.name
                }
                with open(self.summary_file, 'w', encoding='utf-8') as f:
                  json.dump(summary, f, indent=2, ensure_ascii=False)
                break
              elif response in ['N', 'NO']:
                print(f"{Fore.YELLOW}Starting a new session. Previous results will not be loaded.")
                # Do not copy previous results
                break
              else:
                print(f"{Fore.RED}Invalid response. Please enter Y or N.")
    except Exception as e:
      self.logger.error(f"Error loading existing results: {e}")

  def _log_resource_usage(self, session_num=None):
    """Log memory and resource usage for diagnostics"""
    process = psutil.Process(os.getpid())
    mem_mb = process.memory_info().rss / 1024 / 1024
    open_files = process.open_files()
    children = process.children(recursive=True)
    msg = f"[Resource] Memory: {mem_mb:.1f} MB | Open files: {len(open_files)} | Child processes: {len(children)}"
    if session_num is not None:
        msg = f"Session {session_num}: " + msg
    print(msg)
    self.logger.info(msg)

  async def _restart_playwright(self):
        """Forcefully restart Playwright to clear any lingering resources/processes."""
        gc.collect()
        self._log_resource_usage()
        print("[Playwright] Restarted Playwright and forced garbage collection.")
        self.logger.info("[Playwright] Restarted Playwright and forced garbage collection.")

  async def _launch_browser(self, playwright, browser_type: BrowserType, proxy: ProxyInfo):
    """Launch browser with proxy configuration"""
    proxy_config = {
        "server": f"http://{proxy.host}:{proxy.port}",
        "username": proxy.username,
        "password": proxy.password
    }

    if browser_type == BrowserType.FIREFOX:
        return await playwright.firefox.launch(
            headless=not self.debug_mode,
            proxy=proxy_config
        )
    elif browser_type == BrowserType.EDGE:
        return await playwright.chromium.launch(
            headless=not self.debug_mode,
            proxy=proxy_config,
            channel="msedge"
        )
    elif browser_type == BrowserType.BRAVE:
        # For Brave, use the Chromium launcher with Brave's binary path (Windows default)
        brave_path = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
        return await playwright.chromium.launch(
            headless=not self.debug_mode,
            proxy=proxy_config,
            executable_path=brave_path
        )
    elif browser_type == BrowserType.WEBKIT:
        return await playwright.webkit.launch(
            headless=not self.debug_mode,
            proxy=proxy_config
        )
    else:  # Chrome (default)
        return await playwright.chromium.launch(
            headless=not self.debug_mode,
            proxy=proxy_config
        )

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

    # Check French hours and ask user permission if outside hours only once
    override_hours = False
    if not self._is_french_hours():
        print(f"\n{Fore.YELLOW}⏰ Currently outside French business hours (8AM-10PM)")
        print(f"{Fore.YELLOW}The bot is configured to run only during French hours by default.")
        while True:
            response = input(f"\n{Fore.CYAN}Do you wish to run outside of French hours? (Y/N): ").upper().strip()
            if response in ['Y', 'YES']:
                override_hours = True
                break
            elif response in ['N', 'NO']:
                override_hours = False
                break
            else:
                print(f"{Fore.RED}Invalid response. Please enter Y or N.")
    else:
        print(f"{Fore.GREEN}✅ Running during French business hours (8AM-10PM)")
        override_hours = True  # Already in valid hours

    # Get daily session count
    daily_sessions = self._get_daily_session_count()
    print(f"{Fore.GREEN}Daily target: {daily_sessions} sessions")

    browser_types = [BrowserType.CHROME, BrowserType.FIREFOX, BrowserType.EDGE, BrowserType.WEBKIT, BrowserType.BRAVE]

    try:
        for session_num in range(1, daily_sessions + 1):
            # Check if we should stop due to hours (only if overridden)
            if not override_hours and not self._is_french_hours():
                print(f"{Fore.RED}⏰ French hours ended. Stopping bot.")
                break

            # Reintroduce browser_weights for random browser selection
            browser_type = random.choices(
                browser_types,
                weights=[
                    self.config['browser_weights']['chromium'],
                    self.config['browser_weights']['firefox'],
                    self.config['browser_weights']['edge'],
                    self.config['browser_weights']['webkit'],
                    self.config['browser_weights']['brave']
                ]
            )[0]

            # Run session
            result = await self._run_single_session(session_num, daily_sessions, browser_type)
            self.session_results.append(result)

            # Display session results in terminal
            self._display_session_results(result)

            # Save result immediately to file
            self._save_session_result(result)

            # Periodic resource logging and cleanup
            if session_num % 25 == 0:
              self._log_resource_usage(session_num)
              gc.collect()
              print(f"[GC] Garbage collection forced after {session_num} sessions.")
              await asyncio.sleep(random.uniform(2, 5))

            # Periodic Playwright restart (every 50 sessions)
            if session_num % 50 == 0:
              await self._restart_playwright()
              await asyncio.sleep(random.uniform(2, 5))

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
            # Always force garbage collection after each session
            gc.collect()
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

  def _generate_pdf_report(self, report_sessions, start_session):
    """Generate a PDF report for the given sessions, with session details in tabular format."""
    try:
      from reportlab.lib.pagesizes import A4
      from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
      from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
      from reportlab.lib import colors

      # Prepare report filename
      end_session = start_session + len(report_sessions) - 1
      report_name = f"report_{self.run_timestamp}_sessions_{start_session}_to_{end_session}.pdf"
      report_path = os.path.join(self.reports_dir, report_name)

      doc = SimpleDocTemplate(report_path, pagesize=A4)
      styles = getSampleStyleSheet()
      elements = []

      # Title
      title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=30,
        alignment=1  # Center
      )
      elements.append(Paragraph("Web Automation Bot Report", title_style))
      elements.append(Spacer(1, 12))

      # Summary
      total = len(report_sessions)
      success = sum(1 for s in report_sessions if s.success)
      fail = total - success
      summary_data = [
        ['Report Period', f"Sessions {start_session} - {end_session}"],
        ['Total Sessions', str(total)],
        ['Successful', str(success)],
        ['Failed', str(fail)],
        ['Success Rate', f"{(success/total*100):.1f}%" if total > 0 else "0%"],
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
      elements.append(summary_table)
      elements.append(Spacer(1, 20))

      # Session details as 2-column tables
      elements.append(Paragraph("Session Details", styles['Heading2']))
      elements.append(Spacer(1, 12))
      for session in report_sessions:
        elements.append(Paragraph(f"Session {session.session_number}", styles['Heading3']))
        # Use Paragraph for all text fields to ensure Unicode
        session_data = [
          ["Browser", Paragraph(str(session.browser), styles['Normal'])],
          ["IP Address", Paragraph(str(session.ip_address), styles['Normal'])],
          ["IP Location", Paragraph(str(session.ip_location), styles['Normal'])],
          ["Web Route", Paragraph(str(session.web_route), styles['Normal'])],
          ["Search Engine", Paragraph(str(session.search_engine.title()) if session.search_engine else "N/A (Direct)", styles['Normal'])],
          ["URL/Keywords", Paragraph(str(session.url_or_keywords), styles['Normal'])],
          ["Target URL Reached", Paragraph(str(session.target_url_reached) if session.target_url_reached else "N/A", styles['Normal'])],
          ["Other URLs Visited", Paragraph(", ".join(map(str, session.other_urls_visited)) if session.other_urls_visited else "None", styles['Normal'])],
          ["Time on Target URL", Paragraph(f"{session.time_on_target_url:.1f} seconds", styles['Normal'])],
          ["Clicks", Paragraph(str(session.clicks), styles['Normal'])],
          ["Status", Paragraph("✓ Success" if session.success else f"✗ Failed: {session.failure_reason}", styles['Normal'])],
          ["Timestamp", Paragraph(session.timestamp.strftime('%Y-%m-%d %H:%M:%S'), styles['Normal'])],
        ]
        session_table = Table(session_data, colWidths=[1.7*inch, 4.8*inch])
        session_table.setStyle(TableStyle([
          ('BACKGROUND', (0, 0), (1, 0), colors.darkblue),
          ('TEXTCOLOR', (0, 0), (1, 0), colors.white),
          ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
          ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
          ('FONTSIZE', (0, 0), (-1, -1), 9),
          ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
          ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
          ('BACKGROUND', (0, 1), (-1, -1), colors.beige if session.success else colors.lightpink)
        ]))
        elements.append(session_table)
        elements.append(Spacer(1, 10))

      doc.build(elements)
      self.logger.info(f"[Report] PDF report generated: {report_path}")
      print(f"{Fore.GREEN}PDF report generated: {report_path}")
      return True
    except Exception as e:
      self.logger.error(f"Failed to generate PDF report: {e}")
      print(f"{Fore.RED}Failed to generate PDF report: {e}")
      return False


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
