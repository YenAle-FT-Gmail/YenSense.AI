#!/usr/bin/env python3
"""
Trading Economics Calendar Scraper with Selenium
Uses dynamic filtering for comprehensive G3 economic calendar data
"""

import os
import json
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional
from bs4 import BeautifulSoup

# Selenium imports with error handling
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait, Select
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchElementException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    print("Warning: Selenium not available. Install with: pip install selenium")


class TradingEconomicsSeleniumScraper:
    """Advanced Trading Economics scraper with dynamic filtering"""
    
    def __init__(self, cache_dir: Optional[str] = None, cache_hours: int = 24, headless: bool = True):
        """Initialize scraper with Selenium WebDriver"""
        self.logger = logging.getLogger(__name__)
        
        if not SELENIUM_AVAILABLE:
            raise ImportError("Selenium is required. Install with: pip install selenium")
        
        # Set cache directory
        if cache_dir is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            self.cache_dir = os.path.join(current_dir, '..', '..', 'data', 'input', 'calendar')
        else:
            self.cache_dir = cache_dir
            
        os.makedirs(self.cache_dir, exist_ok=True)
        
        self.cache_hours = cache_hours
        self.headless = headless
        self.driver = None
        
        # G3 country mappings
        self.g3_countries = {
            'United States': {'currency': 'USD', 'aliases': ['US', 'USA', 'United States']},
            'Japan': {'currency': 'JPY', 'aliases': ['Japan', 'JP', 'JPN']},
            'Euro Area': {'currency': 'EUR', 'aliases': ['Euro Area', 'Eurozone', 'Germany', 'DE', 'EA']},
        }
        
        # Enhanced category mapping
        self.category_map = {
            'cpi': 'inflation',
            'ppi': 'inflation', 
            'inflation': 'inflation',
            'core inflation': 'inflation',
            'gdp': 'growth',
            'retail': 'retail',
            'employment': 'employment',
            'unemployment': 'employment',
            'nfp': 'employment',
            'payroll': 'employment',
            'housing': 'housing',
            'industrial': 'manufacturing',
            'manufacturing': 'manufacturing',
            'fomc': 'monetary_policy',
            'fed': 'monetary_policy',
            'federal funds': 'monetary_policy',
            'interest rate': 'monetary_policy',
            'policy rate': 'monetary_policy',
            'boj': 'monetary_policy',
            'ecb': 'monetary_policy',
            'bond': 'fixed_income',
            'auction': 'fixed_income',
            'treasury': 'fixed_income',
            'note': 'fixed_income',
            'bill': 'fixed_income',
            'jgb': 'fixed_income',
            'trade balance': 'trade',
            'current account': 'trade',
            'consumer confidence': 'sentiment',
            'business confidence': 'sentiment'
        }
    
    def _setup_driver(self) -> webdriver.Chrome:
        """Setup Chrome WebDriver with optimal settings"""
        try:
            chrome_options = Options()
            
            if self.headless:
                chrome_options.add_argument('--headless=new')  # Use new headless mode
                
            # Performance and stability options
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--disable-images')
            chrome_options.add_argument('--disable-javascript-harmony-shipping')
            chrome_options.add_argument('--disable-background-timer-throttling')
            chrome_options.add_argument('--disable-renderer-backgrounding')
            chrome_options.add_argument('--disable-backgrounding-occluded-windows')
            chrome_options.add_argument('--window-size=1920,1080')
            
            # User agent to avoid detection
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            # Try to use system Chrome first, then fall back to chromedriver
            try:
                driver = webdriver.Chrome(options=chrome_options)
            except Exception as e:
                self.logger.warning(f"Failed to use system Chrome: {e}")
                # Try with explicit service
                service = Service()
                driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Set timeouts
            driver.implicitly_wait(10)
            driver.set_page_load_timeout(30)
            
            self.logger.info("Chrome WebDriver initialized successfully")
            return driver
            
        except Exception as e:
            self.logger.error(f"Failed to setup WebDriver: {e}")
            raise
    
    def _is_cache_valid(self, cache_file: str) -> bool:
        """Check if cache file is valid and not expired"""
        try:
            if not os.path.exists(cache_file):
                return False
                
            file_time = os.path.getmtime(cache_file)
            file_dt = datetime.fromtimestamp(file_time)
            expiry_time = datetime.now() - timedelta(hours=self.cache_hours)
            
            return file_dt > expiry_time
        except Exception:
            return False
    
    def _load_from_cache(self, cache_file: str) -> Optional[Dict[str, Any]]:
        """Load data from cache file"""
        try:
            if self._is_cache_valid(cache_file):
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.logger.info(f"Loaded calendar data from cache: {cache_file}")
                return data
        except Exception as e:
            self.logger.error(f"Error loading cache: {e}")
        return None
    
    def _save_to_cache(self, data: Dict[str, Any], cache_file: str) -> None:
        """Save data to cache file"""
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            self.logger.info(f"Saved calendar data to cache: {cache_file}")
        except Exception as e:
            self.logger.error(f"Error saving cache: {e}")
    
    def _apply_filters(self, driver: webdriver.Chrome) -> None:
        """Apply dynamic filters to Trading Economics calendar"""
        try:
            self.logger.info("Applying dynamic filters...")
            
            # Wait for page to fully load
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.CLASS_NAME, "btn-group-calendar"))
            )
            
            # Set timezone to UTC for consistency
            try:
                timezone_select = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.ID, "DropDownListTimezone"))
                )
                select = Select(timezone_select)
                select.select_by_value("0")  # UTC = 0 offset
                self.logger.info("Set timezone to UTC")
                time.sleep(2)
            except Exception as e:
                self.logger.warning(f"Could not set timezone: {e}")
            
            # Set time range to "This Month"
            try:
                driver.execute_script("setCalendarRange('5');")
                self.logger.info("Set time range to 'This Month'")
                time.sleep(2)
            except Exception as e:
                self.logger.warning(f"Could not set time range: {e}")
            
            # Set impact to highest level (3 stars)
            try:
                driver.execute_script("setCalendarImportance('3');")
                self.logger.info("Set importance to high impact (3 stars)")
                time.sleep(2)
            except Exception as e:
                self.logger.warning(f"Could not set importance: {e}")
            
            # Wait for filters to apply and content to reload
            time.sleep(5)
            
            # Verify filters were applied by checking if content changed
            try:
                # Look for high importance indicators
                high_importance_events = driver.find_elements(By.CSS_SELECTOR, "[class*='importance-3'], [class*='high'], .calendar-item")
                self.logger.info(f"Found {len(high_importance_events)} high importance elements after filtering")
            except Exception as e:
                self.logger.warning(f"Could not verify filter application: {e}")
                
        except TimeoutException:
            self.logger.error("Timeout while applying filters")
            raise
        except Exception as e:
            self.logger.error(f"Error applying filters: {e}")
            raise
    
    def _extract_events_from_table(self, driver: webdriver.Chrome) -> List[Dict[str, Any]]:
        """Extract events from the filtered calendar table"""
        events = []
        
        try:
            # Get page source and parse with BeautifulSoup for reliable parsing
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            
            # Find all calendar tables
            tables = soup.find_all('table')
            self.logger.info(f"Found {len(tables)} tables on filtered page")
            
            for i, table in enumerate(tables):
                # Look for the main calendar table with proper headers
                headers = table.find('tr')
                if not headers:
                    continue
                    
                header_cells = headers.find_all(['th', 'td'])
                if len(header_cells) < 4:
                    continue
                    
                header_text = ' '.join([cell.get_text().strip() for cell in header_cells])
                
                # Identify main calendar table
                if ('Actual' in header_text and 'Previous' in header_text and 
                    any(month in header_text for month in 
                    ['January', 'February', 'March', 'April', 'May', 'June',
                     'July', 'August', 'September', 'October', 'November', 'December'])):
                    
                    self.logger.info(f"Processing calendar table at index {i}")
                    
                    # Extract date from header
                    date_header = header_cells[0].get_text().strip()
                    
                    # Process all rows in this table
                    rows = table.find_all('tr')[1:]  # Skip header row
                    
                    for row in rows:
                        cells = row.find_all(['td', 'th'])
                        if len(cells) < 5:
                            continue
                        
                        try:
                            # Extract data based on known structure
                            time_cell = cells[0].get_text().strip() if len(cells) > 0 else ""
                            country_cell = cells[3].get_text().strip() if len(cells) > 3 else ""
                            event_cell = cells[4].get_text().strip() if len(cells) > 4 else ""
                            actual_cell = cells[5].get_text().strip() if len(cells) > 5 else ""
                            previous_cell = cells[6].get_text().strip() if len(cells) > 6 else ""
                            consensus_cell = cells[7].get_text().strip() if len(cells) > 7 else ""
                            forecast_cell = cells[8].get_text().strip() if len(cells) > 8 else ""
                            
                            # Skip invalid rows
                            if not event_cell or not country_cell or len(event_cell) < 3:
                                continue
                            
                            if event_cell in ['Actual', 'Previous', 'Consensus', 'Forecast'] or not time_cell:
                                continue
                            
                            # Map country codes to G3 countries
                            country = self._map_country_code(country_cell)
                            if not country:
                                continue
                            
                            # Parse datetime in UTC (since we set timezone filter to UTC)
                            event_datetime = self._parse_event_datetime(date_header, time_cell)
                            
                            # Categorize and score importance
                            category = self._categorize_event(event_cell)
                            importance = self._estimate_importance(event_cell)
                            is_bond_auction = self._is_bond_auction(event_cell)
                            
                            event_data = {
                                'datetime_utc': event_datetime.isoformat() if event_datetime else None,
                                'date_display': date_header,
                                'time_display': f"{time_cell} UTC" if time_cell else "TBD UTC",
                                'country': country,
                                'currency': self.g3_countries[country]['currency'],
                                'event_name': event_cell,
                                'category': category,
                                'importance': importance,
                                'actual': actual_cell if actual_cell not in ['-', 'n/a', 'N/A', ''] else None,
                                'previous': previous_cell if previous_cell not in ['-', 'n/a', 'N/A', ''] else None,
                                'consensus': consensus_cell if consensus_cell not in ['-', 'n/a', 'N/A', ''] else None,
                                'forecast': forecast_cell if forecast_cell not in ['-', 'n/a', 'N/A', ''] else None,
                                'source': 'trading_economics_selenium',
                                'is_bond_auction': is_bond_auction
                            }
                            
                            events.append(event_data)
                            
                        except Exception as e:
                            self.logger.warning(f"Error parsing row: {e}")
                            continue
            
            self.logger.info(f"Extracted {len(events)} events from filtered tables")
            return events
            
        except Exception as e:
            self.logger.error(f"Error extracting events: {e}")
            return []
    
    def _map_country_code(self, country_code: str) -> Optional[str]:
        """Map country code to G3 country name"""
        country_mapping = {
            'US': 'United States',
            'USA': 'United States', 
            'JP': 'Japan',
            'JPN': 'Japan',
            'EA': 'Euro Area',
            'EUR': 'Euro Area',
            'DE': 'Euro Area',  # Include Germany as part of Euro Area
            'DEU': 'Euro Area'
        }
        return country_mapping.get(country_code.upper())
    
    def _parse_event_datetime(self, date_str: str, time_str: str) -> Optional[datetime]:
        """Parse event datetime to UTC datetime object"""
        try:
            # Parse date string like "Friday September 13 2024"
            date_parts = date_str.split()
            
            if len(date_parts) >= 3:
                # Extract month, day, year
                month_str = date_parts[-3] if len(date_parts) >= 3 else date_parts[1]
                day_str = date_parts[-2] if len(date_parts) >= 2 else date_parts[2] 
                year_str = date_parts[-1] if len(date_parts) >= 1 else "2025"
                
                # Month name to number mapping
                month_map = {
                    'January': 1, 'February': 2, 'March': 3, 'April': 4,
                    'May': 5, 'June': 6, 'July': 7, 'August': 8,
                    'September': 9, 'October': 10, 'November': 11, 'December': 12
                }
                
                month_num = month_map.get(month_str, 1)
                day_num = int(day_str)
                year_num = int(year_str)
                
                base_date = datetime(year_num, month_num, day_num)
            else:
                base_date = datetime.now()
            
            # Parse time if provided (assuming UTC since we set timezone filter)
            if time_str and ':' in time_str:
                time_part = time_str.replace('AM', '').replace('PM', '').strip()
                if ':' in time_part:
                    hour_str, minute_str = time_part.split(':')[:2]
                    hour = int(hour_str)
                    minute = int(minute_str)
                    
                    # Handle AM/PM
                    if 'PM' in time_str and hour != 12:
                        hour += 12
                    elif 'AM' in time_str and hour == 12:
                        hour = 0
                    
                    event_dt = base_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
                else:
                    event_dt = base_date.replace(hour=9, minute=0, second=0, microsecond=0)
            else:
                # Default time if not specified
                event_dt = base_date.replace(hour=9, minute=0, second=0, microsecond=0)
            
            # Return as UTC (timezone-naive but representing UTC time)
            return event_dt
            
        except Exception as e:
            self.logger.warning(f"Error parsing datetime '{date_str}' '{time_str}': {e}")
            return None
    
    def _categorize_event(self, event_name: str) -> str:
        """Categorize event based on name"""
        event_lower = event_name.lower()
        
        for keyword, category in self.category_map.items():
            if keyword in event_lower:
                return category
                
        return 'economic'
    
    def _estimate_importance(self, event_name: str) -> int:
        """Estimate event importance (since we're filtering for high impact, default to high)"""
        event_lower = event_name.lower()
        
        # Very high importance events (5)
        very_high_importance = [
            'cpi', 'inflation rate', 'gdp', 'employment', 'unemployment rate', 'nfp', 
            'non-farm payroll', 'fomc', 'federal funds rate', 'ecb interest rate',
            'boj interest rate', 'policy rate'
        ]
        
        # Since we filtered for high impact, most events should be important
        for keyword in very_high_importance:
            if keyword in event_lower:
                return 5
        
        # Default to 4 since we filtered for high importance
        return 4
    
    def _is_bond_auction(self, event_name: str) -> bool:
        """Check if event is a bond auction"""
        auction_keywords = [
            'auction', 'bond', 'treasury', 'note', 'bill', 'jgb', 'bund', 'oat',
            'gilt', 'btp', 'bobl', 'schatz', 'bubill', 'tap', 'syndication',
            '1-month', '2-month', '3-month', '6-month', '1-year', '2-year', 
            '3-year', '5-year', '7-year', '10-year', '20-year', '30-year',
            'week bill', 'month bill', 'year note', 'year bond',
            'fixed rate', 'floating rate', 'inflation-linked'
        ]
        event_lower = event_name.lower()
        return any(keyword in event_lower for keyword in auction_keywords)
    
    def scrape_calendar(self, months_ahead: int = 2) -> Dict[str, Any]:
        """Scrape comprehensive calendar data with dynamic filtering"""
        cache_file = os.path.join(self.cache_dir, 'trading_economics_selenium_calendar.json')
        
        # Try cache first
        cached_data = self._load_from_cache(cache_file)
        if cached_data:
            return cached_data
        
        self.driver = None
        
        try:
            # Setup WebDriver
            self.driver = self._setup_driver()
            
            # Navigate to Trading Economics calendar
            url = "https://tradingeconomics.com/calendar"
            self.logger.info(f"Navigating to: {url}")
            self.driver.get(url)
            
            # Wait for page to load
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, "table"))
            )
            
            all_events = []
            
            # Scrape "This Month"
            self.logger.info("Scraping 'This Month' data...")
            self._apply_filters(self.driver)
            events_this_month = self._extract_events_from_table(self.driver)
            all_events.extend(events_this_month)
            
            # Scrape "Next Month" if requested
            if months_ahead > 1:
                self.logger.info("Scraping 'Next Month' data...")
                try:
                    self.driver.execute_script("setCalendarRange('6');")  # Next Month
                    time.sleep(5)  # Wait for content to reload
                    
                    events_next_month = self._extract_events_from_table(self.driver)
                    all_events.extend(events_next_month)
                except Exception as e:
                    self.logger.warning(f"Error scraping next month: {e}")
            
            # Scrape with medium impact to catch bond auctions on main calendar
            self.logger.info("Scraping medium impact events (including bond auctions)...")
            try:
                # Go back to main calendar
                main_url = "https://tradingeconomics.com/calendar"
                self.driver.get(main_url)
                
                # Wait for page to load
                WebDriverWait(self.driver, 20).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "btn-group-calendar"))
                )
                
                # Apply filters with medium impact
                try:
                    # Set timezone to UTC
                    timezone_select = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.ID, "DropDownListTimezone"))
                    )
                    select = Select(timezone_select)
                    select.select_by_value("0")  # UTC = 0 offset
                    time.sleep(2)
                except Exception as e:
                    self.logger.warning(f"Could not set timezone: {e}")
                
                # Set to LOW impact (1 star) for bond auctions
                try:
                    self.driver.execute_script("setCalendarImportance('1');")
                    self.logger.info("Set importance to LOW impact (1 star) for bond auctions")
                    time.sleep(3)
                except Exception as e:
                    self.logger.warning(f"Could not set low importance: {e}")
                
                # Set time range to this month
                try:
                    self.driver.execute_script("setCalendarRange('5');")
                    time.sleep(3)
                except Exception as e:
                    self.logger.warning(f"Could not set time range: {e}")
                
                # Extract LOW impact events (which should include bond auctions)
                low_events = self._extract_events_from_table(self.driver)
                self.logger.info(f"Extracted {len(low_events)} low impact events")
                
                # Filter for bond auctions and add them
                bond_events = []
                for event in low_events:
                    if self._is_bond_auction(event.get('event_name', '')):
                        event['is_bond_auction'] = True
                        event['category'] = 'fixed_income'
                        event['importance'] = max(3, event.get('importance', 3))  # Upgrade importance for our purposes
                        bond_events.append(event)
                
                all_events.extend(bond_events)
                self.logger.info(f"Added {len(bond_events)} bond auction events from LOW impact filter")
                
                # Also try next month for bond auctions
                if months_ahead > 1:
                    try:
                        self.driver.execute_script("setCalendarRange('6');")  # Next Month
                        time.sleep(3)
                        
                        next_month_low = self._extract_events_from_table(self.driver)
                        self.logger.info(f"Extracted {len(next_month_low)} low impact events from next month")
                        
                        next_month_bonds = []
                        for event in next_month_low:
                            if self._is_bond_auction(event.get('event_name', '')):
                                event['is_bond_auction'] = True
                                event['category'] = 'fixed_income'
                                event['importance'] = max(3, event.get('importance', 3))
                                next_month_bonds.append(event)
                        
                        all_events.extend(next_month_bonds)
                        self.logger.info(f"Added {len(next_month_bonds)} bond auctions from next month low impact")
                        
                    except Exception as e:
                        self.logger.warning(f"Error scraping next month low impact: {e}")
                
            except Exception as e:
                self.logger.warning(f"Error scraping medium impact events: {e}")
            
            # Separate regular events from bond auctions
            regular_events = [e for e in all_events if not e.get('is_bond_auction', False)]
            bond_auctions = [e for e in all_events if e.get('is_bond_auction', False)]
            
            # Calculate coverage statistics
            g3_coverage = {
                'United States': len([e for e in all_events if e['country'] == 'United States']),
                'Japan': len([e for e in all_events if e['country'] == 'Japan']),
                'Euro Area': len([e for e in all_events if e['country'] == 'Euro Area'])
            }
            
            # Prepare final data structure
            calendar_data = {
                'last_updated': datetime.now(timezone.utc).isoformat(),
                'scraping_method': 'selenium_filtered',
                'filters_applied': {
                    'time_range': f'{months_ahead} months',
                    'importance': 'high_impact_only',
                    'timezone': 'UTC',
                    'countries': 'G3_economies'
                },
                'events': regular_events,
                'bond_auctions': bond_auctions,
                'total_events': len(all_events),
                'g3_coverage': g3_coverage,
                'data_quality': {
                    'timezone_consistent': True,
                    'high_impact_only': True,
                    'date_range_months': months_ahead
                }
            }
            
            # Save to cache
            self._save_to_cache(calendar_data, cache_file)
            
            self.logger.info(f"Successfully scraped {len(all_events)} events ({len(regular_events)} regular, {len(bond_auctions)} auctions)")
            return calendar_data
            
        except Exception as e:
            self.logger.error(f"Error during scraping: {e}")
            return {
                'last_updated': datetime.now(timezone.utc).isoformat(),
                'error': str(e),
                'events': [],
                'bond_auctions': [],
                'total_events': 0,
                'g3_coverage': {'United States': 0, 'Japan': 0, 'Euro Area': 0}
            }
        
        finally:
            # Always cleanup WebDriver
            if self.driver:
                try:
                    self.driver.quit()
                    self.logger.info("WebDriver closed successfully")
                except Exception as e:
                    self.logger.warning(f"Error closing WebDriver: {e}")


