#!/usr/bin/env python3
"""
Economic Calendar for YenSense AI
Loads calendar data from JSON files and calculates recurring events
All times stored and processed in UTC with proper timezone conversion
"""

import json
import logging
import os
import requests
import yaml
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

# Import the Trading Economics scrapers
try:
    from ..scrapers.trading_economics_scraper import TradingEconomicsScraper
    from ..scrapers.trading_economics_selenium_scraper import TradingEconomicsSeleniumScraper
except ImportError:
    # Fallback for when running as standalone script
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
    from scrapers.trading_economics_scraper import TradingEconomicsScraper
    from scrapers.trading_economics_selenium_scraper import TradingEconomicsSeleniumScraper


@dataclass
class EconomicEvent:
    """Represents a single economic event"""
    date: datetime  # Always stored in UTC
    time_local: str  # Local time display (e.g., "12:00 JST")
    event_name: str
    country: str
    currency: str
    importance: int  # 1-5 scale, 5 being highest
    category: str
    source: str
    description: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'date': self.date.strftime('%Y-%m-%d'),
            'time': self.time_local,
            'event_name': self.event_name,
            'country': self.country,
            'currency': self.currency,
            'importance': self.importance,
            'category': self.category,
            'source': self.source,
            'description': self.description
        }


class EconomicCalendar:
    """Economic calendar loading data from JSON files with proper caching"""
    
    def __init__(self, data_dir: Optional[str] = None, config_path: str = "config.yaml"):
        """Initialize calendar with data directory"""
        self.logger = logging.getLogger(__name__)
        
        # Set data directory path
        if data_dir is None:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            self.data_dir = os.path.join(current_dir, '..', '..', 'data', 'input', 'calendar')
        else:
            self.data_dir = data_dir
            
        # Cache for loaded data
        self._central_bank_cache = None
        
        # Load config for future API integrations
        self.config_path = config_path
        try:
            with open(config_path, 'r') as f:
                self.config = yaml.safe_load(f)
        except Exception as e:
            self.logger.warning(f"Could not load config: {e}")
            self.config = {'api_keys': {}}
            
        # Initialize Trading Economics scrapers (prioritize Selenium)
        try:
            self.selenium_scraper = TradingEconomicsSeleniumScraper(cache_dir=self.data_dir)
            self.logger.info("Initialized Selenium-based Trading Economics scraper")
        except Exception as e:
            self.logger.warning(f"Failed to initialize Selenium scraper: {e}")
            self.selenium_scraper = None
            
        try:
            self.trading_scraper = TradingEconomicsScraper(cache_dir=self.data_dir)
            self.logger.info("Initialized basic Trading Economics scraper as fallback")
        except Exception as e:
            self.logger.error(f"Failed to initialize basic Trading Economics scraper: {e}")
            self.trading_scraper = None
        
    def _load_central_bank_data(self) -> Dict[str, Any]:
        """Load central bank meetings from JSON file with caching"""
        if self._central_bank_cache is not None:
            return self._central_bank_cache
            
        try:
            file_path = os.path.join(self.data_dir, 'central_bank_meetings.json')
            with open(file_path, 'r') as f:
                self._central_bank_cache = json.load(f)
            self.logger.info(f"Loaded central bank data from {file_path}")
            return self._central_bank_cache
        except Exception as e:
            self.logger.error(f"Failed to load central bank data: {e}")
            return {}
    
    
    def _convert_utc_to_local_display(self, utc_dt: datetime, timezone: str) -> str:
        """Convert UTC datetime to local time display string"""
        # This is a simplified conversion - for production, use pytz
        timezone_offsets = {
            'JST': 9,  # Japan Standard Time
            'ET': -5,  # Eastern Time (standard)
            'CET': 1,  # Central European Time
            'GMT': 0   # Greenwich Mean Time
        }
        
        offset = timezone_offsets.get(timezone, 0)
        local_dt = utc_dt + timedelta(hours=offset)
        return f"{local_dt.strftime('%H:%M')} {timezone}"
    
    def get_first_friday(self, year: int, month: int) -> datetime:
        """Calculate first Friday of month (NFP release date) in UTC"""
        first_day = datetime(year, month, 1)
        # Calculate days until Friday (4 = Friday, 0 = Monday)
        days_until_friday = (4 - first_day.weekday()) % 7
        first_friday = first_day + timedelta(days=days_until_friday)
        
        # Convert to UTC (NFP releases at 08:30 ET = 12:30 UTC)
        utc_time = first_friday.replace(hour=12, minute=30, second=0, microsecond=0)
        return utc_time
    
    def get_recurring_events(self, start_date: datetime, end_date: datetime) -> List[EconomicEvent]:
        """Get all recurring events (NFP, CPI, etc.) - hardcoded for simplicity"""
        events = []
        
        # Add NFP events (First Friday of each month at 08:30 ET)
        events.extend(self._get_nfp_events(start_date, end_date))
        
        return events
    
    def _get_nfp_events(self, start_date: datetime, end_date: datetime) -> List[EconomicEvent]:
        """Get NFP events (first Friday of each month)"""
        events = []
        current = start_date.replace(day=1)  # Start of month
        
        while current <= end_date:
            event_date = self.get_first_friday(current.year, current.month)
            
            if start_date <= event_date <= end_date:
                events.append(EconomicEvent(
                    date=event_date,
                    time_local="08:30 ET",
                    event_name="US Non-Farm Payrolls",
                    country="United States",
                    currency="USD",
                    importance=5,
                    category="employment",
                    source="Bureau of Labor Statistics",
                    description="Monthly employment data release"
                ))
            
            # Move to next month
            if current.month == 12:
                current = current.replace(year=current.year + 1, month=1)
            else:
                current = current.replace(month=current.month + 1)
        
        return events
    
    
    def get_central_bank_events(self, start_date: datetime, end_date: datetime) -> List[EconomicEvent]:
        """Get central bank meeting events from JSON data"""
        events = []
        central_bank_data = self._load_central_bank_data()
        
        # Map bank names to full names  
        bank_names = {
            "BOJ": "Bank of Japan",
            "FOMC": "Federal Reserve",
            "ECB": "European Central Bank",
            "BOE": "Bank of England"
        }
        
        currency_map = {
            "BOJ": "JPY",
            "FOMC": "USD", 
            "ECB": "EUR",
            "BOE": "GBP"
        }
        
        country_map = {
            "BOJ": "Japan",
            "FOMC": "United States",
            "ECB": "Eurozone",
            "BOE": "United Kingdom"
        }
        
        for bank, years_data in central_bank_data.items():
            for year_str, meetings in years_data.items():
                for meeting in meetings:
                    # Parse UTC datetime from JSON and make timezone-naive for comparison
                    utc_dt = datetime.fromisoformat(meeting['decision_date'].replace('Z', '+00:00')).replace(tzinfo=None)
                    
                    if start_date <= utc_dt <= end_date:
                        event_name = f"{bank} Policy Decision"
                        if bank == "FOMC":
                            event_name = "FOMC Rate Decision"
                        elif bank == "BOE":
                            event_name = "BOE MPC Decision"
                        
                        # Format local time display
                        local_time = f"{meeting['local_time']} {meeting['time_zone']}"
                        
                        events.append(EconomicEvent(
                            date=utc_dt,
                            time_local=local_time,
                            event_name=event_name,
                            country=country_map[bank],
                            currency=currency_map[bank],
                            importance=5,
                            category="monetary_policy",
                            source=bank_names[bank],
                            description=f"{bank_names[bank]} monetary policy decision"
                        ))
        
        return events
    
    def update_fred_calendar(self, months_ahead: int = 6):
        """Fetch and store FRED economic releases calendar"""
        fred_api_key = self.config.get('api_keys', {}).get('fred')
        if not fred_api_key:
            self.logger.error("FRED API key not configured")
            return
        
        try:
            import requests
            
            # Fetch data for next 6 months
            from_date = datetime.now().strftime('%Y-%m-%d')
            end_date = (datetime.now() + timedelta(days=months_ahead*30)).strftime('%Y-%m-%d')
            
            url = "https://api.stlouisfed.org/fred/releases/dates"
            params = {
                'api_key': fred_api_key,
                'file_type': 'json',
                'include_release_dates_with_no_data': 'true',
                'realtime_start': from_date,
                'realtime_end': end_date,
                'limit': 2000,
                'sort_order': 'asc'
            }
            
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            # Process and store data
            fred_calendar = {}
            for item in data.get('release_dates', []):
                release_name = item['release_name']
                release_date = item['date']
                
                # Map to our format
                importance = 3
                category = 'economic'
                time_local = '08:30 ET'
                
                if 'Consumer Price Index' in release_name or 'CPI' in release_name:
                    importance = 5
                    category = 'inflation'
                elif 'Employment' in release_name or 'Payroll' in release_name:
                    importance = 5
                    category = 'employment'
                elif 'GDP' in release_name or 'Gross Domestic' in release_name:
                    importance = 5
                    category = 'growth'
                elif 'Industrial Production' in release_name:
                    importance = 4
                    category = 'manufacturing'
                elif 'Retail' in release_name:
                    importance = 4
                    category = 'retail'
                elif 'Housing' in release_name or 'Building' in release_name:
                    importance = 4
                    category = 'housing'
                elif 'FOMC' in release_name or 'Federal Funds' in release_name:
                    importance = 5
                    category = 'monetary_policy'
                    time_local = '14:00 ET'
                
                if release_date not in fred_calendar:
                    fred_calendar[release_date] = []
                
                fred_calendar[release_date].append({
                    'release_name': release_name,
                    'time_local': time_local,
                    'importance': importance,
                    'category': category,
                    'source': 'FRED'
                })
            
            # Save to file
            fred_file = os.path.join(self.data_dir, 'fred_economic_releases.json')
            with open(fred_file, 'w') as f:
                json.dump(fred_calendar, f, indent=2)
            
            self.logger.info(f"Stored {len(fred_calendar)} dates of FRED releases to {fred_file}")
            
        except Exception as e:
            self.logger.error(f"Error updating FRED calendar: {e}")
    
    def _load_fred_calendar(self) -> Dict[str, Any]:
        """Load FRED economic releases from JSON file"""
        try:
            fred_file = os.path.join(self.data_dir, 'fred_economic_releases.json')
            if os.path.exists(fred_file):
                with open(fred_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            self.logger.error(f"Error loading FRED calendar: {e}")
        return {}
    
    def get_fred_events(self, start_date: datetime, end_date: datetime) -> List[EconomicEvent]:
        """Get FRED economic events from stored data"""
        events = []
        fred_data = self._load_fred_calendar()
        
        current_date = start_date
        while current_date <= end_date:
            date_str = current_date.strftime('%Y-%m-%d')
            if date_str in fred_data:
                for event_data in fred_data[date_str]:
                    event = EconomicEvent(
                        date=current_date,
                        time_local=event_data['time_local'],
                        event_name=event_data['release_name'],
                        country='United States',
                        currency='USD',
                        importance=event_data['importance'],
                        category=event_data['category'],
                        source='FRED',
                        description=f"US economic data release: {event_data['release_name']}"
                    )
                    events.append(event)
            current_date += timedelta(days=1)
        
        return events
    
    def get_trading_economics_events(self, start_date: datetime, end_date: datetime) -> List[EconomicEvent]:
        """Get events from Trading Economics scraper (prioritizes Selenium)"""
        
        # Try Selenium scraper first (comprehensive with bond auctions)
        if self.selenium_scraper:
            try:
                self.logger.info("Using Selenium-based Trading Economics scraper")
                calendar_data = self.selenium_scraper.scrape_calendar(months_ahead=2)
                
                events = []
                
                # Process regular events from Selenium scraper
                for event_data in calendar_data.get('events', []):
                    try:
                        # Parse datetime from Selenium format (already in UTC)
                        datetime_utc_str = event_data.get('datetime_utc')
                        if datetime_utc_str:
                            event_dt = datetime.fromisoformat(datetime_utc_str)
                            
                            if start_date <= event_dt <= end_date:
                                # Create EconomicEvent object
                                event = EconomicEvent(
                                    date=event_dt,
                                    time_local=event_data.get('time_display', 'TBD UTC'),
                                    event_name=event_data['event_name'],
                                    country=event_data['country'],
                                    currency=event_data['currency'],
                                    importance=event_data['importance'],
                                    category=event_data['category'],
                                    source='trading_economics_selenium',
                                    description=f"{event_data['country']} economic data: {event_data['event_name']}"
                                )
                                events.append(event)
                                
                    except Exception as e:
                        self.logger.warning(f"Error processing Selenium event: {e}")
                        continue
                
                # Process bond auctions from Selenium scraper
                for auction_data in calendar_data.get('bond_auctions', []):
                    try:
                        # Parse datetime from Selenium format (already in UTC)
                        datetime_utc_str = auction_data.get('datetime_utc')
                        if datetime_utc_str:
                            event_dt = datetime.fromisoformat(datetime_utc_str)
                            
                            if start_date <= event_dt <= end_date:
                                # Create EconomicEvent object for bond auction
                                event = EconomicEvent(
                                    date=event_dt,
                                    time_local=auction_data.get('time_display', 'TBD UTC'),
                                    event_name=auction_data['event_name'],
                                    country=auction_data['country'],
                                    currency=auction_data['currency'],
                                    importance=auction_data.get('importance', 3),
                                    category='fixed_income',
                                    source='trading_economics_selenium',
                                    description=f"{auction_data['country']} bond auction: {auction_data['event_name']}"
                                )
                                events.append(event)
                                
                    except Exception as e:
                        self.logger.warning(f"Error processing Selenium bond auction: {e}")
                        continue
                        
                self.logger.info(f"Retrieved {len(events)} events from Selenium Trading Economics scraper")
                return events
                
            except Exception as e:
                self.logger.warning(f"Selenium scraper failed, falling back to basic scraper: {e}")
        
        # Fallback to basic scraper
        if not self.trading_scraper:
            self.logger.warning("No Trading Economics scrapers available")
            return []
            
        try:
            self.logger.info("Using basic Trading Economics scraper as fallback")
            # Get calendar data from basic Trading Economics scraper
            calendar_data = self.trading_scraper.scrape_calendar()
            
            events = []
            
            # Process regular events (basic scraper format)
            for event_data in calendar_data.get('events', []):
                try:
                    # Parse date from basic Trading Economics format
                    date_str = event_data['date']
                    time_str = event_data.get('time', '')
                    
                    # Convert to datetime (simplified parsing for now)
                    event_dt = self._parse_trading_economics_date(date_str, time_str, event_data['timezone'])
                    
                    if event_dt and start_date <= event_dt <= end_date:
                        # Create EconomicEvent object
                        event = EconomicEvent(
                            date=event_dt,
                            time_local=f"{time_str} {event_data['timezone']}" if time_str else f"TBD {event_data['timezone']}",
                            event_name=event_data['event_name'],
                            country=event_data['country'],
                            currency=event_data['currency'],
                            importance=event_data['importance'],
                            category=event_data['category'],
                            source='trading_economics_basic',
                            description=f"{event_data['country']} economic data: {event_data['event_name']}"
                        )
                        events.append(event)
                        
                except Exception as e:
                    self.logger.warning(f"Error processing basic Trading Economics event: {e}")
                    continue
            
            # Process bond auctions (basic scraper format)
            for auction_data in calendar_data.get('bond_auctions', []):
                try:
                    # Parse date from basic Trading Economics format
                    date_str = auction_data['date']
                    time_str = auction_data.get('time', '')
                    
                    # Convert to datetime
                    event_dt = self._parse_trading_economics_date(date_str, time_str, auction_data['timezone'])
                    
                    if event_dt and start_date <= event_dt <= end_date:
                        # Create EconomicEvent object for bond auction
                        event = EconomicEvent(
                            date=event_dt,
                            time_local=f"{time_str} {auction_data['timezone']}" if time_str else f"TBD {auction_data['timezone']}",
                            event_name=auction_data['event_name'],
                            country=auction_data['country'],
                            currency=auction_data['currency'],
                            importance=auction_data['importance'],
                            category='fixed_income',
                            source='trading_economics_basic',
                            description=f"{auction_data['country']} bond auction: {auction_data['event_name']}"
                        )
                        events.append(event)
                        
                except Exception as e:
                    self.logger.warning(f"Error processing basic Trading Economics bond auction: {e}")
                    continue
                    
            self.logger.info(f"Retrieved {len(events)} events from basic Trading Economics scraper")
            return events
            
        except Exception as e:
            self.logger.error(f"Error retrieving Trading Economics events: {e}")
            return []
    
    def _parse_trading_economics_date(self, date_str: str, time_str: str, timezone_str: str) -> Optional[datetime]:
        """Parse date from Trading Economics format"""
        try:
            # Handle different date formats
            if 'Today' in date_str:
                base_date = datetime.now()
            elif 'Tomorrow' in date_str:
                base_date = datetime.now() + timedelta(days=1)
            else:
                # Parse date string like "Thursday September 11 2025"
                # Remove day of week and parse the rest
                parts = date_str.split()
                if len(parts) >= 3:
                    # Find month, day, year
                    month_str = parts[-3] if len(parts) >= 3 else parts[1]
                    day_str = parts[-2] if len(parts) >= 3 else parts[2]
                    year_str = parts[-1] if len(parts) >= 3 else "2025"
                    
                    # Parse month name to number
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
                    # Fallback to current date
                    base_date = datetime.now()
            
            # Parse time if provided
            if time_str and ':' in time_str:
                # Parse time like "08:30 AM" or "14:00"
                time_part = time_str.split()[0]  # Get just the time part
                if 'AM' in time_str or 'PM' in time_str:
                    hour, minute = time_part.split(':')
                    hour = int(hour)
                    minute = int(minute)
                    if 'PM' in time_str and hour != 12:
                        hour += 12
                    elif 'AM' in time_str and hour == 12:
                        hour = 0
                else:
                    hour, minute = time_part.split(':')
                    hour = int(hour)
                    minute = int(minute)
                
                event_dt = base_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
            else:
                # Default to 9 AM if no time specified
                event_dt = base_date.replace(hour=9, minute=0, second=0, microsecond=0)
            
            # Convert to UTC based on timezone
            timezone_offsets = {
                'ET': -5,   # Eastern Time (EST)
                'JST': 9,   # Japan Standard Time
                'CET': 1,   # Central European Time
                'GMT': 0,   # Greenwich Mean Time
                'UTC': 0    # UTC
            }
            
            offset_hours = timezone_offsets.get(timezone_str, 0)
            utc_dt = event_dt - timedelta(hours=offset_hours)
            
            return utc_dt
            
        except Exception as e:
            self.logger.warning(f"Error parsing date '{date_str}' '{time_str}': {e}")
            return None
    
    def get_events(self, start_date: datetime, end_date: datetime) -> List[EconomicEvent]:
        """Get all economic events for date range"""
        all_events = []
        
        # Get central bank meetings
        all_events.extend(self.get_central_bank_events(start_date, end_date))
        
        # Get Trading Economics events (primary source)
        trading_events = self.get_trading_economics_events(start_date, end_date)
        if trading_events:
            all_events.extend(trading_events)
            self.logger.info(f"Added {len(trading_events)} Trading Economics events")
        else:
            # Fallback to legacy sources if Trading Economics fails
            self.logger.warning("Trading Economics unavailable, using fallback sources")
            
            # Get recurring events (NFP, CPI, etc.)
            all_events.extend(self.get_recurring_events(start_date, end_date))
            
            # Get FRED economic releases
            all_events.extend(self.get_fred_events(start_date, end_date))
        
        # Sort by date
        all_events.sort(key=lambda x: x.date)
        
        return all_events
    
    def get_today_events(self) -> List[EconomicEvent]:
        """Get today's economic events (in UTC)"""
        now_utc = datetime.now(timezone.utc).replace(tzinfo=None)  # Make timezone-naive
        today_start = now_utc.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = now_utc.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        return self.get_events(today_start, today_end)
    
    def get_upcoming_events(self, days_ahead: int = 7) -> List[EconomicEvent]:
        """Get events for next N days (in UTC)"""
        start_date = datetime.now(timezone.utc).replace(tzinfo=None)  # Make timezone-naive
        end_date = start_date + timedelta(days=days_ahead)
        
        return self.get_events(start_date, end_date)
    
    def get_recent_events(self, days_back: int = 3) -> List[EconomicEvent]:
        """Get events from last N days (in UTC)"""
        end_date = datetime.now(timezone.utc).replace(tzinfo=None)  # Make timezone-naive
        start_date = end_date - timedelta(days=days_back)
        
        return self.get_events(start_date, end_date)
    
    def get_high_importance_events(self, events: List[EconomicEvent]) -> List[EconomicEvent]:
        """Filter for high importance events (4+)"""
        return [event for event in events if event.importance >= 4]
    
    def format_for_brief(self, events: List[EconomicEvent]) -> str:
        """Format events for morning brief commentary"""
        if not events:
            return "No major economic events scheduled."
        
        lines = []
        for event in events:
            importance_stars = "⭐" * event.importance
            time_str = f" at {event.time_local}" if event.time_local else ""
            lines.append(f"{event.date.strftime('%a %m/%d')}: {event.event_name}{time_str} {importance_stars}")
        
        return "\n".join(lines)
    
    def get_calendar_summary(self, days_ahead: int = 7) -> Dict[str, Any]:
        """Get calendar summary for AI analysis"""
        today_events = self.get_today_events()
        upcoming_events = self.get_upcoming_events(days_ahead)
        recent_events = self.get_recent_events(3)
        
        return {
            "today": [event.to_dict() for event in today_events],
            "upcoming": [event.to_dict() for event in upcoming_events],
            "recent": [event.to_dict() for event in recent_events],
            "high_importance_upcoming": [
                event.to_dict() for event in self.get_high_importance_events(upcoming_events)
            ]
        }


if __name__ == "__main__":
    # Test the calendar
    import json
    
    calendar = EconomicCalendar()
    
    # Test getting events for next 14 days
    upcoming = calendar.get_upcoming_events(14)
    
    print(f"Found {len(upcoming)} upcoming events:")
    print("=" * 50)
    
    for event in upcoming:
        importance = "⭐" * event.importance
        print(f"{event.date.strftime('%Y-%m-%d')} {event.time_local} | {importance}")
        print(f"  {event.event_name} ({event.country})")
        print(f"  Category: {event.category}")
        print()
    
    # Test calendar summary
    summary = calendar.get_calendar_summary()
    print("Calendar Summary:")
    print(json.dumps(summary, indent=2, default=str))