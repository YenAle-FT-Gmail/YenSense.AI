"""
Stage 1: Data Collection
Fetches raw market data using existing data fetcher
"""

from typing import Dict, Any
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from .base_stage import BaseStage
from ..context import PipelineContext
from data_fetcher import DataFetcher


class DataCollectionStage(BaseStage):
    """Collects raw market data from various sources"""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize with data fetcher"""
        super().__init__(config_path)
        self.data_fetcher = DataFetcher(config_path)
    
    def execute(self, context: PipelineContext) -> PipelineContext:
        """
        Collect all raw data from APIs and web sources
        
        Returns context with:
        - raw_data: Dictionary containing fx_rates, macro_data, news, etc.
        """
        self.log_stage_start()
        
        try:
            # Fetch all data using existing fetcher's fetch_all_data method
            self.logger.info("Fetching all market data...")
            all_data = self.data_fetcher.fetch_all_data()
            
            # Extract individual components
            fx_rates = all_data.get('fx_rates', {})
            macro_data = all_data.get('macro_data', {})
            boj_news = all_data.get('boj_news', [])
            reuters_news = all_data.get('reuters_news', [])
            nikkei_news = all_data.get('nikkei_news', [])
            sentiment_score = all_data.get('sentiment_score', 50)
            
            # Compile all data
            context.raw_data = {
                'fx_rates': fx_rates,
                'macro_data': macro_data,
                'boj_news': boj_news,
                'reuters_news': reuters_news,
                'nikkei_news': nikkei_news,
                'sentiment_score': sentiment_score
            }
            
            # Store stage output
            context.add_stage_output('data_collection', {
                'sources_fetched': ['fx_rates', 'macro_data', 'boj_news', 'reuters_news', 'nikkei_news'],
                'data_points': self._count_data_points(context.raw_data)
            })
            
            self.logger.info(f"Collected data from {len(context.raw_data)} sources")
            
        except Exception as e:
            return self.handle_error(context, e)
        
        self.log_stage_end()
        return context
    
    def _count_data_points(self, data: Dict[str, Any]) -> int:
        """Count total data points collected"""
        count = 0
        for key, value in data.items():
            if isinstance(value, dict):
                count += len(value)
            elif isinstance(value, list):
                count += len(value)
            else:
                count += 1
        return count