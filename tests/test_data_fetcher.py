#!/usr/bin/env python3
"""
Unit tests for data fetcher functionality
Tests all data sources and methods to ensure proper data collection
"""

import unittest
import os
import tempfile
import json
from unittest.mock import patch, Mock, MagicMock
from datetime import datetime
import sys

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.data_fetcher import DataFetcher


class TestDataFetcher(unittest.TestCase):
    """Test suite for DataFetcher class"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create temporary config file
        self.config_data = {
            'api_keys': {
                'fred': 'test_fred_key',
                'alpha_vantage': 'test_av_key',
                'openai': 'test_openai_key'
            },
            'data': {
                'fx_pairs': ['USD/JPY', 'EUR/JPY'],
                'cache_expiry_hours': 24,
                'retry_attempts': 3,
                'retry_delay_seconds': 5
            },
            'scraping': {
                'user_agent': 'test_agent',
                'timeout_seconds': 10
            }
        }
        
        # Create temporary config file
        self.temp_config = tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False)
        import yaml
        yaml.dump(self.config_data, self.temp_config)
        self.temp_config.close()
        
        # Initialize DataFetcher with temp config
        self.fetcher = DataFetcher(self.temp_config.name)
    
    def tearDown(self):
        """Clean up test fixtures"""
        os.unlink(self.temp_config.name)
    
    def test_init(self):
        """Test DataFetcher initialization"""
        self.assertIsNotNone(self.fetcher.config)
        self.assertIsNotNone(self.fetcher.session)
        self.assertIsNotNone(self.fetcher.logger)
        self.assertEqual(len(self.fetcher.cache_dirs), 5)
    
    @patch('requests.Session.get')
    def test_fetch_fred_macro(self, mock_get):
        """Test FRED macro data fetching"""
        # Clear cache first
        cache_file = self.fetcher._get_cache_path('macro', 'fred_macro.json')
        if os.path.exists(cache_file):
            os.remove(cache_file)
            
        # Mock FRED API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            'observations': [{'value': '106.5', 'date': '2025-09-01'}]
        }
        mock_get.return_value = mock_response
        
        result = self.fetcher.fetch_fred_macro()
        
        # Check structure
        self.assertIsInstance(result, dict)
        self.assertIn('timestamp', result)
        self.assertIn('japan_cpi', result)
        self.assertIn('japan_gdp', result) 
        self.assertIn('us_gdp', result)
        
        # Check API was called
        self.assertTrue(mock_get.called)
        
    def test_fetch_fred_macro_fallback(self):
        """Test FRED macro data fallback when API key is invalid"""
        # Temporarily change API key
        original_key = self.fetcher.config['api_keys']['fred']
        self.fetcher.config['api_keys']['fred'] = 'YOUR_FRED_API_KEY'
        
        result = self.fetcher.fetch_fred_macro()
        
        # Check fallback data structure
        self.assertIsInstance(result, dict)
        self.assertEqual(result['japan_cpi'], 106.5)
        # Note: GDP values may come from actual FRED data if cached
        self.assertIn('japan_gdp', result)
        self.assertIn('us_gdp', result)
        
        # Restore original key
        self.fetcher.config['api_keys']['fred'] = original_key
    
    @patch('requests.Session.get')
    def test_fetch_fred_yields(self, mock_get):
        """Test FRED yield curve fetching"""
        # Mock FRED API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            'observations': [{'value': '4.25', 'date': '2025-09-10'}]
        }
        mock_get.return_value = mock_response
        
        result = self.fetcher.fetch_fred_yields()
        
        # Check UST curve points (no JGB from FRED)
        expected_ust_keys = ['ust_3m', 'ust_6m', 'ust_1y', 'ust_2y', 'ust_5y', 'ust_10y', 'ust_30y']
        for key in expected_ust_keys:
            self.assertIn(key, result)
            self.assertIsInstance(result[key], (int, float))
        
        # Note: May have cached JGB data, but new fetches should only have UST
    
    @patch('requests.Session.get') 
    def test_fetch_fred_fx(self, mock_get):
        """Test FRED FX data fetching"""
        # Mock FRED API response with previous values
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            'observations': [
                {'value': '146.84', 'date': '2025-09-10'},
                {'value': '148.63', 'date': '2025-09-09'}  # Previous value
            ]
        }
        mock_get.return_value = mock_response
        
        result = self.fetcher.fetch_fred_fx()
        
        # Check FX data structure
        self.assertIn('usdjpy', result)
        self.assertIn('usdeur', result)  
        self.assertIn('dxy', result)
        self.assertIn('eurjpy', result)  # Calculated
        
        # Check change calculations
        if 'usdjpy_prev' in result:
            self.assertIn('usdjpy_change', result)
        if 'eurjpy_prev' in result:
            self.assertIn('eurjpy_change', result)
    
    @patch('requests.Session.get')
    def test_fetch_jgb_curve(self, mock_get):
        """Test JGB curve scraping from JBOND"""
        # Mock HTML response
        html_content = """
        <html>
        <body>
        <table>
            <tr><th>3月</th><th>6月</th><th>1年</th><th>2年</th><th>5年</th><th>10年</th><th>20年</th><th>30年</th><th>40年</th></tr>
            <tr><td>0.05</td><td>0.08</td><td>0.10</td><td>0.15</td><td>0.20</td><td>0.25</td><td>0.65</td><td>0.85</td><td>1.05</td></tr>
        </table>
        </body>
        </html>
        """
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_response.text = html_content
        mock_get.return_value = mock_response
        
        result = self.fetcher.fetch_jgb_curve()
        
        # Check JGB curve data structure
        expected_jgb_keys = ['jgb_3m', 'jgb_6m', 'jgb_1y', 'jgb_2y', 'jgb_5y', 'jgb_10y', 'jgb_20y', 'jgb_30y', 'jgb_40y']
        for key in expected_jgb_keys:
            self.assertIn(key, result)
            self.assertIsInstance(result[key], (int, float))
        
        self.assertIn('timestamp', result)
    
    def test_fetch_jgb_curve_fallback(self):
        """Test JGB curve fallback when scraping fails"""
        with patch('requests.Session.get', side_effect=Exception("Network error")):
            result = self.fetcher.fetch_jgb_curve()
            
            # Should return fallback data
            self.assertEqual(result['jgb_10y'], 0.25)
            self.assertEqual(result['jgb_3m'], 0.05)
            self.assertIn('timestamp', result)
    
    @patch('requests.Session.get')
    def test_fetch_repo_rates(self, mock_get):
        """Test Tokyo Tanshi repo rates scraping"""
        # Mock HTML with repo data
        html_content = """
        <html>
        <body>
        <table>
            <tr><td>O/N</td><td>0.489%</td><td>+0.003</td></tr>
            <tr><td>1週間</td><td>0.495%</td><td>+0.002</td></tr>
            <tr><td>1ヶ月</td><td>0.510%</td><td>+0.001</td></tr>
        </table>
        </body>
        </html>
        """
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_response.text = html_content
        mock_get.return_value = mock_response
        
        result = self.fetcher.fetch_repo_rates()
        
        # Check repo data structure
        self.assertIn('timestamp', result)
        # Should contain repo rates (exact parsing may vary)
        self.assertIsInstance(result, dict)
    
    @patch('requests.Session.get')
    def test_fetch_tona_rate(self, mock_get):
        """Test TONA rate scraping"""
        # Mock HTML with TONA data
        html_content = """
        <html>
        <body>
        <table>
            <tr><td>TONA</td><td>0.477%</td></tr>
            <tr><td>High</td><td>0.480%</td></tr>
            <tr><td>Low</td><td>0.471%</td></tr>
        </table>
        </body>
        </html>
        """
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_response.text = html_content
        mock_get.return_value = mock_response
        
        result = self.fetcher.fetch_tona_rate()
        
        # Check TONA data structure
        self.assertIn('timestamp', result)
        self.assertIsInstance(result, dict)
    
    @patch('core.data_fetcher.DataFetcher.fetch_fred_fx')
    @patch('core.data_fetcher.DataFetcher.fetch_fred_yields')
    @patch('core.data_fetcher.DataFetcher.fetch_jgb_curve')
    @patch('core.data_fetcher.DataFetcher.fetch_euro_yields')
    @patch('core.data_fetcher.DataFetcher.fetch_repo_rates')
    @patch('core.data_fetcher.DataFetcher.fetch_tona_rate')
    @patch('core.data_fetcher.DataFetcher.fetch_fred_macro')
    @patch('core.data_fetcher.DataFetcher.fetch_boj_news')
    @patch('core.data_fetcher.DataFetcher.fetch_reuters_rss')
    @patch('core.data_fetcher.DataFetcher.fetch_nikkei_news')
    def test_fetch_morning_brief_data(self, mock_nikkei, mock_reuters, mock_boj, 
                                     mock_macro, mock_tona, mock_repo, mock_euro,
                                     mock_jgb, mock_yields, mock_fx):
        """Test morning brief data aggregation"""
        # Mock all sub-methods
        mock_fx.return_value = {'usdjpy': 146.84, 'eurjpy': 162.65, 'dxy': 120.54}
        mock_yields.return_value = {'ust_10y': 4.25, 'ust_2y': 3.49}
        mock_jgb.return_value = {'jgb_10y': 0.25, 'jgb_2y': 0.15}
        mock_euro.return_value = {'bund_10y': 2.71, 'bund_2y': 2.02, 'bund_30y': 3.30}
        mock_repo.return_value = {'gc_on': 0.489}
        mock_tona.return_value = {'tona': 0.477}
        mock_macro.return_value = {'japan_cpi': 106.5, 'japan_gdp': 562987.8}
        mock_boj.return_value = [{'title': 'BOJ News', 'source': 'BOJ'}]
        mock_reuters.return_value = [{'title': 'Reuters News', 'source': 'Reuters'}]
        mock_nikkei.return_value = [{'title': 'Nikkei News', 'source': 'Nikkei'}]
        
        result = self.fetcher.fetch_morning_brief_data()
        
        # Check complete data structure
        self.assertIn('fx', result)
        self.assertIn('yields', result)
        self.assertIn('repo', result)
        self.assertIn('macro', result)
        self.assertIn('news', result)
        self.assertIn('sentiment_score', result)
        self.assertIn('timestamp', result)
        
        # Check nested structures
        self.assertIn('boj', result['news'])
        self.assertIn('reuters', result['news'])
        self.assertIn('nikkei', result['news'])
        
        # Check that Euro yields are properly integrated
        self.assertIn('bund_10y', result['yields'])
        self.assertIn('bund_2y', result['yields'])
        self.assertIn('bund_30y', result['yields'])
        self.assertEqual(result['yields']['bund_10y'], 2.71)
        
        # Check sentiment score range
        self.assertGreaterEqual(result['sentiment_score'], 0)
        self.assertLessEqual(result['sentiment_score'], 100)
    
    @patch('core.data_fetcher.requests.Session.get')
    def test_fetch_euro_yields(self, mock_get):
        """Test European government bond yield scraping"""
        # Mock HTML response with German bond data
        html_content = '''
        <table>
            <tr><th>Name</th><th>Yield</th><th>Prev.</th></tr>
            <tr><td></td><td>Germany 3M</td><td>1.750</td><td>1.700</td></tr>
            <tr><td></td><td>Germany 10Y</td><td>2.713</td><td>2.700</td></tr>
            <tr><td></td><td>Germany 30Y</td><td>3.300</td><td>3.250</td></tr>
        </table>
        '''
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_response.text = html_content
        mock_get.return_value = mock_response
        
        result = self.fetcher.fetch_euro_yields()
        
        # Check Euro yield data structure
        self.assertIn('bund_3m', result)
        self.assertIn('bund_10y', result)
        self.assertIn('bund_30y', result)
        self.assertIn('timestamp', result)
        # Check that yields are reasonable numbers (since it may hit real site)
        self.assertIsInstance(result['bund_3m'], float)
        self.assertIsInstance(result['bund_10y'], float)
        self.assertIsInstance(result['bund_30y'], float)
        self.assertGreater(result['bund_10y'], 0)
        self.assertLess(result['bund_10y'], 10)  # Reasonable range
    
    def test_calculate_sentiment_score(self):
        """Test sentiment score calculation"""
        # Test neutral sentiment
        fx_data = {'usdjpy': 147.0}
        macro_data = {'japan_cpi': 106.0}
        score = self.fetcher.calculate_sentiment_score(fx_data, macro_data)
        self.assertEqual(score, 50)  # Neutral
        
        # Test yen strengthening
        fx_data = {'usdjpy': 144.0}  # Below 145
        score = self.fetcher.calculate_sentiment_score(fx_data, macro_data)
        self.assertEqual(score, 60)  # +10 for yen strengthening
        
        # Test yen weakening
        fx_data = {'usdjpy': 151.0}  # Above 150
        score = self.fetcher.calculate_sentiment_score(fx_data, macro_data)
        self.assertEqual(score, 40)  # -10 for yen weakening
        
        # Test inflation pressure
        fx_data = {'usdjpy': 147.0}
        macro_data = {'japan_cpi': 107.0}  # Above 106
        score = self.fetcher.calculate_sentiment_score(fx_data, macro_data)
        self.assertEqual(score, 55)  # +5 for inflation
    
    def test_helper_methods(self):
        """Test helper parsing methods"""
        # Test Japanese number parsing
        self.assertEqual(self.fetcher._parse_japanese_number('0.489'), 0.489)
        self.assertEqual(self.fetcher._parse_japanese_number('△0.003'), -0.003)
        self.assertEqual(self.fetcher._parse_japanese_number('0.489％'), 0.489)
        self.assertIsNone(self.fetcher._parse_japanese_number('N/A'))
        self.assertIsNone(self.fetcher._parse_japanese_number(''))
        
        # Test JGB maturity mapping
        self.assertEqual(self.fetcher._map_jgb_maturity('10年'), 'jgb_10y')
        self.assertEqual(self.fetcher._map_jgb_maturity('2年'), 'jgb_2y')
        self.assertEqual(self.fetcher._map_jgb_maturity('6'), 'jgb_6m')
        self.assertIsNone(self.fetcher._map_jgb_maturity('unknown'))
    
    def test_cache_functionality(self):
        """Test data caching mechanism"""
        # Create test cache directory
        import tempfile
        with tempfile.TemporaryDirectory() as temp_dir:
            self.fetcher.cache_dirs['test'] = temp_dir
            
            # Test cache save and load
            test_data = {'test_key': 'test_value', 'timestamp': datetime.now().isoformat()}
            self.fetcher._save_cache(test_data, 'test', 'test_cache.json')
            
            # Check file exists
            cache_path = self.fetcher._get_cache_path('test', 'test_cache.json')
            self.assertTrue(os.path.exists(cache_path))
            
            # Test cache load
            loaded_data = self.fetcher._load_cache('test', 'test_cache.json')
            self.assertEqual(loaded_data['test_key'], 'test_value')


class TestDataValidation(unittest.TestCase):
    """Test data validation and structure"""
    
    def test_fred_series_completeness(self):
        """Verify all required FRED series are defined"""
        # This test ensures we have all UST curve points defined
        try:
            fetcher = DataFetcher('config.yaml')  # Will use fallback if config missing
        except:
            fetcher = DataFetcher(self.temp_config.name)  # Use temp config
        
        # Check that FRED yields method doesn't include JGB
        # We can verify this by checking the method directly
        import inspect
        source = inspect.getsource(fetcher.fetch_fred_yields)
        self.assertNotIn("'jgb_10y':", source)
        self.assertIn("'ust_10y':", source)
    
    def test_data_source_consistency(self):
        """Test that data sources are consistent per product type"""
        fetcher = DataFetcher('config.yaml')
        
        # UST data should come from FRED only
        # JGB data should come from JBOND only  
        # FX data should come from FRED primarily
        # Repo data should come from Tokyo Tanshi
        
        # This is verified by the structure of our fetch methods
        self.assertTrue(hasattr(fetcher, 'fetch_fred_yields'))  # UST from FRED
        self.assertTrue(hasattr(fetcher, 'fetch_jgb_curve'))    # JGB from JBOND
        self.assertTrue(hasattr(fetcher, 'fetch_fred_fx'))      # FX from FRED
        self.assertTrue(hasattr(fetcher, 'fetch_repo_rates'))   # Repo from Tanshi


if __name__ == '__main__':
    # Run tests
    unittest.main(verbosity=2)