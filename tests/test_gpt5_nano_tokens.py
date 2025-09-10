#!/usr/bin/env python3
"""
Test GPT-5-nano token requirements for AI analyst commentary
Systematically test different token limits and document results
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

import requests
import yaml
import json
from datetime import datetime

def load_config():
    """Load API configuration"""
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config.yaml')
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def test_token_limits():
    """Test different token limits with GPT-5-nano"""
    config = load_config()
    api_key = config['api_keys']['openai']
    
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    # Test actual AI analyst prompt (rates commentary)
    test_cases = [
        {
            'name': 'Rates commentary (actual prompt from AI analyst)',
            'prompt': '''Generate podcast commentary about Japan rates markets.

Current levels:
- JGB 10Y: 1.56%
- US 10Y: 4.05%
- Rate differential: 249bp

Recent headlines:
No major rate-related headlines

Cover what matters:
1. Any notable JGB yield moves overnight/yesterday
2. US Treasury spillover effects (rates often move together)
3. BOJ policy implications or operations
4. What this means for USD/JPY carry dynamics

If rates were quiet, just say "JGB yields were little changed overnight, trading around 1.56%."

Be specific about moves, levels, and catalysts. No fluff.''',
            'expected_min_tokens': 100
        }
    ]
    
    # Token limits to test (focused range)
    token_limits = [800, 1200, 1500]
    
    results = {}
    
    print(f"=== GPT-5-nano Token Requirements Test ===")
    print(f"Date: {datetime.now().isoformat()}")
    print(f"Model: gpt-5-nano")
    print()
    
    for test_case in test_cases:
        print(f"Testing: {test_case['name']}")
        print(f"Expected min output: {test_case['expected_min_tokens']} tokens")
        print("-" * 60)
        
        results[test_case['name']] = {}
        
        for max_tokens in token_limits:
            print(f"  Testing {max_tokens} tokens... ", end="")
            
            data = {
                'model': 'gpt-5-nano',
                'messages': [
                    {
                        'role': 'system',
                        'content': 'You are a Japan markets analyst. Be concise and specific.'
                    },
                    {
                        'role': 'user',
                        'content': test_case['prompt']
                    }
                ],
                'max_completion_tokens': max_tokens
            }
            
            try:
                response = requests.post(
                    'https://api.openai.com/v1/chat/completions',
                    headers=headers,
                    json=data,
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    content = result['choices'][0]['message']['content']
                    usage = result.get('usage', {})
                    completion_details = usage.get('completion_tokens_details', {})
                    
                    reasoning_tokens = completion_details.get('reasoning_tokens', 0)
                    finish_reason = result['choices'][0].get('finish_reason')
                    
                    success = len(content.strip()) >= test_case['expected_min_tokens']
                    
                    results[test_case['name']][max_tokens] = {
                        'success': success,
                        'content_length': len(content),
                        'reasoning_tokens': reasoning_tokens,
                        'total_completion_tokens': usage.get('completion_tokens', 0),
                        'finish_reason': finish_reason,
                        'content_preview': content[:100] if content else "(empty)"
                    }
                    
                    status = "✓" if success else "✗"
                    print(f"{status} {len(content)} chars, {reasoning_tokens} reasoning tokens, {finish_reason}")
                    
                    # Stop testing higher limits once we get success
                    if success:
                        print(f"  → SUCCESS at {max_tokens} tokens")
                        break
                        
                else:
                    print(f"✗ API Error: {response.status_code}")
                    results[test_case['name']][max_tokens] = {'error': f"API Error {response.status_code}"}
                    
            except Exception as e:
                print(f"✗ Exception: {e}")
                results[test_case['name']][max_tokens] = {'error': str(e)}
        
        print()
    
    # Summary
    print("=== RESULTS SUMMARY ===")
    for test_name, test_results in results.items():
        print(f"{test_name}:")
        successful_limit = None
        for limit, result in test_results.items():
            if isinstance(result, dict) and result.get('success'):
                successful_limit = limit
                break
        
        if successful_limit:
            print(f"  ✓ Works at: {successful_limit} tokens")
            details = test_results[successful_limit]
            print(f"    Content: {details['content_length']} chars")
            print(f"    Reasoning: {details['reasoning_tokens']} tokens")
            print(f"    Preview: {details['content_preview']}")
        else:
            print(f"  ✗ Failed at all tested token limits")
        print()
    
    # Recommendations
    print("=== RECOMMENDATIONS ===")
    max_successful_limit = 0
    for test_results in results.values():
        for limit, result in test_results.items():
            if isinstance(result, dict) and result.get('success'):
                max_successful_limit = max(max_successful_limit, limit)
                break
    
    if max_successful_limit > 0:
        recommended = max_successful_limit + 200  # Add buffer
        print(f"Recommended token limit: {recommended}")
        print(f"Reasoning: Highest successful limit was {max_successful_limit}, adding 200 token buffer")
    else:
        print("FAILED: No token limit worked for all test cases")
        print("Consider switching models or simplifying prompts")
    
    return results

if __name__ == "__main__":
    results = test_token_limits()