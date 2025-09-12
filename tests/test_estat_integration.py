#!/usr/bin/env python3
"""
Test e-stat integration with DataFetcher
"""

import sys
import os
import logging

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.data_fetcher import DataFetcher

def test_estat_integration():
    """Test e-stat data fetching through DataFetcher"""
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    print("Testing e-stat integration...")
    
    # Initialize DataFetcher
    fetcher = DataFetcher('config.yaml')
    
    # Test 1: Direct e-stat method
    print("\n1. Testing direct e-stat method...")
    try:
        estat_data = fetcher.fetch_estat_data()
        print(f"E-stat data keys: {list(estat_data.keys())}")
        
        # Check Tokyo CPI
        if 'tokyo_cpi' in estat_data:
            cpi = estat_data['tokyo_cpi']
            print(f"Tokyo CPI: {cpi.get('latest_value', 'N/A')} ({cpi.get('latest_time', 'N/A')})")
            print(f"Values count: {len(cpi.get('values', []))}")
        
        # Check Machinery Orders
        if 'machinery_orders' in estat_data:
            machinery = estat_data['machinery_orders']
            print(f"Machinery Orders: {machinery.get('latest_value', 'N/A')} ({machinery.get('latest_time', 'N/A')})")
            print(f"Values count: {len(machinery.get('values', []))}")
            
    except Exception as e:
        print(f"Error in direct e-stat test: {e}")
    
    # Test 2: Morning brief integration
    print("\n2. Testing morning brief integration...")
    try:
        brief_data = fetcher.fetch_morning_brief_data()
        print(f"Morning brief data keys: {list(brief_data.keys())}")
        
        if 'estat' in brief_data:
            estat_data = brief_data['estat']
            print(f"E-stat in morning brief: {list(estat_data.keys())}")
            
            # Show what data is available for AI analysis
            if 'tokyo_cpi' in estat_data:
                cpi_latest = estat_data['tokyo_cpi'].get('latest_value', 'N/A')
                print(f"AI will have access to: Tokyo CPI = {cpi_latest}")
            
            if 'machinery_orders' in estat_data:
                machinery_latest = estat_data['machinery_orders'].get('latest_value', 'N/A')
                print(f"AI will have access to: Machinery Orders = {machinery_latest}")
        else:
            print("No e-stat data in morning brief")
    
    except Exception as e:
        print(f"Error in morning brief integration test: {e}")

if __name__ == "__main__":
    test_estat_integration()