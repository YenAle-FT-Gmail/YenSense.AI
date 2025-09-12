#!/usr/bin/env python3
"""
Test e-stat API integration to find dataset IDs
"""

import requests
import json
import yaml
import sys
import os

def test_estat_api():
    """Test basic e-stat API connectivity and find dataset IDs"""
    
    # Load config
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    app_id = config['api_keys']['estat']
    base_url = "http://api.e-stat.go.jp/rest/3.0/app/json"
    
    print(f"Testing e-stat API with appId: {app_id[:10]}...")
    
    # Test 1: Get statistical table list to find dataset IDs
    print("\n1. Searching for CPI datasets...")
    
    params = {
        'appId': app_id,
        'lang': 'E',  # English
        'searchWord': 'Consumer Price Index Tokyo',
        'limit': 10
    }
    
    try:
        response = requests.get(f"{base_url}/getStatsList", params=params)
        response.raise_for_status()
        
        data = response.json()
        print(f"Status: {response.status_code}")
        print(f"Response keys: {list(data.keys())}")
        
        if 'GET_STATS_LIST' in data:
            stats_list = data['GET_STATS_LIST']
            if 'DATALIST_INF' in stats_list:
                datasets = stats_list['DATALIST_INF']['TABLE_INF']
                if isinstance(datasets, list):
                    print(f"Found {len(datasets)} CPI datasets:")
                    for i, dataset in enumerate(datasets[:5]):  # Show first 5
                        print(f"  {i+1}. {dataset.get('@id', 'N/A')} - {dataset.get('TITLE', 'No title')}")
                        print(f"     Stats: {dataset.get('STATISTICS_NAME', 'N/A')}")
                        print(f"     Updated: {dataset.get('UPDATED_DATE', 'N/A')}")
                        print()
                else:
                    print(f"Single dataset found: {datasets.get('@id', 'N/A')}")
            
        print(f"Full response: {json.dumps(data, indent=2, ensure_ascii=False)}")
        
    except Exception as e:
        print(f"Error testing CPI search: {e}")
    
    # Test 2: Search for Tankan or business survey data
    print("\n2. Searching for business survey datasets...")
    
    params = {
        'appId': app_id,
        'lang': 'E',
        'searchWord': 'business survey',
        'limit': 10
    }
    
    try:
        response = requests.get(f"{base_url}/getStatsList", params=params)
        response.raise_for_status()
        
        data = response.json()
        if 'GET_STATS_LIST' in data and 'DATALIST_INF' in data['GET_STATS_LIST']:
            datasets = data['GET_STATS_LIST']['DATALIST_INF']['TABLE_INF']
            if isinstance(datasets, list):
                print(f"Found {len(datasets)} business survey datasets:")
                for i, dataset in enumerate(datasets[:3]):
                    print(f"  {i+1}. {dataset.get('@id', 'N/A')} - {dataset.get('TITLE', 'No title')}")
            else:
                print(f"Single dataset: {datasets.get('@id', 'N/A')} - {datasets.get('TITLE', 'No title')}")
        else:
            print("No business survey datasets found")
            
    except Exception as e:
        print(f"Error testing business survey search: {e}")
    
    # Test 3: Search for machinery orders
    print("\n3. Searching for machinery orders datasets...")
    
    params = {
        'appId': app_id,
        'lang': 'E',
        'searchWord': 'machinery orders',
        'limit': 10
    }
    
    try:
        response = requests.get(f"{base_url}/getStatsList", params=params)
        response.raise_for_status()
        
        data = response.json()
        if 'GET_STATS_LIST' in data and 'DATALIST_INF' in data['GET_STATS_LIST']:
            datasets = data['GET_STATS_LIST']['DATALIST_INF']['TABLE_INF']
            if isinstance(datasets, list):
                print(f"Found {len(datasets)} machinery orders datasets:")
                for i, dataset in enumerate(datasets[:3]):
                    print(f"  {i+1}. {dataset.get('@id', 'N/A')} - {dataset.get('TITLE', 'No title')}")
            else:
                print(f"Single dataset: {datasets.get('@id', 'N/A')} - {datasets.get('TITLE', 'No title')}")
        else:
            print("No machinery orders datasets found")
            
    except Exception as e:
        print(f"Error testing machinery orders search: {e}")

if __name__ == "__main__":
    test_estat_api()