"""
Unit tests for all data fetchers in YenSense.AI
Tests each product/data source we want to fetch.
"""

import unittest
import json
import os
import sys
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.data_fetcher import DataFetcher


class TestDataFetchers(unittest.TestCase):
    """Test all data fetching methods"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.fetcher = DataFetcher()
        # Clear any existing cache for clean tests
        self.clear_test_cache()
    
    def tearDown(self):
        """Clean up after tests"""
        self.clear_test_cache()
    
    def clear_test_cache(self):
        """Remove cached files to ensure fresh data"""
        cache_files = [
            'data/input/fx/fx_rates.json',
            'data/input/macro/fred_macro.json',
            'data/input/macro/fred_yields.json',
            'data/input/macro/jgb_curve.json',
            'data/input/repo/repo_rates.json',
            'data/input/repo/tona_rate.json'
        ]
        for cache_file in cache_files:
            if os.path.exists(cache_file):
                os.remove(cache_file)
    
    def test_fx_rates_fetch(self):
        """Test FX rates fetching from Alpha Vantage"""
        print("Testing FX rates fetch...")
        
        data = self.fetcher.fetch_fx_rates_alpha()
        
        # Verify structure
        self.assertIsInstance(data, dict)
        self.assertIn('timestamp', data)
        
        # Check for USD/JPY rate
        if 'USD/JPY' in data:
            rate = data['USD/JPY']
            self.assertIsInstance(rate, (int, float))
            self.assertGreater(rate, 100)  # USD/JPY should be > 100
            self.assertLess(rate, 200)     # and < 200 (reasonable range)
            print(f"✓ USD/JPY: {rate}")
        
        # Check for EUR/JPY rate  
        if 'EUR/JPY' in data:
            rate = data['EUR/JPY']
            self.assertIsInstance(rate, (int, float))
            self.assertGreater(rate, 120)  # EUR/JPY should be > 120
            self.assertLess(rate, 200)     # and < 200
            print(f"✓ EUR/JPY: {rate}")
        
    
    def test_ust_yields_fetch(self):
        """Test US Treasury yields from FRED"""
        print("Testing UST yields fetch...")
        
        data = self.fetcher.fetch_fred_yields()
        
        # Verify structure
        self.assertIsInstance(data, dict)
        self.assertIn('timestamp', data)
        
        # Check for key yield points
        expected_yields = ['ust_2y', 'ust_5y', 'ust_10y', 'ust_30y']
        for yield_key in expected_yields:
            self.assertIn(yield_key, data, f"Missing {yield_key}")
            yield_val = data[yield_key]
            self.assertIsInstance(yield_val, (int, float))
            self.assertGreater(yield_val, 0)    # Yields should be positive
            self.assertLess(yield_val, 10)      # and reasonable
            print(f"✓ {yield_key}: {yield_val}%")
    
    def test_japan_cpi_fetch(self):
        """Test Japan CPI from FRED"""
        print("Testing Japan CPI fetch...")
        
        data = self.fetcher.fetch_fred_macro()
        
        # Verify structure
        self.assertIsInstance(data, dict)
        self.assertIn('japan_cpi', data)
        self.assertIn('timestamp', data)
        
        # Verify CPI is reasonable
        cpi = data['japan_cpi']
        self.assertIsInstance(cpi, (int, float))
        self.assertGreater(cpi, -5)   # CPI should be > -5%
        self.assertLess(cpi, 15)      # and < 15%
        
        print(f"✓ Japan CPI: {cpi}%")
    
    def test_jgb_curve_fetch(self):
        """Test JGB yield curve scraping"""
        print("Testing JGB curve fetch...")
        
        data = self.fetcher.fetch_jgb_curve()
        
        # Verify structure
        self.assertIsInstance(data, dict)
        self.assertIn('timestamp', data)
        
        # Check for key JGB yields
        expected_jgbs = ['jgb_2y', 'jgb_5y', 'jgb_10y', 'jgb_20y', 'jgb_30y', 'jgb_40y']
        found_yields = 0
        
        for jgb_key in expected_jgbs:
            if jgb_key in data:
                found_yields += 1
                yield_val = data[jgb_key]
                self.assertIsInstance(yield_val, (int, float))
                self.assertGreater(yield_val, -1)   # JGB can be negative but reasonable
                self.assertLess(yield_val, 10)      # and < 10%
                print(f"✓ {jgb_key}: {yield_val}%")
        
        # Should have at least 4 JGB yields
        self.assertGreaterEqual(found_yields, 4, f"Only found {found_yields} JGB yields")
        
        # Check for data date
        if 'data_date' in data:
            print(f"✓ JGB data date: {data['data_date']}")
    
    def test_repo_rates_fetch(self):
        """Test repo rates scraping"""
        print("Testing repo rates fetch...")
        
        data = self.fetcher.fetch_repo_rates()
        
        # Verify structure
        self.assertIsInstance(data, dict)
        self.assertIn('timestamp', data)
        
        # Check for repo rates
        expected_repos = ['gc_on', 'gc_1w', 'gc_1m']
        found_rates = 0
        
        for repo_key in expected_repos:
            if repo_key in data:
                found_rates += 1
                rate_val = data[repo_key]
                self.assertIsInstance(rate_val, (int, float))
                self.assertGreater(rate_val, -2)   # Repo rates can be low but reasonable
                self.assertLess(rate_val, 5)       # and < 5%
                print(f"✓ {repo_key}: {rate_val}%")
        
        # Should have at least 1 repo rate
        self.assertGreaterEqual(found_rates, 1, f"Only found {found_rates} repo rates")
    
    def test_tona_rate_fetch(self):
        """Test TONA rate scraping"""
        print("Testing TONA rate fetch...")
        
        data = self.fetcher.fetch_tona_rate()
        
        # Verify structure
        self.assertIsInstance(data, dict)
        self.assertIn('timestamp', data)
        
        # Check for TONA rate
        if 'tona_rate' in data:
            tona_val = data['tona_rate']
            self.assertIsInstance(tona_val, (int, float))
            self.assertGreater(tona_val, -2)   # TONA can be low but reasonable
            self.assertLess(tona_val, 5)       # and < 5%
            print(f"✓ TONA rate: {tona_val}%")
        else:
            print("! TONA rate not found (may be using fallback)")
    
    def test_morning_brief_data_aggregation(self):
        """Test the complete morning brief data aggregation"""
        print("Testing morning brief data aggregation...")
        
        data = self.fetcher.fetch_morning_brief_data()
        
        # Verify structure
        self.assertIsInstance(data, dict)
        self.assertIn('timestamp', data)
        
        # Check that we have data from major categories by looking at actual keys
        print(f"Morning brief data keys: {list(data.keys())}")
        
        # Count non-timestamp keys that contain data
        data_keys = [k for k in data.keys() if k != 'timestamp' and data.get(k)]
        found_categories = len(data_keys)
        
        print(f"✓ Found {found_categories} data categories: {data_keys}")
        
        # Should have some data categories
        self.assertGreaterEqual(found_categories, 1, f"Only found {found_categories} data categories")
    
    def test_data_persistence(self):
        """Test that data is properly saved to cache files"""
        print("Testing data persistence...")
        
        # Fetch some data to trigger caching
        self.fetcher.fetch_fx_rates_alpha()
        self.fetcher.fetch_fred_yields()
        self.fetcher.fetch_jgb_curve()
        self.fetcher.fetch_repo_rates()
        
        # Check that cache files were created
        expected_files = [
            'data/input/fx/fx_rates.json',
            'data/input/macro/fred_yields.json',
            'data/input/macro/jgb_curve.json',
            'data/input/repo/repo_rates.json'
        ]
        
        for cache_file in expected_files:
            if os.path.exists(cache_file):
                print(f"✓ Cache file created: {cache_file}")
                # Verify it contains valid JSON
                with open(cache_file, 'r') as f:
                    cached_data = json.load(f)
                    self.assertIsInstance(cached_data, dict)
                    self.assertIn('timestamp', cached_data)
            else:
                print(f"! Cache file missing: {cache_file}")


def run_data_tests():
    """Run all data fetcher tests and show results"""
    print("="*60)
    print("YENSENSE.AI - DATA FETCHER TESTS")
    print("="*60)
    print()
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestDataFetchers)
    
    # Run tests with detailed output
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(suite)
    
    print()
    print("="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.failures:
        print("\nFAILURES:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback}")
    
    if result.errors:
        print("\nERRORS:")  
        for test, traceback in result.errors:
            print(f"- {test}: {traceback}")
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_data_tests()
    sys.exit(0 if success else 1)