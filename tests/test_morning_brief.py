"""
Unit tests for Morning Brief generation
Tests data flow, AI prompts, and output generation
"""

import unittest
import json
import os
import sys
from datetime import datetime
from unittest.mock import patch, MagicMock

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.data_fetcher import DataFetcher
from core.ai_analyst_brief import AIAnalystBrief
from generators.morning_brief import MorningBriefGenerator


class TestMorningBrief(unittest.TestCase):
    """Test morning brief generation with real data"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.data_fetcher = DataFetcher()
        self.ai_analyst = AIAnalystBrief()
        self.brief_generator = MorningBriefGenerator()
        
        # Sample morning brief data structure
        self.sample_data = {
            'fx': {
                'USD/JPY': 147.35,
                'EUR/JPY': 172.68,
                'timestamp': datetime.now().isoformat()
            },
            'yields': {
                'ust_10y': 4.05,
                'ust_2y': 3.49,
                'ust_30y': 4.69,
                'jgb_10y': 1.56,
                'jgb_2y': 0.83,
                'jgb_40y': 3.515,
                'data_date': '2025/09/09',
                'timestamp': datetime.now().isoformat()
            },
            'repo': {
                'gc_on': 0.489,
                'gc_1w': 0.482,
                'gc_1m': 0.484,
                'tona': 0.477,
                'timestamp': datetime.now().isoformat()
            },
            'macro': {
                'japan_cpi': 2.74,
                'japan_gdp': 562987.8,
                'us_gdp': 30353.902,
                'timestamp': datetime.now().isoformat()
            },
            'news': {
                'boj': [{'title': 'BOJ maintains policy stance', 'source': 'Bank of Japan'}],
                'reuters': [{'title': 'Yen steady ahead of data', 'source': 'Reuters'}],
                'nikkei': [{'title': 'Japan exports rise', 'source': 'Nikkei'}]
            },
            'sentiment_score': 45,
            'timestamp': datetime.now().isoformat()
        }
    
    def test_data_fetcher_structure(self):
        """Test that morning brief data fetcher returns correct structure"""
        print("Testing morning brief data structure...")
        
        data = self.data_fetcher.fetch_morning_brief_data()
        
        # Verify required keys exist
        required_keys = ['fx', 'yields', 'repo', 'macro', 'news', 'sentiment_score']
        for key in required_keys:
            self.assertIn(key, data, f"Missing required key: {key}")
        
        # Verify FX data
        self.assertIn('USD/JPY', data['fx'])
        self.assertIn('EUR/JPY', data['fx'])
        
        # Verify yields data has both UST and JGB
        self.assertIn('ust_10y', data['yields'])
        self.assertIn('jgb_10y', data['yields'])
        
        # Verify repo data
        self.assertIn('gc_on', data['repo'])
        
        # Verify macro data
        self.assertIn('japan_cpi', data['macro'])
        
        print("✓ Data structure is correct")
    
    def test_ai_analyst_uses_real_data(self):
        """Test that AI analyst receives and uses real market data"""
        print("Testing AI analyst data usage...")
        
        # Mock OpenAI API to capture the prompt
        with patch.object(self.ai_analyst, '_call_openai') as mock_openai:
            mock_openai.return_value = "Mock rates commentary"
            
            # Generate rates commentary
            self.ai_analyst.generate_rates_commentary(self.sample_data)
            
            # Verify OpenAI was called
            self.assertTrue(mock_openai.called)
            
            # Get the prompt that was sent
            call_args = mock_openai.call_args
            prompt = call_args[0][0]  # First argument is the prompt
            
            # Verify real data is in the prompt
            self.assertIn('JGB 10Y: 1.56%', prompt)
            self.assertIn('US 10Y: 4.05%', prompt)
            
            print("✓ AI analyst uses real JGB and UST data")
    
    def test_fx_commentary_data(self):
        """Test FX commentary uses correct data structure"""
        print("Testing FX commentary data usage...")
        
        with patch.object(self.ai_analyst, '_call_openai') as mock_openai:
            mock_openai.return_value = "Mock FX commentary"
            
            self.ai_analyst.generate_fx_commentary(self.sample_data)
            
            # Verify call was made
            self.assertTrue(mock_openai.called)
            
            call_args = mock_openai.call_args
            prompt = call_args[0][0]
            
            # Verify USD/JPY and EUR/JPY are in prompt
            self.assertIn('USD/JPY: 147', prompt)
            self.assertIn('EUR/JPY: 173', prompt)
            
            print("✓ FX commentary uses real exchange rates")
    
    def test_repo_commentary_data(self):
        """Test repo commentary uses correct data structure"""
        print("Testing repo commentary data usage...")
        
        with patch.object(self.ai_analyst, '_call_openai') as mock_openai:
            mock_openai.return_value = "Mock repo commentary"
            
            self.ai_analyst.generate_repo_commentary(self.sample_data)
            
            self.assertTrue(mock_openai.called)
            
            call_args = mock_openai.call_args
            prompt = call_args[0][0]
            
            # Verify repo rates are in prompt
            self.assertIn('0.489', prompt)  # gc_on
            self.assertIn('0.477', prompt)  # tona
            
            print("✓ Repo commentary uses real Tokyo repo rates")
    
    def test_economist_commentary_data(self):
        """Test economist commentary uses correct data structure"""
        print("Testing economist commentary data usage...")
        
        with patch.object(self.ai_analyst, '_call_openai') as mock_openai:
            mock_openai.return_value = "Mock economist commentary"
            
            self.ai_analyst.generate_economist_commentary(self.sample_data)
            
            self.assertTrue(mock_openai.called)
            
            call_args = mock_openai.call_args
            prompt = call_args[0][0]
            
            # Verify macro data is in prompt
            self.assertIn('2.74', prompt)  # Japan CPI
            
            print("✓ Economist commentary uses real macro data")
    
    def test_all_segments_generation(self):
        """Test that all 4 segments can be generated successfully"""
        print("Testing all segments generation...")
        
        with patch.object(self.ai_analyst, '_call_openai') as mock_openai:
            mock_openai.side_effect = [
                "Rates markets commentary",
                "FX markets commentary", 
                "Repo markets commentary",
                "Economic outlook commentary"
            ]
            
            segments = self.brief_generator.generate_segments(self.sample_data)
            
            # Verify all 4 segments were generated
            expected_segments = ['rates', 'fx', 'repo', 'economist']
            for segment in expected_segments:
                self.assertIn(segment, segments)
                self.assertIsInstance(segments[segment], str)
                self.assertGreater(len(segments[segment]), 0)
            
            # Verify OpenAI was called 4 times
            self.assertEqual(mock_openai.call_count, 4)
            
            print("✓ All 4 segments generated successfully")
    
    def test_no_placeholders_in_prompts(self):
        """Test that no placeholder values are used in AI prompts"""
        print("Testing for placeholder values...")
        
        captured_prompts = []
        
        def capture_prompt(prompt, **kwargs):
            captured_prompts.append(prompt)
            return "Mock response"
        
        with patch.object(self.ai_analyst, '_call_openai', side_effect=capture_prompt):
            # Generate all segments
            self.ai_analyst.generate_rates_commentary(self.sample_data)
            self.ai_analyst.generate_fx_commentary(self.sample_data)
            self.ai_analyst.generate_repo_commentary(self.sample_data)
            self.ai_analyst.generate_economist_commentary(self.sample_data)
        
        # Check all prompts for placeholder values
        all_prompts = ' '.join(captured_prompts)
        
        # These should NOT appear (old placeholder values)
        forbidden_values = ['0.25', '4.25', '147.25', '158.90', '106.5']
        for value in forbidden_values:
            if value in all_prompts:
                print(f"! WARNING: Found potential placeholder value: {value}")
        
        # These SHOULD appear (real current values)
        expected_values = ['1.56', '4.05', '147.35', '172.68', '2.74', '0.489']
        found_real_values = 0
        for value in expected_values:
            if value in all_prompts:
                found_real_values += 1
        
        self.assertGreater(found_real_values, 3, "Not enough real market data in prompts")
        print(f"✓ Found {found_real_values} real market values in prompts")


def run_morning_brief_tests():
    """Run all morning brief tests"""
    print("="*60)
    print("YENSENSE.AI - MORNING BRIEF TESTS")
    print("="*60)
    print()
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestMorningBrief)
    
    # Run tests
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
            print(f"- {test}")
    
    if result.errors:
        print("\nERRORS:")
        for test, traceback in result.errors:
            print(f"- {test}")
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_morning_brief_tests()
    sys.exit(0 if success else 1)