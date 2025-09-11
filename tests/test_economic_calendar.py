#!/usr/bin/env python3
"""
Unit tests for EconomicCalendar
Tests the new JSON-based calendar functionality with proper timezone handling
"""

import unittest
import sys
import os
import tempfile
import json
from datetime import datetime, timedelta, timezone

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.economic_calendar import EconomicCalendar, EconomicEvent


class TestEconomicCalendar(unittest.TestCase):
    """Test suite for EconomicCalendar functionality"""
    
    def setUp(self):
        """Set up test fixtures with temporary data directory"""
        # Create temporary directory for test data
        self.test_dir = tempfile.mkdtemp()
        
        # Create test central bank data
        self.cb_data = {
            "BOJ": {
                "2025": [
                    {"meeting_dates": "Sep 18-19", "decision_date": "2025-09-19T03:00:00Z", "time_zone": "JST", "local_time": "12:00"}
                ]
            },
            "FOMC": {
                "2025": [
                    {"meeting_dates": "Sep 16-17", "decision_date": "2025-09-17T19:00:00Z", "time_zone": "ET", "local_time": "14:00"}
                ]
            }
        }
        
        # Create test recurring events data
        self.recurring_data = {
            "nfp": {
                "name": "US Non-Farm Payrolls",
                "country": "United States",
                "currency": "USD",
                "importance": 5,
                "category": "employment",
                "source": "Bureau of Labor Statistics",
                "description": "Monthly employment report",
                "schedule": "first_friday_of_month",
                "time_utc": "12:30:00",
                "time_zone": "ET",
                "local_time": "08:30"
            },
            "us_cpi": {
                "name": "US CPI (Core) YoY",
                "country": "United States",
                "currency": "USD",
                "importance": 5,
                "category": "inflation",
                "source": "Bureau of Labor Statistics",
                "description": "Consumer Price Index",
                "schedule": "monthly_fixed_day",
                "day_of_month": 12,
                "time_utc": "12:30:00",
                "time_zone": "ET",
                "local_time": "08:30"
            }
        }
        
        # Write test data to files
        with open(os.path.join(self.test_dir, 'central_bank_meetings.json'), 'w') as f:
            json.dump(self.cb_data, f)
            
        with open(os.path.join(self.test_dir, 'recurring_events.json'), 'w') as f:
            json.dump(self.recurring_data, f)
        
        # Create a test config without Finnhub key (to avoid API calls in tests)
        test_config = {'api_keys': {}}
        with open(os.path.join(self.test_dir, 'test_config.yaml'), 'w') as f:
            import yaml
            yaml.dump(test_config, f)
        
        # Initialize calendar with test data directory and test config
        self.calendar = EconomicCalendar(data_dir=self.test_dir, 
                                        config_path=os.path.join(self.test_dir, 'test_config.yaml'))
    
    def tearDown(self):
        """Clean up test files"""
        import shutil
        shutil.rmtree(self.test_dir)
    
    def test_calendar_initialization(self):
        """Test that calendar initializes properly"""
        self.assertIsInstance(self.calendar, EconomicCalendar)
        self.assertEqual(self.calendar.data_dir, self.test_dir)
        
        # Test data loading
        cb_data = self.calendar._load_central_bank_data()
        self.assertIn("BOJ", cb_data)
        self.assertIn("FOMC", cb_data)
        
        recurring_data = self.calendar._load_recurring_events_data()
        self.assertIn("nfp", recurring_data)
        self.assertIn("us_cpi", recurring_data)
    
    def test_json_data_structure(self):
        """Test that JSON data has correct structure"""
        cb_data = self.calendar._load_central_bank_data()
        
        # Test BOJ 2025 structure
        boj_2025 = cb_data["BOJ"]["2025"]
        self.assertEqual(len(boj_2025), 1)  # Test data has 1 meeting
        
        # Test meeting structure
        first_meeting = boj_2025[0]
        self.assertIn("meeting_dates", first_meeting)
        self.assertIn("decision_date", first_meeting)
        self.assertIn("time_zone", first_meeting)
        self.assertEqual(first_meeting["decision_date"], "2025-09-19T03:00:00Z")
        
        # Test recurring events structure
        recurring_data = self.calendar._load_recurring_events_data()
        nfp_config = recurring_data["nfp"]
        self.assertEqual(nfp_config["schedule"], "first_friday_of_month")
        self.assertEqual(nfp_config["time_utc"], "12:30:00")
    
    def test_get_first_friday_calculation(self):
        """Test NFP first Friday calculation with UTC conversion"""
        # Test known first Fridays (now returns UTC datetime with time)
        test_cases = [
            (2025, 9, datetime(2025, 9, 5, 12, 30, 0)),   # Sep 2025 first Friday at 12:30 UTC
            (2025, 10, datetime(2025, 10, 3, 12, 30, 0)), # Oct 2025 first Friday at 12:30 UTC
            (2025, 11, datetime(2025, 11, 7, 12, 30, 0)), # Nov 2025 first Friday at 12:30 UTC
            (2025, 12, datetime(2025, 12, 5, 12, 30, 0))  # Dec 2025 first Friday at 12:30 UTC
        ]
        
        for year, month, expected in test_cases:
            result = self.calendar.get_first_friday(year, month)
            self.assertEqual(result, expected, 
                           f"First Friday for {year}-{month} should be {expected}, got {result}")
            self.assertEqual(result.weekday(), 4, "First Friday should be on Friday (weekday 4)")
            self.assertEqual(result.hour, 12, "Should be at 12:30 UTC for NFP")
            self.assertEqual(result.minute, 30, "Should be at 12:30 UTC for NFP")
    
    def test_recurring_events_generation(self):
        """Test recurring events generation (NFP) for specific month"""
        start_date = datetime(2025, 9, 1)
        end_date = datetime(2025, 9, 30)
        
        recurring_events = self.calendar.get_recurring_events(start_date, end_date)
        
        # Should have NFP and CPI events
        self.assertGreaterEqual(len(recurring_events), 1)
        
        # Find NFP event
        nfp_event = next((e for e in recurring_events if "Non-Farm" in e.event_name), None)
        self.assertIsNotNone(nfp_event)
        
        self.assertEqual(nfp_event.date.date(), datetime(2025, 9, 5).date())
        self.assertEqual(nfp_event.event_name, "US Non-Farm Payrolls")
        self.assertEqual(nfp_event.time_local, "08:30 ET")
        self.assertEqual(nfp_event.importance, 5)
        self.assertEqual(nfp_event.category, "employment")
        self.assertEqual(nfp_event.currency, "USD")
    
    def test_monthly_fixed_day_events(self):
        """Test monthly fixed day events (CPI) generation"""
        start_date = datetime(2025, 9, 1)
        end_date = datetime(2025, 9, 30)
        
        recurring_events = self.calendar.get_recurring_events(start_date, end_date)
        
        # Find US CPI event
        us_cpi = next((e for e in recurring_events if "CPI" in e.event_name), None)
        self.assertIsNotNone(us_cpi)
        
        # Test US CPI
        self.assertEqual(us_cpi.date.day, 12)
        self.assertEqual(us_cpi.time_local, "08:30 ET")
        self.assertEqual(us_cpi.event_name, "US CPI (Core) YoY")
        self.assertEqual(us_cpi.category, "inflation")
        self.assertEqual(us_cpi.importance, 5)
    
    def test_central_bank_events_boj(self):
        """Test BOJ meeting events generation with timezone conversion"""
        # Test range that includes September 2025 BOJ meeting
        start_date = datetime(2025, 9, 1)
        end_date = datetime(2025, 9, 30)
        
        cb_events = self.calendar.get_central_bank_events(start_date, end_date)
        
        # Find BOJ event
        boj_event = next((e for e in cb_events if e.country == "Japan"), None)
        self.assertIsNotNone(boj_event, "Should find BOJ meeting in September 2025")
        
        # Check UTC datetime (JST 12:00 = UTC 03:00)
        self.assertEqual(boj_event.date.date(), datetime(2025, 9, 19).date())
        self.assertEqual(boj_event.date.hour, 3)  # UTC time
        self.assertEqual(boj_event.event_name, "BOJ Policy Decision")
        self.assertEqual(boj_event.time_local, "12:00 JST")
        self.assertEqual(boj_event.importance, 5)
        self.assertEqual(boj_event.category, "monetary_policy")
    
    def test_central_bank_events_fomc(self):
        """Test FOMC meeting events generation with timezone conversion"""
        # Test range that includes September 2025 FOMC meeting  
        start_date = datetime(2025, 9, 1)
        end_date = datetime(2025, 9, 30)
        
        cb_events = self.calendar.get_central_bank_events(start_date, end_date)
        
        # Find FOMC event
        fomc_event = next((e for e in cb_events if e.country == "United States" and "FOMC" in e.event_name), None)
        self.assertIsNotNone(fomc_event, "Should find FOMC meeting in September 2025")
        
        # Check UTC datetime (ET 14:00 = UTC 19:00)
        self.assertEqual(fomc_event.date.date(), datetime(2025, 9, 17).date())
        self.assertEqual(fomc_event.date.hour, 19)  # UTC time
        self.assertEqual(fomc_event.event_name, "FOMC Rate Decision")
        self.assertEqual(fomc_event.time_local, "14:00 ET")
        self.assertEqual(fomc_event.currency, "USD")
    
    def test_get_events_integration(self):
        """Test get_events integrates all event types"""
        start_date = datetime(2025, 9, 1)
        end_date = datetime(2025, 9, 30)
        
        all_events = self.calendar.get_events(start_date, end_date)
        
        # Should have multiple types of events
        event_types = set(event.category for event in all_events)
        expected_types = {"employment", "inflation", "monetary_policy"}
        
        self.assertTrue(expected_types.issubset(event_types), 
                       f"Should include event types {expected_types}, got {event_types}")
        
        # Should be sorted by date
        dates = [event.date for event in all_events]
        self.assertEqual(dates, sorted(dates), "Events should be sorted by date")
        
        # All events should be EconomicEvent instances with proper structure
        for event in all_events:
            self.assertIsInstance(event, EconomicEvent)
            self.assertIsInstance(event.date, datetime)
            self.assertIsNotNone(event.time_local)
            self.assertIsNotNone(event.event_name)
    
    def test_today_events(self):
        """Test get_today_events method with UTC handling"""
        today_events = self.calendar.get_today_events()
        
        # All events should be today (but may be empty if no events today)
        today_utc = datetime.now(timezone.utc).date()
        for event in today_events:
            self.assertEqual(event.date.date(), today_utc, 
                           f"Event {event.event_name} should be today (UTC), got {event.date.date()}")
        
        # Test that method works (doesn't crash) even if no events today
        self.assertIsInstance(today_events, list)
    
    def test_upcoming_events(self):
        """Test get_upcoming_events method with UTC handling"""
        upcoming = self.calendar.get_upcoming_events(days_ahead=7)
        
        # All events should be within next 7 days (UTC)
        now = datetime.now(timezone.utc)
        max_date = now + timedelta(days=7)
        
        for event in upcoming:
            # Remove timezone info for comparison since test data is naive
            event_date = event.date.replace(tzinfo=None) if event.date.tzinfo else event.date
            now_naive = now.replace(tzinfo=None)
            max_date_naive = max_date.replace(tzinfo=None)
            
            self.assertGreaterEqual(event_date, now_naive, 
                                   f"Event {event.event_name} should be in future")
            self.assertLessEqual(event_date, max_date_naive, 
                                f"Event {event.event_name} should be within 7 days")
    
    def test_recent_events(self):
        """Test get_recent_events method with UTC handling"""
        recent = self.calendar.get_recent_events(days_back=3)
        
        # All events should be within last 3 days (UTC)
        now = datetime.now(timezone.utc)
        min_date = now - timedelta(days=3)
        
        for event in recent:
            # Remove timezone info for comparison since test data is naive
            event_date = event.date.replace(tzinfo=None) if event.date.tzinfo else event.date
            now_naive = now.replace(tzinfo=None)
            min_date_naive = min_date.replace(tzinfo=None)
            
            self.assertGreaterEqual(event_date, min_date_naive, 
                                   f"Event {event.event_name} should be within last 3 days")
            self.assertLessEqual(event_date, now_naive, 
                                f"Event {event.event_name} should be in past")
    
    def test_high_importance_filtering(self):
        """Test filtering of high importance events"""
        # Create test events with different importance levels
        start_date = datetime(2025, 9, 1)
        end_date = datetime(2025, 9, 30)
        
        all_events = self.calendar.get_events(start_date, end_date)
        high_importance = self.calendar.get_high_importance_events(all_events)
        
        # All filtered events should have importance >= 4
        for event in high_importance:
            self.assertGreaterEqual(event.importance, 4, 
                                   f"Event {event.event_name} should have high importance")
    
    def test_economic_event_to_dict(self):
        """Test EconomicEvent to_dict conversion with new structure"""
        event = EconomicEvent(
            date=datetime(2025, 9, 19, 3, 0, 0),  # UTC time
            time_local="12:00 JST",
            event_name="BOJ Policy Decision",
            country="Japan",
            currency="JPY",
            importance=5,
            category="monetary_policy",
            source="Bank of Japan",
            description="Test description"
        )
        
        event_dict = event.to_dict()
        
        expected_keys = {'date', 'time', 'event_name', 'country', 'currency', 
                        'importance', 'category', 'source', 'description'}
        self.assertEqual(set(event_dict.keys()), expected_keys)
        
        self.assertEqual(event_dict['date'], '2025-09-19')
        self.assertEqual(event_dict['time'], '12:00 JST')  # Uses time_local
        self.assertEqual(event_dict['importance'], 5)
        self.assertEqual(event_dict['currency'], 'JPY')
    
    def test_calendar_summary(self):
        """Test get_calendar_summary method structure"""
        summary = self.calendar.get_calendar_summary(days_ahead=7)
        
        expected_keys = {'today', 'upcoming', 'recent', 'high_importance_upcoming'}
        self.assertEqual(set(summary.keys()), expected_keys)
        
        # Each section should be a list
        for key in expected_keys:
            self.assertIsInstance(summary[key], list, f"{key} should be a list")
        
        # High importance upcoming should be subset of upcoming
        upcoming_names = {event['event_name'] for event in summary['upcoming']}
        high_imp_names = {event['event_name'] for event in summary['high_importance_upcoming']}
        
        self.assertTrue(high_imp_names.issubset(upcoming_names), 
                       "High importance events should be subset of upcoming events")
        
        # All events in summary should have proper structure
        for section in summary.values():
            for event_dict in section:
                self.assertIn('event_name', event_dict)
                self.assertIn('date', event_dict)
                self.assertIn('importance', event_dict)
    
    def test_format_for_brief(self):
        """Test format_for_brief method with new time_local field"""
        # Test with empty events
        empty_format = self.calendar.format_for_brief([])
        self.assertEqual(empty_format, "No major economic events scheduled.")
        
        # Test with sample events
        start_date = datetime(2025, 9, 1)
        end_date = datetime(2025, 9, 30)
        events = self.calendar.get_events(start_date, end_date)
        
        if events:  # Only test if we have events
            formatted = self.calendar.format_for_brief(events[:2])  # Test first 2
            
            # Should contain event names and star ratings
            for event in events[:2]:
                self.assertIn(event.event_name, formatted)
                self.assertIn("⭐", formatted)  # Should have star ratings
                if event.time_local:
                    self.assertIn(event.time_local, formatted)  # Should show local time
    
    def test_finnhub_integration(self):
        """Test Finnhub API integration (mocked)"""
        # Test that Finnhub method exists and returns empty list when no API key
        start_date = datetime(2025, 9, 1)
        end_date = datetime(2025, 9, 30)
        
        # Without API key, should return empty list
        finnhub_events = self.calendar.fetch_finnhub_events(start_date, end_date)
        self.assertEqual(finnhub_events, [])
        
        # Test that calendar still works without Finnhub
        all_events = self.calendar.get_events(start_date, end_date)
        self.assertGreaterEqual(len(all_events), 2)  # Should have at least CB meetings and NFP
    
    def test_event_deduplication(self):
        """Test that duplicate events are properly deduplicated"""
        start_date = datetime(2025, 9, 1)
        end_date = datetime(2025, 9, 30)
        
        # Get all events
        all_events = self.calendar.get_events(start_date, end_date)
        
        # Check no duplicates (same name and date)
        seen = set()
        for event in all_events:
            key = (event.event_name, event.date.date())
            self.assertNotIn(key, seen, f"Duplicate event found: {event.event_name} on {event.date.date()}")
            seen.add(key)


if __name__ == "__main__":
    # Run the tests
    unittest.main(verbosity=2)