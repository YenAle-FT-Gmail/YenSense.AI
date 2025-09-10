"""
Stage 2: Initial Summary
AI generates factual summary of what happened in markets
"""

import json
from typing import Dict, Any
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from .base_stage import BaseStage
from ..context import PipelineContext
from ai_analyst import AIAnalyst


class InitialSummaryStage(BaseStage):
    """AI generates initial factual summary of market events"""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize with AI analyst"""
        super().__init__(config_path)
        self.ai_analyst = AIAnalyst(config_path)
    
    def execute(self, context: PipelineContext) -> PipelineContext:
        """
        Generate factual summary of market events
        
        Returns context with:
        - summary: Factual summary of what happened
        """
        self.log_stage_start()
        
        try:
            data = context.raw_data
            
            # Build comprehensive prompt for factual summary
            prompt = self._build_summary_prompt(data)
            
            # Get AI to generate factual summary
            summary = self.ai_analyst._call_openai(prompt, max_tokens=800)
            
            context.summary = summary
            
            # Store stage output
            context.add_stage_output('initial_summary', {
                'summary_length': len(summary),
                'key_metrics_covered': self._extract_key_metrics(data)
            })
            
            self.logger.info("Generated initial market summary")
            
        except Exception as e:
            return self.handle_error(context, e)
        
        self.log_stage_end()
        return context
    
    def _build_summary_prompt(self, data: Dict[str, Any]) -> str:
        """Build prompt for factual summary"""
        fx_rates = data.get('fx_rates', {})
        macro_data = data.get('macro_data', {})
        
        # Compile news headlines
        headlines = []
        for source in ['boj_news', 'reuters_news', 'nikkei_news']:
            if source in data and isinstance(data[source], list):
                for item in data[source][:3]:
                    if isinstance(item, dict):
                        headlines.append(f"- {item.get('title', '')} ({item.get('source', '')})")
        
        headlines_text = "\n".join(headlines) if headlines else "No major headlines"
        
        prompt = f"""You are a senior financial analyst. Generate a FACTUAL summary of what happened in Japan's markets and economy. 
        
DO NOT interpret or provide opinions. Only state facts about price movements, data releases, and news events.

Current Market Data:
- USD/JPY: {fx_rates.get('USD/JPY', 'N/A')}
- EUR/JPY: {fx_rates.get('EUR/JPY', 'N/A')}

Economic Indicators:
- Japan CPI: {macro_data.get('japan_cpi', 'N/A')}
- Japan GDP: ${macro_data.get('japan_gdp', 'N/A')} billion

Recent Headlines:
{headlines_text}

Provide a structured factual summary covering:
1. FX market movements (actual levels and changes)
2. Economic data releases (what was released, actual vs expected if available)
3. Central bank or policy news
4. Major market events or news

Be specific with numbers and facts. Do not speculate or interpret."""
        
        return prompt
    
    def _extract_key_metrics(self, data: Dict[str, Any]) -> list:
        """Extract list of key metrics covered"""
        metrics = []
        if 'fx_rates' in data and data['fx_rates']:
            metrics.extend(['USD/JPY', 'EUR/JPY'])
        if 'macro_data' in data and data['macro_data']:
            if 'japan_cpi' in data['macro_data']:
                metrics.append('CPI')
            if 'japan_gdp' in data['macro_data']:
                metrics.append('GDP')
        return metrics