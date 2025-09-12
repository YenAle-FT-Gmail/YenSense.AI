#!/usr/bin/env python3
"""
Debug machinery orders data structure
"""

import requests
import json
import yaml

def debug_machinery_orders():
    """Debug the machinery orders dataset structure"""
    
    # Load config
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    app_id = config['api_keys']['estat']
    base_url = "http://api.e-stat.go.jp/rest/3.0/app/json/getStatsData"
    
    dataset_id = "0003355266"  # Machinery Orders
    
    params = {
        'appId': app_id,
        'statsDataId': dataset_id,
        'limit': 5
    }
    
    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        
        data = response.json()
        print("Full Machinery Orders Response:")
        print(json.dumps(data, indent=2, ensure_ascii=False))
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug_machinery_orders()