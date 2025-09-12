#!/usr/bin/env python3
"""
Test e-stat API data retrieval with specific dataset IDs
"""

import requests
import json
import yaml
import sys
import os

def test_estat_data_access():
    """Test accessing actual data from e-stat API"""
    
    # Load config
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    app_id = config['api_keys']['estat']
    base_url = "http://api.e-stat.go.jp/rest/3.0/app/json"
    
    print(f"Testing e-stat data access with appId: {app_id[:10]}...")
    
    # Test 1: Get CPI data (2020-Base Consumer Price Index)
    print("\n1. Testing CPI data access...")
    
    dataset_id = "0003427113"  # 2020-Base Consumer Price Index
    
    params = {
        'appId': app_id,
        'statsDataId': dataset_id,
        'limit': 10
    }
    
    try:
        response = requests.get(f"{base_url}/getStatsData", params=params)
        response.raise_for_status()
        
        data = response.json()
        print(f"CPI Data Status: {response.status_code}")
        print(f"Response keys: {list(data.keys())}")
        
        if 'GET_STATS_DATA' in data:
            stats_data = data['GET_STATS_DATA']
            if 'STATISTICAL_DATA' in stats_data:
                stat_info = stats_data['STATISTICAL_DATA']
                table_inf = stat_info.get('TABLE_INF', {})
                
                print(f"Statistics Name: {table_inf.get('STATISTICS_NAME', 'N/A')}")
                print(f"Title: {table_inf.get('TITLE', 'N/A')}")
                print(f"Last Updated: {table_inf.get('UPDATED_DATE', 'N/A')}")
                
                # Check if we have actual data
                if 'DATA_INF' in stat_info:
                    data_inf = stat_info['DATA_INF']
                    if 'VALUE' in data_inf:
                        values = data_inf['VALUE']
                        if isinstance(values, list):
                            print(f"Found {len(values)} data points")
                            # Show first few values
                            for i, value in enumerate(values[:5]):
                                print(f"  Value {i+1}: {value}")
                        else:
                            print(f"Single value: {values}")
                    else:
                        print("No VALUE data found")
                        print(f"DATA_INF keys: {list(data_inf.keys())}")
                else:
                    print("No DATA_INF found")
            else:
                print("No STATISTICAL_DATA found")
        else:
            print("No GET_STATS_DATA found")
            
        # Show error if any
        if 'GET_STATS_DATA' in data and 'RESULT' in data['GET_STATS_DATA']:
            result = data['GET_STATS_DATA']['RESULT']
            print(f"Status Code: {result.get('STATUS', 'N/A')}")
            print(f"Error Message: {result.get('ERROR_MSG', 'N/A')}")
        
    except Exception as e:
        print(f"Error accessing CPI data: {e}")
    
    # Test 2: Get Machinery Orders data
    print("\n2. Testing Machinery Orders data access...")
    
    machinery_dataset_id = "0003355266"  # Historical Machinery Orders data
    
    params = {
        'appId': app_id,
        'statsDataId': machinery_dataset_id,
        'limit': 5
    }
    
    try:
        response = requests.get(f"{base_url}/getStatsData", params=params)
        response.raise_for_status()
        
        data = response.json()
        print(f"Machinery Orders Status: {response.status_code}")
        
        if 'GET_STATS_DATA' in data:
            result = data['GET_STATS_DATA'].get('RESULT', {})
            print(f"API Status: {result.get('STATUS', 'N/A')}")
            print(f"Message: {result.get('ERROR_MSG', 'N/A')}")
            
            if 'STATISTICAL_DATA' in data['GET_STATS_DATA']:
                stat_data = data['GET_STATS_DATA']['STATISTICAL_DATA']
                table_inf = stat_data.get('TABLE_INF', {})
                print(f"Dataset Title: {table_inf.get('TITLE', 'N/A')}")
                print(f"Updated: {table_inf.get('UPDATED_DATE', 'N/A')}")
        
    except Exception as e:
        print(f"Error accessing Machinery Orders data: {e}")

if __name__ == "__main__":
    test_estat_data_access()