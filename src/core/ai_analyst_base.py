#!/usr/bin/env python3
"""
Base AI Analyst class with shared OpenAI utilities
Provides common functionality for both brief and report analysts
"""

import logging
import os
from typing import Dict, Any

import requests
import yaml


class AIAnalystBase:
    """Base class for AI-powered market analysts"""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize AI analyst base with configuration"""
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.logger = logging.getLogger(__name__)
        
        # Check environment variable first, then config file
        self.api_key = os.getenv('OPENAI_API_KEY') or self.config['api_keys'].get('openai')
        
        if not self.api_key or self.api_key == "YOUR_OPENAI_API_KEY":
            self.logger.warning("OpenAI API key not configured - using fallback analysis")
            self.use_ai = False
        else:
            self.use_ai = True
    
    def _call_openai(self, prompt: str, max_completion_tokens: int = 1000, system_prompt: str = "") -> str:
        """Call OpenAI API for analysis"""
        if not self.use_ai:
            return self._fallback_analysis()
        
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        # Use custom system prompt or default
        if not system_prompt:
            system_prompt = '''You are a senior Japan macro and FX strategist at a major investment bank. 
            You provide professional, insightful market analysis with specific data interpretation, 
            historical context, and forward-looking views. Your analysis is sophisticated but 
            accessible to both institutional and retail clients.'''
        
        data = {
            'model': 'gpt-4o-mini',
            'messages': [
                {
                    'role': 'system',
                    'content': system_prompt
                },
                {
                    'role': 'user',
                    'content': prompt
                }
            ],
            'max_completion_tokens': max_completion_tokens
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
                
                self.logger.info(f"OpenAI API call successful, {len(content)} characters")
                return content.strip()
            else:
                self.logger.error(f"OpenAI API error: {response.status_code}, {response.text}")
                return self._fallback_analysis()
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"OpenAI API request failed: {e}")
            return self._fallback_analysis()
        except Exception as e:
            self.logger.error(f"OpenAI API unexpected error: {e}")
            return self._fallback_analysis()
    
    def _fallback_analysis(self) -> str:
        """Provide fallback analysis when AI is unavailable"""
        return ("Market conditions remain in focus as investors monitor central bank policy "
                "divergence between the Fed and BOJ. Current data suggests cautious positioning "
                "with attention to inflation trends and policy communications.")
    
    def _format_number(self, number: float, decimals: int = 2) -> str:
        """Format number for display"""
        if number is None:
            return "N/A"
        if number >= 1000000:
            return f"{number/1000000:.{decimals}f}M"
        elif number >= 1000:
            return f"{number:,.{decimals}f}"
        return f"{number:.{decimals}f}"
    
    def _extract_headlines(self, news_data: Dict[str, Any], limit: int = 5) -> list:
        """Extract news headlines from various sources"""
        headlines = []
        
        for source in ['boj_news', 'reuters_news', 'nikkei_news']:
            if source in news_data and isinstance(news_data[source], list):
                for item in news_data[source][:limit]:
                    if isinstance(item, dict) and 'title' in item:
                        headlines.append({
                            'title': item.get('title', ''),
                            'source': item.get('source', source.replace('_news', '').upper()),
                            'timestamp': item.get('timestamp', '')
                        })
        
        return headlines[:limit]