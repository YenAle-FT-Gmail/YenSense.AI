#!/usr/bin/env python3
"""
Data fetching module for YenSense AI
Handles API calls, web scraping, and data caching with clear organization
"""

import json
import logging
import os
import pickle
import re
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
    """
    Handles all data fetching operations with caching and error handling
    
    Organized into sections:
    1. Core utilities (cache, session)
    2. FRED API methods
    3. Web scraping methods
    4. Data aggregation methods
    """
    
    # ========== CORE UTILITIES ========== #
    
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
        
        cache_hours = hours or self.config['data']['cache_expiry_hours']
        file_time = datetime.fromtimestamp(os.path.getmtime(filepath))
        return datetime.now() - file_time < timedelta(hours=cache_hours)
    
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
    
    # ========== FRED API DATA FETCHERS ========== #
    
    def fetch_fred_macro(self) -> Dict[str, Any]:
        """Fetch core macro indicators (CPI, GDP) from FRED"""
        cache_file = 'fred_macro.json'
        
        # Try cache first
        cached = self._load_cache('macro', cache_file)
        if cached:
            self.logger.info("Using cached FRED macro data")
            return cached
        
        api_key = self.config['api_keys']['fred']
        if api_key == "YOUR_FRED_API_KEY":
            self.logger.warning("Using demo macro data - please configure FRED API key")
            data = {
                'japan_cpi': 106.5,
                'japan_gdp': 4231.14,
                'us_gdp': 27000.0,
                'timestamp': datetime.now().isoformat()
            }
            self._save_cache(data, 'macro', cache_file)
            return data
        
        series_ids = {
            'japan_cpi': 'FPCPITOTLZGJPN',   # Japan Consumer Price Inflation (most recent)
            'japan_gdp': 'JPNRGDPEXP',       # Japan GDP
            'us_gdp': 'GDP'                  # US GDP for comparison
        }
        
        data = self._fetch_fred_series(series_ids, fallback_values={
            'japan_cpi': 106.5,
            'japan_gdp': 4231.14,
            'us_gdp': 27000.0
        })
        
        self._save_cache(data, 'macro', cache_file)
        return data
    
    def fetch_fred_yields(self) -> Dict[str, Any]:
        """Fetch UST yield curve and JGB 10Y from FRED"""
        cache_file = 'fred_yields.json'
        
        # Try cache first
        cached = self._load_cache('macro', cache_file)
        if cached:
            self.logger.info("Using cached FRED yields data")
            return cached
        
        api_key = self.config['api_keys']['fred']
        if api_key == "YOUR_FRED_API_KEY":
            self.logger.warning("Using demo yields data - please configure FRED API key")
            data = {
                'ust_3m': 5.25,
                'ust_6m': 5.15,
                'ust_1y': 4.85,
                'ust_2y': 4.60,
                'ust_5y': 4.40,
                'ust_10y': 4.25,
                'ust_30y': 4.40,
                'timestamp': datetime.now().isoformat()
            }
            self._save_cache(data, 'macro', cache_file)
            return data
        
        series_ids = {
            # Full UST curve (daily) - FRED is authoritative source for US rates
            'ust_1m': 'DGS1MO',
            'ust_3m': 'DGS3MO',
            'ust_6m': 'DGS6MO', 
            'ust_1y': 'DGS1',
            'ust_2y': 'DGS2',
            'ust_3y': 'DGS3',
            'ust_5y': 'DGS5',
            'ust_7y': 'DGS7',
            'ust_10y': 'DGS10',
            'ust_20y': 'DGS20',
            'ust_30y': 'DGS30'
            # JGB yields removed - JBOND is authoritative source for JGB rates
        }
        
        data = self._fetch_fred_series(series_ids, fallback_values={
            'ust_1m': 5.50,
            'ust_3m': 5.25,
            'ust_6m': 5.15,
            'ust_1y': 4.85,
            'ust_2y': 4.60,
            'ust_3y': 4.50,
            'ust_5y': 4.40,
            'ust_7y': 4.35,
            'ust_10y': 4.25,
            'ust_20y': 4.35,
            'ust_30y': 4.40
        })
        
        self._save_cache(data, 'macro', cache_file)
        return data
    
    def fetch_fred_fx(self) -> Dict[str, Any]:
        """Fetch FX rates and dollar index from FRED"""
        cache_file = 'fred_fx.json'
        
        # Try cache first
        cached = self._load_cache('fx', cache_file)
        if cached:
            self.logger.info("Using cached FRED FX data")
            return cached
        
        api_key = self.config['api_keys']['fred']
        if api_key == "YOUR_FRED_API_KEY":
            self.logger.warning("Using demo FX data - please configure FRED API key")
            data = {
                'usdjpy': 147.25,
                'usdeur': 0.9050,
                'eurjpy': 162.65,
                'dxy': 103.5,
                'timestamp': datetime.now().isoformat()
            }
            self._save_cache(data, 'fx', cache_file)
            return data
        
        series_ids = {
            'usdjpy': 'DEXJPUS',    # USD/JPY spot
            'usdeur': 'DEXUSEU',    # USD/EUR spot  
            'dxy': 'DTWEXBGS'       # Dollar index
        }
        
        data = self._fetch_fred_series(series_ids, fallback_values={
            'usdjpy': 147.25,
            'usdeur': 0.9050,
            'dxy': 103.5
        }, include_previous=True)
        
        # Calculate EUR/JPY from USD rates
        if 'usdjpy' in data and 'usdeur' in data:
            data['eurjpy'] = data['usdjpy'] / data['usdeur']
            if 'usdjpy_prev' in data and 'usdeur_prev' in data:
                eurjpy_prev = data['usdjpy_prev'] / data['usdeur_prev']
                data['eurjpy_prev'] = eurjpy_prev
                data['eurjpy_change'] = data['eurjpy'] - eurjpy_prev
        
        self._save_cache(data, 'fx', cache_file)
        return data
    
    def _fetch_fred_series(self, series_ids: Dict[str, str], fallback_values: Dict[str, float], 
                          include_previous: bool = False) -> Dict[str, Any]:
        """Helper method to fetch multiple FRED series"""
        data = {}
        api_key = self.config['api_keys']['fred']
        base_url = "https://api.stlouisfed.org/fred/series/observations"
        
        for name, series_id in series_ids.items():
            params = {
                'series_id': series_id,
                'api_key': api_key,
                'file_type': 'json',
                'limit': 2 if include_previous else 1,
                'sort_order': 'desc'
            }
            
            try:
                response = self.session.get(base_url, params=params, timeout=10)
                response.raise_for_status()
                result = response.json()
                
                if 'observations' in result and result['observations']:
                    obs = result['observations']
                    # Filter out null values
                    valid_obs = [o for o in obs if o['value'] != '.']
                    
                    if valid_obs:
                        current_val = float(valid_obs[0]['value'])
                        data[name] = current_val
                        
                        # Add previous value for change calculation
                        if include_previous and len(valid_obs) > 1:
                            prev_val = float(valid_obs[1]['value'])
                            data[f"{name}_prev"] = prev_val
                            data[f"{name}_change"] = current_val - prev_val
                        
                        self.logger.info(f"Fetched {name}: {current_val}")
                    else:
                        data[name] = fallback_values.get(name, 100.0)
                        self.logger.warning(f"No valid data for {name}, using fallback")
                else:
                    data[name] = fallback_values.get(name, 100.0)
                    self.logger.warning(f"No observations for {name}, using fallback")
                    
            except Exception as e:
                self.logger.error(f"Error fetching {name}: {e}")
                data[name] = fallback_values.get(name, 100.0)
            
            # Rate limiting
            time.sleep(0.1)
        
        data['timestamp'] = datetime.now().isoformat()
        return data
    
    # ========== JAPANESE MARKET DATA SCRAPERS ========== #
    
    def fetch_jgb_curve(self) -> Dict[str, Any]:
        """Scrape full JGB curve from JBOND historical rates"""
        cache_file = 'jgb_curve.json'
        
        # Try cache first
        cached = self._load_cache('macro', cache_file)
        if cached:
            self.logger.info("Using cached JGB curve data")
            return cached
        
        url = "https://www.bb.jbts.co.jp/ja/historical/main_rate.html"
        
        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find the main table with yield data
            tables = soup.find_all('table')
            jgb_data = {}
            
            # Look for the JGB data table
            for table in tables:
                rows = table.find_all('tr')
                
                # Table 2 has the data - it has 9 rows with dates
                if len(rows) >= 7:
                    # Process each row
                    for row in rows:
                        cells = row.find_all('td')
                        if len(cells) >= 7:
                            # Get all cell texts
                            cell_texts = [cell.get_text(strip=True) for cell in cells]
                            
                            # Check if first cell is a 2025 date
                            if cell_texts[0].startswith('2025/'):
                                date_str = cell_texts[0]
                                
                                # Extract all yields: 40Y, 30Y, 20Y, 10Y, 5Y, 2Y, TDB(1Y), TDB(6M), TDB(3M)
                                yields = cell_texts[1:10] if len(cell_texts) >= 10 else cell_texts[1:]
                                
                                # Parse main JGB yields
                                if len(yields) > 0 and yields[0]:  # 40Y
                                    try:
                                        jgb_data['jgb_40y'] = float(yields[0])
                                    except: pass
                                if len(yields) > 1 and yields[1]:  # 30Y
                                    try:
                                        jgb_data['jgb_30y'] = float(yields[1])
                                    except: pass
                                if len(yields) > 2 and yields[2]:  # 20Y
                                    try:
                                        jgb_data['jgb_20y'] = float(yields[2])
                                    except: pass
                                if len(yields) > 3 and yields[3]:  # 10Y
                                    try:
                                        jgb_data['jgb_10y'] = float(yields[3])
                                    except: pass
                                if len(yields) > 4 and yields[4]:  # 5Y
                                    try:
                                        jgb_data['jgb_5y'] = float(yields[4])
                                    except: pass
                                if len(yields) > 5 and yields[5]:  # 2Y
                                    try:
                                        jgb_data['jgb_2y'] = float(yields[5])
                                    except: pass
                                        
                                # Parse TDB yields if available
                                if len(yields) > 6 and yields[6]:  # TDB 1Y
                                    try:
                                        jgb_data['tdb_1y'] = float(yields[6])
                                    except: pass
                                if len(yields) > 7 and yields[7]:  # TDB 6M
                                    try:
                                        jgb_data['tdb_6m'] = float(yields[7])
                                    except: pass
                                if len(yields) > 8 and yields[8]:  # TDB 3M
                                    try:
                                        jgb_data['tdb_3m'] = float(yields[8])
                                    except: pass
                                
                                if jgb_data:
                                    jgb_data['data_date'] = date_str
                                    self.logger.info(f"Parsed JGB data from {date_str}")
                                    # Don't break - keep going to get the latest date
                
                # If we found data, stop
                if jgb_data:
                    break
            
            if not jgb_data:
                # Fallback data
                self.logger.warning("Could not parse JGB data, using fallback")
                jgb_data = {
                    'jgb_40y': 3.425,
                    'jgb_30y': 3.19,
                    'jgb_20y': 2.63,
                    'jgb_10y': 1.625,
                    'jgb_5y': 1.165,
                    'jgb_2y': 0.875,
                    'data_date': "2025/09/01",
                    'timestamp': datetime.now().isoformat()
                }
            else:
                jgb_data['timestamp'] = datetime.now().isoformat()
            self._save_cache(jgb_data, 'macro', cache_file)
            return jgb_data
            
        except Exception as e:
            self.logger.error(f"Error scraping JGB curve: {e}")
            # Return fallback data
            fallback_data = {
                'jgb_40y': 3.425,
                'jgb_30y': 3.19,
                'jgb_20y': 2.63,
                'jgb_10y': 1.625,
                'jgb_5y': 1.165,
                'jgb_2y': 0.875,
                'data_date': "2025/09/01",
                'timestamp': datetime.now().isoformat()
            }
            self._save_cache(fallback_data, 'macro', cache_file)
            return fallback_data
    
    def fetch_repo_rates(self) -> Dict[str, Any]:
        """Scrape Tokyo repo rates from Tokyo Tanshi"""
        cache_file = 'repo_rates.json'
        
        # Try cache first
        cached = self._load_cache('repo', cache_file)
        if cached:
            self.logger.info("Using cached repo rates data")
            return cached
        
        url = "https://www.tokyotanshi.co.jp/market_report/daily_d.html"
        
        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            repo_data = {}
            
            # Parse repo rates from the well-structured HTML tables
            tables = soup.find_all('table')
            
            for table in tables:
                rows = table.find_all('tr')
                if len(rows) < 2:
                    continue
                
                # Look for table with Japanese tenor labels
                table_text = table.get_text()
                
                if '東京レポ・レート' in table_text:  # Look specifically for Tokyo Repo Rate table
                    for row in rows:
                        cells = row.find_all(['td', 'th'])
                        if len(cells) < 2:
                            continue
                        
                        cell_texts = [cell.get_text(strip=True) for cell in cells]
                        row_label = cell_texts[0] if cell_texts else ""
                        
                        # Look for overnight rates (翌日物)
                        if '翌日物' in row_label:
                            # Find numeric rate in this row
                            for cell_text in cell_texts[1:]:
                                if self._is_numeric_rate(cell_text):
                                    try:
                                        rate = float(cell_text)
                                        if 0.1 <= rate <= 2.0:
                                            repo_data['gc_on'] = rate
                                            self.logger.info(f"Found overnight repo rate: {rate}%")
                                            break
                                    except (ValueError, TypeError):
                                        continue
                        
                        # Look for 1 week rates (1週間物)
                        elif '1週間物' in row_label:
                            for cell_text in cell_texts[1:]:
                                if self._is_numeric_rate(cell_text):
                                    try:
                                        rate = float(cell_text)
                                        if 0.1 <= rate <= 2.0:
                                            repo_data['gc_1w'] = rate
                                            self.logger.info(f"Found 1W repo rate: {rate}%")
                                            break
                                    except (ValueError, TypeError):
                                        continue
                        
                        # Look for 1 month rates (1ヶ月物)
                        elif '1ヶ月物' in row_label:
                            for cell_text in cell_texts[1:]:
                                if self._is_numeric_rate(cell_text):
                                    try:
                                        rate = float(cell_text)
                                        if 0.1 <= rate <= 2.0:
                                            repo_data['gc_1m'] = rate
                                            self.logger.info(f"Found 1M repo rate: {rate}%")
                                            break
                                    except (ValueError, TypeError):
                                        continue
                    
                    # If we found some rates, we can break
                    if repo_data:
                        break
            
            # If no data found, use fallback based on user's data
            if not repo_data:
                self.logger.warning("Could not parse repo data, using fallback")
                repo_data = {
                    'gc_on': 0.45,
                    'gc_1w': 0.477,
                    'gc_1m': 0.525,
                    'timestamp': datetime.now().isoformat()
                }
            else:
                repo_data['timestamp'] = datetime.now().isoformat()
            
            # Add data freshness warning for scraped repo data
            if repo_data and not any(k.startswith('gc_') for k in repo_data.keys() if isinstance(repo_data.get(k), float) and repo_data[k] != 0.489):
                self.logger.warning("Repo data may be using fallback values - website may not have current data")
            elif repo_data:
                self.logger.info("Repo data scraped successfully from website")
                
            self._save_cache(repo_data, 'repo', cache_file)
            return repo_data
            
        except Exception as e:
            self.logger.error(f"Error scraping repo rates: {e}")
            # Return fallback data
            fallback_data = {
                'gc_on': 0.45,
                'gc_1w': 0.477,
                'gc_1m': 0.525,
                'timestamp': datetime.now().isoformat()
            }
            self._save_cache(fallback_data, 'repo', cache_file)
            return fallback_data
    
    def fetch_tona_rate(self) -> Dict[str, Any]:
        """Scrape TONA overnight rate from Tokyo Tanshi"""
        cache_file = 'tona_rate.json'
        
        # Try cache first
        cached = self._load_cache('repo', cache_file)
        if cached:
            self.logger.info("Using cached TONA rate data")
            return cached
        
        url = "https://www.tokyotanshi.co.jp/market_report/market_data/tona/mkinfo.html"
        
        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            tona_data = {}
            
            # Look for TONA rate data in text content
            page_text = soup.get_text()
            
            # Look for patterns like "加重平均値 0.477" (Weighted Average Value)
            import re
            patterns = [
                r'加重平均値\s*([0-9]+\.?[0-9]*)',  # Japanese: Weighted Average Value
                r'weighted average\s*([0-9]+\.?[0-9]*)',  # English
                r'TONA\s*([0-9]+\.?[0-9]*)',  # Direct TONA reference
                r'([0-9]+\.?[0-9]*)\s*%',  # Any percentage
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, page_text, re.IGNORECASE)
                for match in matches:
                    rate = self._parse_japanese_number(match)
                    if rate is not None and 0 <= rate < 10:
                        if 'tona' not in tona_data:
                            tona_data['tona'] = rate
                            self.logger.info(f"Found TONA rate: {rate}%")
                            break
                if 'tona' in tona_data:
                    break
            
            # Also try table-based parsing as fallback
            if not tona_data:
                tables = soup.find_all('table')
                for table in tables:
                    table_text = table.get_text()
                    if 'TONA' in table_text or '無担保コール' in table_text:
                        rows = table.find_all('tr')
                        for row in rows:
                            cells = [td.get_text(strip=True) for td in row.find_all(['td', 'th'])]
                            for cell_text in cells:
                                rate = self._parse_japanese_number(cell_text.replace('%', ''))
                                if rate is not None and 0 <= rate < 10:
                                    tona_data['tona'] = rate
                                    self.logger.info(f"Found TONA rate from table: {rate}%")
                                    break
                            if tona_data:
                                break
            
            # If no data found, use fallback
            if not tona_data:
                self.logger.warning("Could not parse TONA data, using fallback")
                tona_data = {
                    'tona': 0.477,
                    'tona_high': 0.480,
                    'tona_low': 0.471,
                    'timestamp': datetime.now().isoformat()
                }
            else:
                tona_data['timestamp'] = datetime.now().isoformat()
            self._save_cache(tona_data, 'repo', cache_file)
            return tona_data
            
        except Exception as e:
            self.logger.error(f"Error scraping TONA rate: {e}")
            # Return fallback data
            fallback_data = {
                'tona': 0.477,
                'tona_high': 0.480,
                'tona_low': 0.471,
                'timestamp': datetime.now().isoformat()
            }
            self._save_cache(fallback_data, 'repo', cache_file)
            return fallback_data
    
    # ========== NEWS SCRAPERS (EXISTING) ========== #
    
    def fetch_boj_news(self) -> List[Dict[str, str]]:
        """Scrape BOJ website for policy news"""
        cache_file = 'boj_news.json'
        
        # Try cache first
        cached = self._load_cache('news', cache_file)
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
                title_elem = item.find('h2') or item.find('h3') or item.find('a')
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
        
        self._save_cache(news, 'news', cache_file)
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
                        title_text = title.text or ""
                        link_text = link.text or ""
                        news.append({
                            'title': title_text[:200],
                            'link': link_text,
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
        cached = self._load_cache('news', cache_file)
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
                title_elem = article.find('h2') or article.find('h3') or article.find('a')
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
        
        self._save_cache(news, 'news', cache_file)
        return news
    
    # ========== ALPHA VANTAGE FALLBACK ========== #
    
    def fetch_fx_rates_alpha(self) -> Dict[str, float]:
        """Fallback FX from Alpha Vantage if FRED fails"""
        rates = {}
        cache_file = 'alpha_fx_rates.json'
        
        # Try cache first
        cached = self._load_cache('fx', cache_file)
        if cached:
            self.logger.info("Using cached Alpha Vantage FX rates")
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
    
    # ========== DATA AGGREGATION METHODS ========== #
    
    def fetch_morning_brief_data(self) -> Dict[str, Any]:
        """Fetch all data needed for morning brief"""
        self.logger.info("Fetching morning brief data")
        
        data: Dict[str, Any] = {
            'timestamp': datetime.now().isoformat()
        }
        
        # Fetch market data - use Alpha Vantage for FX
        try:
            data['fx'] = self.fetch_fx_rates_alpha()
        except Exception as e:
            self.logger.error(f"Failed to fetch Alpha Vantage FX data: {e}")
            data['fx'] = {'USD/JPY': 147.0, 'EUR/JPY': 163.0}  # Fallback
        
        try:
            yield_data = self.fetch_fred_yields()
            jgb_data = self.fetch_jgb_curve()
            # Merge yield curves
            data['yields'] = {**yield_data, **jgb_data}
        except Exception as e:
            self.logger.error(f"Failed to fetch yield data: {e}")
            data['yields'] = {'ust_10y': 4.25, 'jgb_10y': 0.25}
        
        try:
            repo_data = self.fetch_repo_rates()
            tona_data = self.fetch_tona_rate()
            data['repo'] = {**repo_data, **tona_data}
        except Exception as e:
            self.logger.error(f"Failed to fetch repo data: {e}")
            data['repo'] = {'gc_on': 0.489, 'tona': 0.477}
        
        # Fetch macro context
        try:
            data['macro'] = self.fetch_fred_macro()
        except Exception as e:
            self.logger.error(f"Failed to fetch macro data: {e}")
            data['macro'] = {'japan_cpi': 106.5, 'japan_gdp': 4231.14}
        
        # Fetch news (limit to recent)
        try:
            data['news'] = {
                'boj': self.fetch_boj_news()[:2],
                'reuters': self.fetch_reuters_rss()[:2], 
                'nikkei': self.fetch_nikkei_news()[:2]
            }
        except Exception as e:
            self.logger.error(f"Failed to fetch news: {e}")
            data['news'] = {'boj': [], 'reuters': [], 'nikkei': []}
        
        # Calculate sentiment
        try:
            data['sentiment_score'] = self.calculate_sentiment_score(
                data.get('fx', {}), 
                data.get('macro', {})
            )
        except Exception as e:
            self.logger.error(f"Failed to calculate sentiment: {e}")
            data['sentiment_score'] = 50
        
        self.logger.info("Morning brief data fetch complete")
        return data
    
    def fetch_weekly_report_data(self) -> Dict[str, Any]:
        """Fetch comprehensive data for weekly report"""
        self.logger.info("Fetching weekly report data")
        
        # Start with morning brief data and extend it
        data = self.fetch_morning_brief_data()
        
        # Add any weekly-specific data here
        # For now, weekly reports can use the same data structure
        
        self.logger.info("Weekly report data fetch complete")
        return data
    
    def fetch_all_data(self) -> Dict[str, Any]:
        """Legacy method for backward compatibility"""
        self.logger.info("Starting comprehensive data fetch (legacy format)")
        
        # Maintain old structure for backward compatibility
        all_data = {
            'fx_rates': {},
            'macro_data': {},
            'boj_news': [],
            'reuters_news': [],
            'nikkei_news': [],
            'sentiment_score': 50,
            'timestamp': datetime.now().isoformat()
        }
        
        # Get new structured data
        new_data = self.fetch_morning_brief_data()
        
        # Map to old structure
        if 'fx' in new_data:
            # Convert new FX structure to old format
            fx = new_data['fx']
            all_data['fx_rates'] = {
                'USD/JPY': fx.get('usdjpy', 147.25),
                'EUR/JPY': fx.get('eurjpy', 158.90),
                'timestamp': fx.get('timestamp', datetime.now().isoformat())
            }
        
        if 'macro' in new_data:
            all_data['macro_data'] = new_data['macro']
        
        if 'news' in new_data:
            all_data['boj_news'] = new_data['news'].get('boj', [])
            all_data['reuters_news'] = new_data['news'].get('reuters', [])
            all_data['nikkei_news'] = new_data['news'].get('nikkei', [])
        
        all_data['sentiment_score'] = new_data.get('sentiment_score', 50)
        
        self.logger.info("Legacy data fetch complete")
        return all_data
    
    # ========== HELPER METHODS ========== #
    
    def calculate_sentiment_score(self, fx_data: Any, macro_data: Any) -> int:
        """Calculate yen sentiment score (0-100)"""
        score = 50  # Neutral baseline
        
        try:
            # FX momentum (compare to typical ranges)
            usd_jpy = fx_data.get('usdjpy', fx_data.get('USD/JPY', 147.0))
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
    
    def _parse_japanese_number(self, text: str) -> Optional[float]:
        """Parse Japanese formatted numbers"""
        if not text:
            return None
        
        try:
            # Remove common Japanese characters and whitespace
            cleaned = text.strip().replace('％', '').replace('%', '')
            cleaned = cleaned.replace('△', '-').replace('▲', '-')
            cleaned = re.sub(r'[^\d\.\-\+]', '', cleaned)
            
            if not cleaned or cleaned in ['-', '+', '.']:
                return None
            
            return float(cleaned)
        
        except (ValueError, TypeError):
            return None
    
    def _is_numeric_rate(self, value: str) -> bool:
        """Check if a string value represents a numeric rate"""
        try:
            float(value.replace(',', '').replace('%', ''))
            return True
        except (ValueError, TypeError):
            return False
    
    def _map_jgb_column_to_key(self, header: str) -> Optional[str]:
        """Map JGB column headers to our standard keys"""
        header_map = {
            # Japanese headers (actual website)
            '40年債': 'jgb_40y',
            '30年債': 'jgb_30y',
            '20年債': 'jgb_20y', 
            '10年債': 'jgb_10y',
            '5年債': 'jgb_5y',
            '2年債': 'jgb_2y',
            '1年債': 'jgb_1y',
            # English fallbacks (if any)
            '40Y': 'jgb_40y',
            '30Y': 'jgb_30y', 
            '20Y': 'jgb_20y',
            '10Y': 'jgb_10y',
            '5Y': 'jgb_5y',
            '2Y': 'jgb_2y',
            'TDB(1Y)': 'jgb_1y',
            'TDB(6M)': 'jgb_6m',
            'TDB(3M)': 'jgb_3m'
        }
        return header_map.get(header)
    
    def _map_jgb_maturity(self, header: str) -> Optional[str]:
        """Map Japanese maturity terms to English keys"""
        maturity_map = {
            '3': 'jgb_3m',
            '6': 'jgb_6m', 
            '1年': 'jgb_1y',
            '2年': 'jgb_2y',
            '5年': 'jgb_5y',
            '10年': 'jgb_10y',
            '20年': 'jgb_20y',
            '30年': 'jgb_30y',
            '40年': 'jgb_40y'
        }
        
        for term, key in maturity_map.items():
            if term in header:
                return key
        
        return None
    
    def _extract_data_date(self, cells: List[str]) -> Optional[str]:
        """Extract data date from scraped cells"""
        import re
        for cell in cells:
            # Look for date patterns like 2025/09/01
            date_match = re.search(r'20\d{2}/\d{2}/\d{2}', cell)
            if date_match:
                return date_match.group(0)
        return None
    
    def _days_since_date(self, date_str: str) -> int:
        """Calculate days since a date string (YYYY/MM/DD format)"""
        try:
            from datetime import datetime
            date_obj = datetime.strptime(date_str, '%Y/%m/%d')
            today = datetime.now()
            return (today - date_obj).days
        except (ValueError, TypeError):
            return 0
    
    def _get_previous_business_day(self) -> datetime:
        """Get previous business day for change calculations"""
        today = datetime.now()
        if today.weekday() == 0:  # Monday
            return today - timedelta(days=3)  # Friday
        else:
            return today - timedelta(days=1)


if __name__ == "__main__":
    # Test the data fetcher
    logging.basicConfig(level=logging.INFO)
    fetcher = DataFetcher()
    
    # Test morning brief data
    print("Testing morning brief data fetch...")
    data = fetcher.fetch_morning_brief_data()
    print(json.dumps(data, indent=2, default=str))