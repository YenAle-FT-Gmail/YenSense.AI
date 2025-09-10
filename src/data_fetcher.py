#!/usr/bin/env python3
"""
Data fetching module for YenSense AI
Handles API calls, web scraping, and data caching
"""

import json
import logging
import os
import pickle
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import xml.etree.ElementTree as ET

import pandas as pd
import requests
import yaml
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class DataFetcher:
    """Handles all data fetching operations with caching and error handling"""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize data fetcher with configuration"""
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.session = self._create_session()
        self.logger = logging.getLogger(__name__)
        
        # Set up cache directories
        self.cache_dirs = {
            'fx': 'data/input/fx',
            'macro': 'data/input/macro',
            'economist': 'data/input/economist',
            'news': 'data/input/news',
            'repo': 'data/input/repo'
        }
        for dir_path in self.cache_dirs.values():
            os.makedirs(dir_path, exist_ok=True)
    
    def _create_session(self) -> requests.Session:
        """Create requests session with retry logic"""
        session = requests.Session()
        retry = Retry(
            total=self.config['data']['retry_attempts'],
            backoff_factor=1,
            status_forcelist=[500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        session.headers.update({
            'User-Agent': self.config['scraping']['user_agent']
        })
        return session
    
    def _get_cache_path(self, cache_type: str, filename: str) -> str:
        """Get full cache file path"""
        return os.path.join(self.cache_dirs.get(cache_type, 'data/input/macro'), filename)
    
    def _is_cache_valid(self, filepath: str, hours: Optional[int] = None) -> bool:
        """Check if cached data is still valid"""
        if not os.path.exists(filepath):
            return False
        
        hours = hours or self.config['data']['cache_expiry_hours']
        file_time = datetime.fromtimestamp(os.path.getmtime(filepath))
        return datetime.now() - file_time < timedelta(hours=hours)
    
    def _save_cache(self, data: Any, cache_type: str, filename: str):
        """Save data to cache"""
        filepath = self._get_cache_path(cache_type, filename)
        
        if filename.endswith('.json'):
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        elif filename.endswith('.csv'):
            if isinstance(data, pd.DataFrame):
                data.to_csv(filepath, index=False)
            else:
                pd.DataFrame(data).to_csv(filepath, index=False)
        else:
            with open(filepath, 'wb') as f:
                pickle.dump(data, f)
        
        self.logger.info(f"Cached data to {filepath}")
    
    def _load_cache(self, cache_type: str, filename: str) -> Optional[Any]:
        """Load data from cache if valid"""
        filepath = self._get_cache_path(cache_type, filename)
        
        if not self._is_cache_valid(filepath):
            return None
        
        try:
            if filename.endswith('.json'):
                with open(filepath, 'r') as f:
                    return json.load(f)
            elif filename.endswith('.csv'):
                return pd.read_csv(filepath)
            else:
                with open(filepath, 'rb') as f:
                    return pickle.load(f)
        except Exception as e:
            self.logger.error(f"Error loading cache {filepath}: {e}")
            return None
    
    def fetch_fx_rates(self) -> Dict[str, float]:
        """Fetch FX rates from Alpha Vantage"""
        rates = {}
        cache_file = 'fx_rates.json'
        
        # Try cache first
        cached = self._load_cache('fx', cache_file)
        if cached:
            self.logger.info("Using cached FX rates")
            return cached
        
        api_key = self.config['api_keys']['alpha_vantage']
        if api_key == "YOUR_ALPHA_VANTAGE_API_KEY":
            # Fallback data for demo
            self.logger.warning("Using demo FX rates - please configure Alpha Vantage API key")
            rates = {
                'USD/JPY': 147.25,
                'EUR/JPY': 158.90,
                'timestamp': datetime.now().isoformat()
            }
            self._save_cache(rates, 'fx', cache_file)
            return rates
        
        for pair in self.config['data']['fx_pairs']:
            from_currency, to_currency = pair.split('/')
            url = f"https://www.alphavantage.co/query"
            params = {
                'function': 'CURRENCY_EXCHANGE_RATE',
                'from_currency': from_currency,
                'to_currency': to_currency,
                'apikey': api_key
            }
            
            try:
                response = self.session.get(url, params=params, timeout=10)
                response.raise_for_status()
                data = response.json()
                
                if 'Realtime Currency Exchange Rate' in data:
                    rate = float(data['Realtime Currency Exchange Rate']['5. Exchange Rate'])
                    rates[pair] = rate
                    self.logger.info(f"Fetched {pair}: {rate}")
                else:
                    self.logger.error(f"Invalid response for {pair}")
                    # Use fallback
                    rates[pair] = 147.25 if pair == 'USD/JPY' else 158.90
                    
                time.sleep(1)  # Rate limiting
                
            except Exception as e:
                self.logger.error(f"Error fetching {pair}: {e}")
                # Use fallback
                rates[pair] = 147.25 if pair == 'USD/JPY' else 158.90
        
        rates['timestamp'] = datetime.now().isoformat()
        self._save_cache(rates, 'fx', cache_file)
        return rates
    
    def fetch_fred_data(self) -> Dict[str, Any]:
        """Fetch macro data from FRED"""
        cache_file = 'fred_data.json'
        
        # Try cache first
        cached = self._load_cache('macro', cache_file)
        if cached:
            self.logger.info("Using cached FRED data")
            return cached
        
        api_key = self.config['api_keys']['fred']
        if api_key == "YOUR_FRED_API_KEY":
            # Fallback data for demo
            self.logger.warning("Using demo FRED data - please configure FRED API key")
            data = {
                'japan_cpi': 106.5,
                'japan_gdp': 4231.14,
                'us_gdp': 27000.0,
                'timestamp': datetime.now().isoformat()
            }
            self._save_cache(data, 'macro', cache_file)
            return data
        
        series_ids = {
            'japan_cpi': 'JPNCPIALLMINMEI',  # Japan CPI
            'japan_gdp': 'JPNRGDPEXP',  # Japan GDP
            'us_gdp': 'GDP'  # US GDP for comparison
        }
        
        data = {}
        base_url = "https://api.stlouisfed.org/fred/series/observations"
        
        for name, series_id in series_ids.items():
            params = {
                'series_id': series_id,
                'api_key': api_key,
                'file_type': 'json',
                'limit': 1,
                'sort_order': 'desc'
            }
            
            try:
                response = self.session.get(base_url, params=params, timeout=10)
                response.raise_for_status()
                result = response.json()
                
                if 'observations' in result and result['observations']:
                    data[name] = float(result['observations'][0]['value'])
                    self.logger.info(f"Fetched {name}: {data[name]}")
                else:
                    # Use fallback
                    data[name] = 106.5 if 'cpi' in name else 4231.14
                    
            except Exception as e:
                self.logger.error(f"Error fetching {name}: {e}")
                # Use fallback
                data[name] = 106.5 if 'cpi' in name else 4231.14
        
        data['timestamp'] = datetime.now().isoformat()
        self._save_cache(data, 'macro', cache_file)
        return data
    
    def fetch_boj_news(self) -> List[Dict[str, str]]:
        """Scrape BOJ website for policy news"""
        cache_file = 'boj_news.json'
        
        # Try cache first
        cached = self._load_cache('macro', cache_file)
        if cached:
            self.logger.info("Using cached BOJ news")
            return cached
        
        news = []
        url = "https://www.boj.or.jp/en/index.htm"
        
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Look for news items - BOJ structure may vary
            news_items = soup.find_all('div', class_='news-item', limit=5)
            if not news_items:
                # Try alternative selectors
                news_items = soup.find_all(['article', 'li'], limit=5)
            
            for item in news_items[:3]:  # Get top 3 items
                title_elem = item.find(['h2', 'h3', 'a'])
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    link = item.find('a')
                    href = link.get('href', '') if link else ''
                    if href and not href.startswith('http'):
                        href = f"https://www.boj.or.jp{href}"
                    
                    news.append({
                        'title': title[:200],  # Limit title length
                        'link': href,
                        'source': 'Bank of Japan'
                    })
            
            self.logger.info(f"Scraped {len(news)} BOJ news items")
            
        except Exception as e:
            self.logger.error(f"Error scraping BOJ: {e}")
            # Use fallback news
            news = [{
                'title': 'BOJ Maintains Current Monetary Policy Stance',
                'link': 'https://www.boj.or.jp/en/',
                'source': 'Bank of Japan'
            }]
        
        if not news:
            # Fallback if no news found
            news = [{
                'title': 'BOJ Policy Update - Check Official Website',
                'link': 'https://www.boj.or.jp/en/',
                'source': 'Bank of Japan'
            }]
        
        self._save_cache(news, 'macro', cache_file)
        return news
    
    def fetch_reuters_rss(self) -> List[Dict[str, str]]:
        """Fetch Reuters Japan news via RSS"""
        cache_file = 'reuters_news.json'
        
        # Try cache first
        cached = self._load_cache('news', cache_file)
        if cached:
            self.logger.info("Using cached Reuters news")
            return cached
        
        news = []
        # Reuters RSS feeds
        rss_urls = [
            "https://feeds.reuters.com/reuters/JPMarketNews",
            "https://feeds.reuters.com/reuters/JPBusinessNews"
        ]
        
        for rss_url in rss_urls:
            try:
                response = self.session.get(rss_url, timeout=10)
                response.raise_for_status()
                
                root = ET.fromstring(response.content)
                items = root.findall('.//item')[:3]  # Get top 3 items per feed
                
                for item in items:
                    title = item.find('title')
                    link = item.find('link')
                    
                    if title is not None and link is not None:
                        news.append({
                            'title': title.text[:200],
                            'link': link.text,
                            'source': 'Reuters'
                        })
                
            except Exception as e:
                self.logger.error(f"Error fetching Reuters RSS: {e}")
        
        if not news:
            # Fallback news
            news = [{
                'title': 'Japan Markets Update - Check Reuters for Latest',
                'link': 'https://www.reuters.com/markets/asia/',
                'source': 'Reuters'
            }]
        
        self.logger.info(f"Fetched {len(news)} Reuters news items")
        self._save_cache(news, 'news', cache_file)
        return news
    
    def fetch_nikkei_news(self) -> List[Dict[str, str]]:
        """Scrape Nikkei Asia for Japan economy news"""
        cache_file = 'nikkei_news.json'
        
        # Try cache first
        cached = self._load_cache('macro', cache_file)
        if cached:
            self.logger.info("Using cached Nikkei news")
            return cached
        
        news = []
        url = "https://asia.nikkei.com/Economy"
        
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Look for article elements
            articles = soup.find_all('article', limit=5)
            if not articles:
                articles = soup.find_all('div', class_='story', limit=5)
            
            for article in articles[:3]:
                title_elem = article.find(['h2', 'h3', 'a'])
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    link = article.find('a')
                    href = link.get('href', '') if link else ''
                    if href and not href.startswith('http'):
                        href = f"https://asia.nikkei.com{href}"
                    
                    news.append({
                        'title': title[:200],
                        'link': href,
                        'source': 'Nikkei Asia'
                    })
            
            self.logger.info(f"Scraped {len(news)} Nikkei news items")
            
        except Exception as e:
            self.logger.error(f"Error scraping Nikkei: {e}")
            # Fallback
            news = [{
                'title': 'Japan Economy Update - Visit Nikkei Asia',
                'link': 'https://asia.nikkei.com/Economy',
                'source': 'Nikkei Asia'
            }]
        
        if not news:
            news = [{
                'title': 'Latest Japan Economic News',
                'link': 'https://asia.nikkei.com/Economy',
                'source': 'Nikkei Asia'
            }]
        
        self._save_cache(news, 'macro', cache_file)
        return news
    
    def calculate_sentiment_score(self, fx_data: Dict, macro_data: Dict) -> int:
        """Calculate yen sentiment score (0-100)"""
        score = 50  # Neutral baseline
        
        try:
            # FX momentum (compare to typical ranges)
            usd_jpy = fx_data.get('USD/JPY', 147.0)
            if usd_jpy < 145:
                score += 10  # Yen strengthening
            elif usd_jpy > 150:
                score -= 10  # Yen weakening
            
            # CPI factor
            cpi = macro_data.get('japan_cpi', 106)
            if cpi > 106:
                score += 5  # Inflation pressure
            elif cpi < 105:
                score -= 5  # Deflation concern
            
            # Normalize to 0-100
            score = max(0, min(100, score))
            
        except Exception as e:
            self.logger.error(f"Error calculating sentiment: {e}")
            score = 50
        
        return score
    
    def fetch_all_data(self) -> Dict[str, Any]:
        """Fetch all required data with error handling"""
        self.logger.info("Starting comprehensive data fetch")
        
        all_data = {
            'fx_rates': {},
            'macro_data': {},
            'boj_news': [],
            'reuters_news': [],
            'nikkei_news': [],
            'sentiment_score': 50,
            'timestamp': datetime.now().isoformat()
        }
        
        # Fetch each data source with error handling
        try:
            all_data['fx_rates'] = self.fetch_fx_rates()
        except Exception as e:
            self.logger.error(f"Failed to fetch FX rates: {e}")
            all_data['fx_rates'] = {'USD/JPY': 147.25, 'EUR/JPY': 158.90}
        
        try:
            all_data['macro_data'] = self.fetch_fred_data()
        except Exception as e:
            self.logger.error(f"Failed to fetch FRED data: {e}")
            all_data['macro_data'] = {'japan_cpi': 106.5, 'japan_gdp': 4231.14}
        
        try:
            all_data['boj_news'] = self.fetch_boj_news()
        except Exception as e:
            self.logger.error(f"Failed to fetch BOJ news: {e}")
        
        try:
            all_data['reuters_news'] = self.fetch_reuters_rss()
        except Exception as e:
            self.logger.error(f"Failed to fetch Reuters news: {e}")
        
        try:
            all_data['nikkei_news'] = self.fetch_nikkei_news()
        except Exception as e:
            self.logger.error(f"Failed to fetch Nikkei news: {e}")
        
        # Calculate sentiment
        all_data['sentiment_score'] = self.calculate_sentiment_score(
            all_data['fx_rates'], 
            all_data['macro_data']
        )
        
        self.logger.info("Data fetch complete")
        return all_data


if __name__ == "__main__":
    # Test the data fetcher
    logging.basicConfig(level=logging.INFO)
    fetcher = DataFetcher()
    data = fetcher.fetch_all_data()
    print(json.dumps(data, indent=2, default=str))