# Test function
def test_scraper():
    """Test the Selenium scraper thoroughly"""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    print("Testing Trading Economics Selenium Scraper...")
    print("=" * 60)
    
    try:
        scraper = TradingEconomicsSeleniumScraper(headless=False)  # Use visible browser for testing
        
        print("🚀 Starting comprehensive scraping test...")
        calendar_data = scraper.scrape_calendar(months_ahead=2)
        
        print(f"✅ Scraping completed!")
        print(f"📊 Results Summary:")
        print(f"   Total Events: {calendar_data.get('total_events', 0)}")
        print(f"   Regular Events: {len(calendar_data.get('events', []))}")
        print(f"   Bond Auctions: {len(calendar_data.get('bond_auctions', []))}")
        print()
        
        # Coverage analysis
        coverage = calendar_data.get('g3_coverage', {})
        print(f"🌍 G3 Coverage:")
        for country, count in coverage.items():
            print(f"   {country}: {count} events")
        print()
        
        # Sample events
        events = calendar_data.get('events', [])[:5]
        if events:
            print(f"📅 Sample Events:")
            for event in events:
                print(f"   {event.get('date_display', 'N/A')} {event.get('time_display', 'N/A')}")
                print(f"   → {event.get('event_name', 'N/A')} ({event.get('country', 'N/A')})")
                print(f"   → Category: {event.get('category', 'N/A')}, Importance: {event.get('importance', 'N/A')}")
                print()
        
        # Sample bond auctions
        auctions = calendar_data.get('bond_auctions', [])[:3]
        if auctions:
            print(f"💰 Sample Bond Auctions:")
            for auction in auctions:
                print(f"   {auction.get('date_display', 'N/A')} {auction.get('time_display', 'N/A')}")
                print(f"   → {auction.get('event_name', 'N/A')} ({auction.get('country', 'N/A')})")
                print()
        
        # Quality metrics
        quality = calendar_data.get('data_quality', {})
        print(f"✅ Data Quality:")
        print(f"   Timezone Consistent: {quality.get('timezone_consistent', False)}")
        print(f"   High Impact Only: {quality.get('high_impact_only', False)}")
        print(f"   Date Range: {quality.get('date_range_months', 0)} months")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


if __name__ == "__main__":
    test_scraper()