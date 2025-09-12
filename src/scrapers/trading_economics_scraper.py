#!/usr/bin/env python3
"""
Trading Economics Calendar Scraper
Scrapes economic events and bond auctions for G3 economies
"""

import os
import json
import requests
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional
from bs4 import BeautifulSoup
import time


class TradingEconomicsScraper:
    """Scraper for Trading Economics calendar data"""
    
    def __init__(self, cache_dir: Optional[str] = None, cache_hours: int = 24):
        """Initialize scraper with caching"""
        self.logger = logging.getLogger(__name__)
        
        # Set cache directory
        if cache_dir is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            self.cache_dir = os.path.join(current_dir, '..', '..', 'data', 'input', 'calendar')
        else:
            self.cache_dir = cache_dir
            
        os.makedirs(self.cache_dir, exist_ok=True)
        
        self.cache_hours = cache_hours
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        # G3 country mappings
        self.g3_countries = {
            'United States': {'currency': 'USD', 'aliases': ['US', 'USA', 'United States']},
            'Japan': {'currency': 'JPY', 'aliases': ['Japan', 'JP']},
            'Euro Area': {'currency': 'EUR', 'aliases': ['Euro Area', 'Eurozone', 'Germany', 'DE']},
        }
        
        # Event importance mapping
        self.importance_map = {
            'high': 5,
            'medium': 3,
            'low': 1
        }
        
        # Category mapping for events
        self.category_map = {
            'cpi': 'inflation',
            'ppi': 'inflation',
            'inflation': 'inflation',
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
            'boj': 'monetary_policy',
            'ecb': 'monetary_policy',
            'interest rate': 'monetary_policy',
            'policy rate': 'monetary_policy',
            'bond': 'fixed_income',
            'auction': 'fixed_income',
            'treasury': 'fixed_income',
            'note': 'fixed_income',
            'bill': 'fixed_income'
        }
        
    def _is_cache_valid(self, cache_file: str) -> bool:
        """Check if cache file is valid and not expired"""
        try:
            if not os.path.exists(cache_file):
                return False
                
            file_time = os.path.getmtime(cache_file)
            file_dt = datetime.fromtimestamp(file_time)
            expiry_time = datetime.now() - timedelta(hours=self.cache_hours)
            
            return file_dt > expiry_time
        except Exception as e:
            self.logger.error(f"Error checking cache validity: {e}")
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
    
    def _get_country_for_event(self, event_text: str) -> Optional[str]:
        """Determine G3 country from event text"""
        event_lower = event_text.lower()
        
        for country, info in self.g3_countries.items():
            for alias in info['aliases']:
                if alias.lower() in event_lower:
                    return country
                    
        # Additional heuristics for country detection
        if any(word in event_lower for word in ['fed', 'fomc', 'treasury', 'nfp']):
            return 'United States'
        elif any(word in event_lower for word in ['boj', 'jpy', 'yen']):
            return 'Japan'
        elif any(word in event_lower for word in ['ecb', 'eur', 'euro']):
            return 'Euro Area'
            
        return None
    
    def _categorize_event(self, event_name: str) -> str:
        """Categorize event based on name"""
        event_lower = event_name.lower()
        
        for keyword, category in self.category_map.items():
            if keyword in event_lower:
                return category
                
        return 'economic'
    
    def _estimate_importance(self, event_name: str) -> int:
        """Estimate event importance based on name"""
        event_lower = event_name.lower()
        
        # High importance events (5)
        high_importance = [
            'cpi', 'inflation', 'gdp', 'employment', 'unemployment', 'nfp', 'payroll',
            'interest rate', 'policy rate', 'fomc', 'fed fund', 'boj', 'ecb'
        ]
        
        # Medium importance events (3) 
        medium_importance = [
            'retail', 'manufacturing', 'industrial', 'housing', 'trade balance',
            'current account', 'consumer confidence', 'business confidence'
        ]
        
        # Check for high importance
        for keyword in high_importance:
            if keyword in event_lower:
                return 5
        
        # Check for medium importance  
        for keyword in medium_importance:
            if keyword in event_lower:
                return 3
        
        # Bond auctions are generally medium importance
        if any(word in event_lower for word in ['auction', 'bond', 'treasury', 'note', 'bill']):
            return 3
            
        # Default to low importance
        return 1
    
    def _parse_importance(self, importance_element) -> int:
        """Parse importance from HTML element"""
        if not importance_element:
            return 3
            
        # Look for common importance indicators
        class_name = str(importance_element.get('class', [])).lower()
        if 'high' in class_name or 'red' in class_name:
            return 5
        elif 'medium' in class_name or 'orange' in class_name:
            return 3
        elif 'low' in class_name or 'yellow' in class_name:
            return 1
            
        # Count stars or dots
        text = importance_element.get_text().strip()
        if '★' in text or '●' in text:
            return len([c for c in text if c in '★●'])
            
        return 3
    
    def _scrape_calendar_page(self, url: str) -> List[Dict[str, Any]]:
        """Scrape calendar data from Trading Economics page"""
        try:
            self.logger.info(f"Scraping calendar from: {url}")
            
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            events = []
            tables = soup.find_all('table')
            
            # Look for the main calendar table (should be Table 2 based on debug)
            for i, table in enumerate(tables):
                headers = table.find('tr')
                if not headers:
                    continue
                    
                header_cells = headers.find_all(['th', 'td'])
                if len(header_cells) < 4:
                    continue
                    
                header_text = ' '.join([cell.get_text().strip() for cell in header_cells])
                
                # Look for the main calendar table with date header and data columns
                if ('Actual' in header_text and 'Previous' in header_text and 
                    'Consensus' in header_text and any(month in header_text for month in 
                    ['January', 'February', 'March', 'April', 'May', 'June',
                     'July', 'August', 'September', 'October', 'November', 'December'])):
                    
                    self.logger.info(f"Found calendar table at index {i}")
                    calendar_table = table
                    
                    # Extract date from header
                    date_header = header_cells[0].get_text().strip()
                    
                    # Parse all rows in this table
                    rows = table.find_all('tr')[1:]  # Skip header row
                    
                    for row in rows:
                        cells = row.find_all(['td', 'th'])
                        if len(cells) < 5:
                            continue
                        
                        try:
                            # Based on debug analysis, the structure is:
                            # Cell 0: Time 
                            # Cell 1: Calendar item indicator
                            # Cell 2: Empty spacer
                            # Cell 3: Country code (JP, US, EA, etc.)
                            # Cell 4: Event name
                            # Cell 5: Actual value
                            # Cell 6: Previous value  
                            # Cell 7: Consensus
                            # Cell 8: Forecast
                            
                            time_cell = cells[0].get_text().strip() if len(cells) > 0 else ""
                            country_cell = cells[3].get_text().strip() if len(cells) > 3 else ""
                            event_cell = cells[4].get_text().strip() if len(cells) > 4 else ""
                            actual_cell = cells[5].get_text().strip() if len(cells) > 5 else ""
                            previous_cell = cells[6].get_text().strip() if len(cells) > 6 else ""
                            consensus_cell = cells[7].get_text().strip() if len(cells) > 7 else ""
                            forecast_cell = cells[8].get_text().strip() if len(cells) > 8 else ""
                            
                            # Skip rows that don't have event data
                            if not event_cell or not country_cell or len(event_cell) < 3:
                                continue
                            
                            # Skip header rows or spacer rows
                            if event_cell in ['Actual', 'Previous', 'Consensus', 'Forecast'] or not time_cell:
                                continue
                            
                            # Map country codes to G3 countries
                            country = None
                            if country_cell in ['US', 'USA']:
                                country = 'United States'
                            elif country_cell in ['JP', 'JPN']:
                                country = 'Japan'  
                            elif country_cell in ['EA', 'EUR', 'DE', 'DEU']:
                                country = 'Euro Area'
                            
                            # Only include G3 countries
                            if not country:
                                continue
                            
                            # Determine if this is a bond auction
                            is_bond_auction = any(word in event_cell.lower() for word in 
                                                ['auction', 'bond', 'treasury', 'note', 'bill'])
                            
                            event_data = {
                                'date': date_header,
                                'time': time_cell,
                                'timezone': self._get_timezone_for_country(country),
                                'country': country,
                                'currency': self.g3_countries[country]['currency'],
                                'event_name': event_cell,
                                'category': self._categorize_event(event_cell),
                                'importance': self._estimate_importance(event_cell),
                                'actual': actual_cell if actual_cell not in ['-', 'n/a', 'N/A', ''] else None,
                                'forecast': forecast_cell if forecast_cell not in ['-', 'n/a', 'N/A', ''] else None,
                                'previous': previous_cell if previous_cell not in ['-', 'n/a', 'N/A', ''] else None,
                                'source': 'trading_economics',
                                'is_bond_auction': is_bond_auction
                            }
                            
                            events.append(event_data)
                            
                        except Exception as e:
                            self.logger.warning(f"Error parsing row: {e}")
                            continue
            
            # Also look for individual country tables (the ones with just country codes)
            for i, table in enumerate(tables):
                headers = table.find('tr')
                if not headers:
                    continue
                    
                header_cells = headers.find_all(['th', 'td'])
                if len(header_cells) != 2:
                    continue
                    
                # Check if this is a country-specific table
                country_code = header_cells[1].get_text().strip()
                country = None
                if country_code in ['US']:
                    country = 'United States'
                elif country_code in ['JP']:
                    country = 'Japan'  
                elif country_code in ['EA', 'DE']:
                    country = 'Euro Area'
                
                if country:
                    # This table contains events for this country
                    rows = table.find_all('tr')[1:]  # Skip header
                    for row in rows:
                        cells = row.find_all(['td', 'th'])
                        if len(cells) < 1:
                            continue
                            
                        event_text = cells[0].get_text().strip()
                        if not event_text or len(event_text) < 3:
                            continue
                            
                        # Extract time if present (format: "HH:MM AM/PM")
                        time_match = ""
                        if any(char.isdigit() for char in event_text[:10]):
                            parts = event_text.split()
                            if parts and ':' in parts[0]:
                                time_match = parts[0]
                                event_text = ' '.join(parts[1:])
                        
                        is_bond_auction = any(word in event_text.lower() for word in 
                                            ['auction', 'bond', 'treasury', 'note', 'bill'])
                        
                        event_data = {
                            'date': 'Today',  # Will be updated by caller
                            'time': time_match,
                            'timezone': self._get_timezone_for_country(country),
                            'country': country,
                            'currency': self.g3_countries[country]['currency'],
                            'event_name': event_text,
                            'category': self._categorize_event(event_text),
                            'importance': self._estimate_importance(event_text),
                            'actual': None,
                            'forecast': None,
                            'previous': None,
                            'source': 'trading_economics',
                            'is_bond_auction': is_bond_auction
                        }
                        
                        events.append(event_data)
            
            self.logger.info(f"Scraped {len(events)} events from Trading Economics")
            return events
            
        except Exception as e:
            self.logger.error(f"Error scraping Trading Economics: {e}")
            return []
    
    def _get_timezone_for_country(self, country: str) -> str:
        """Get timezone for country"""
        timezone_map = {
            'United States': 'ET',
            'Japan': 'JST',
            'Euro Area': 'CET'
        }
        return timezone_map.get(country, 'UTC')
    
    def scrape_calendar(self, days_ahead: int = 14) -> Dict[str, Any]:
        """Scrape calendar data for specified number of days ahead"""
        cache_file = os.path.join(self.cache_dir, 'trading_economics_calendar.json')
        
        # Try cache first
        cached_data = self._load_from_cache(cache_file)
        if cached_data:
            return cached_data
        
        # Scrape fresh data
        base_url = "https://tradingeconomics.com/calendar"
        
        all_events = []
        
        # Scrape current week and next week
        urls_to_scrape = [
            base_url,  # Current week
            f"{base_url}?week=1",  # Next week
        ]
        
        for url in urls_to_scrape:
            try:
                events = self._scrape_calendar_page(url)
                all_events.extend(events)
                time.sleep(2)  # Be respectful to the server
            except Exception as e:
                self.logger.error(f"Error scraping {url}: {e}")
                continue
        
        # Separate regular events from bond auctions
        regular_events = [e for e in all_events if not e.get('is_bond_auction', False)]
        bond_auctions = [e for e in all_events if e.get('is_bond_auction', False)]
        
        # Prepare final data structure
        calendar_data = {
            'last_updated': datetime.now(timezone.utc).isoformat(),
            'events': regular_events,
            'bond_auctions': bond_auctions,
            'total_events': len(all_events),
            'g3_coverage': {
                'United States': len([e for e in all_events if e['country'] == 'United States']),
                'Japan': len([e for e in all_events if e['country'] == 'Japan']),
                'Euro Area': len([e for e in all_events if e['country'] == 'Euro Area'])
            }
        }
        
        # Save to cache
        self._save_to_cache(calendar_data, cache_file)
        
        return calendar_data
    
    def get_todays_events(self) -> List[Dict[str, Any]]:
        """Get today's events"""
        calendar_data = self.scrape_calendar()
        today = datetime.now().strftime('%b %d')  # Format: "Jan 12"
        
        todays_events = []
        for event in calendar_data.get('events', []):
            if today in event.get('date', ''):
                todays_events.append(event)
                
        return todays_events
    
    def get_upcoming_events(self, days_ahead: int = 7) -> List[Dict[str, Any]]:
        """Get upcoming events for specified days"""
        calendar_data = self.scrape_calendar(days_ahead)
        return calendar_data.get('events', [])
    
    def get_bond_auctions(self, days_ahead: int = 7) -> List[Dict[str, Any]]:
        """Get upcoming bond auctions"""
        calendar_data = self.scrape_calendar(days_ahead)
        return calendar_data.get('bond_auctions', [])


if __name__ == "__main__":
    # Test the scraper
    logging.basicConfig(level=logging.INFO)
    
    scraper = TradingEconomicsScraper()
    
    print("Testing Trading Economics scraper...")
    print("=" * 50)
    
    # Test calendar scraping
    calendar_data = scraper.scrape_calendar()
    
    print(f"Total events found: {calendar_data.get('total_events', 0)}")
    print(f"Regular events: {len(calendar_data.get('events', []))}")
    print(f"Bond auctions: {len(calendar_data.get('bond_auctions', []))}")
    print()
    
    # Show G3 coverage
    coverage = calendar_data.get('g3_coverage', {})
    for country, count in coverage.items():
        print(f"{country}: {count} events")
    print()
    
    # Show sample events
    events = calendar_data.get('events', [])[:5]
    print("Sample events:")
    for event in events:
        print(f"  {event['date']} {event['time']} | {event['event_name']} ({event['country']})")
    
    # Show sample bond auctions
    auctions = calendar_data.get('bond_auctions', [])[:3]
    if auctions:
        print("\nSample bond auctions:")
        for auction in auctions:
            print(f"  {auction['date']} {auction['time']} | {auction['event_name']} ({auction['country']})")