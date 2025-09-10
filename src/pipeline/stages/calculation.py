"""
Stage 6: Calculation
AI performs actual calculations and analysis
"""

from typing import Dict, Any
import sys
import os
import json
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from .base_stage import BaseStage
from ..context import PipelineContext
from core.ai_analyst import AIAnalyst


class CalculationStage(BaseStage):
    """AI performs calculations to answer the identified questions"""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize with AI analyst"""
        super().__init__(config_path)
        self.ai_analyst = AIAnalyst(config_path)
    
    def execute(self, context: PipelineContext) -> PipelineContext:
        """
        AI performs calculations based on the analysis plan
        
        Returns context with:
        - calculations: Results of all calculations performed
        """
        self.log_stage_start()
        
        try:
            # Perform calculations for each analysis in the plan
            calculations = self._perform_calculations(context)
            
            context.calculations = calculations
            
            # Store stage output
            context.add_stage_output('calculation', {
                'calculations_performed': len(calculations),
                'calculation_types': list(calculations.keys())
            })
            
            self.logger.info(f"Performed {len(calculations)} calculations")
            
        except Exception as e:
            return self.handle_error(context, e)
        
        self.log_stage_end()
        return context
    
    def _perform_calculations(self, context: PipelineContext) -> Dict[str, Any]:
        """Perform actual calculations based on analysis plan"""
        calculations = {}
        
        # Get data for calculations
        fx_rates = context.raw_data.get('fx_rates', {})
        macro_data = context.raw_data.get('macro_data', {})
        enhanced = context.enhanced_data
        
        # Perform simple calculations that are always useful
        calculations['basic_metrics'] = self._calculate_basic_metrics(fx_rates, macro_data, enhanced)
        
        # Ask AI to perform specific calculations based on the analysis plan
        for i, analysis_item in enumerate(context.analysis_plan[:5]):  # Limit to 5 for performance
            calc_result = self._ai_calculation(analysis_item, context)
            calculations[f'analysis_{i+1}'] = {
                'question': analysis_item['question'],
                'calculation': calc_result
            }
        
        return calculations
    
    def _calculate_basic_metrics(self, fx_rates: Dict, macro_data: Dict, enhanced: Dict) -> Dict[str, Any]:
        """Calculate basic metrics that are always useful"""
        metrics = {}
        
        # FX calculations
        if fx_rates:
            usd_jpy = fx_rates.get('USD/JPY', 147.25)
            eur_jpy = fx_rates.get('EUR/JPY', 158.90)
            
            # EUR/USD implied
            if usd_jpy and eur_jpy:
                metrics['implied_eurusd'] = round(eur_jpy / usd_jpy, 4)
            
            # Compare to historical if available
            if 'historical_usdjpy' in enhanced:
                hist = enhanced['historical_usdjpy']
                if '1_month_ago' in hist:
                    metrics['usdjpy_1m_change'] = round(usd_jpy - hist['1_month_ago'], 2)
                    metrics['usdjpy_1m_change_pct'] = round((usd_jpy / hist['1_month_ago'] - 1) * 100, 2)
        
        # Rate differential if we have yield data
        if 'us_yields' in enhanced:
            yields = enhanced['us_yields']
            jgb_10y = 0.25  # Approximate JGB yield
            if '10Y' in yields:
                metrics['rate_differential_10y'] = round(yields['10Y'] - jgb_10y, 2)
        
        # Sentiment vs price alignment
        sentiment = fx_rates.get('sentiment_score', 50) if fx_rates else 50
        metrics['sentiment_score'] = sentiment
        metrics['sentiment_interpretation'] = (
            'Bullish' if sentiment > 60 else
            'Bearish' if sentiment < 40 else
            'Neutral'
        )
        
        return metrics
    
    def _ai_calculation(self, analysis_item: Dict[str, str], context: PipelineContext) -> str:
        """Ask AI to perform a specific calculation"""
        
        # Build data context for AI
        data_context = self._build_calculation_context(context)
        
        prompt = f"""Perform the following financial calculation/analysis:

Question: {analysis_item['question']}
Required Analysis: {analysis_item['analysis']}
Data Needed: {analysis_item['data_needed']}

Available Data:
{data_context}

Perform the calculation or analysis. Show your work:
1. State what you're calculating
2. Show the numbers used
3. Perform the calculation
4. Interpret the result

Be specific with numbers and show actual calculations."""
        
        response = self.ai_analyst._call_openai(prompt, max_tokens=400)
        
        return response
    
    def _build_calculation_context(self, context: PipelineContext) -> str:
        """Build data context for calculations"""
        lines = []
        
        # Add raw data
        if context.raw_data:
            fx = context.raw_data.get('fx_rates', {})
            macro = context.raw_data.get('macro_data', {})
            lines.append(f"Current FX Rates:")
            lines.append(f"  USD/JPY: {fx.get('USD/JPY', 'N/A')}")
            lines.append(f"  EUR/JPY: {fx.get('EUR/JPY', 'N/A')}")
            lines.append(f"Macro Data:")
            lines.append(f"  Japan CPI: {macro.get('japan_cpi', 'N/A')}")
            lines.append(f"  Japan GDP: ${macro.get('japan_gdp', 'N/A')} billion")
            lines.append(f"  Sentiment Score: {context.raw_data.get('sentiment_score', 'N/A')}/100")
        
        # Add enhanced data
        if context.enhanced_data:
            for key, value in context.enhanced_data.items():
                if isinstance(value, dict):
                    lines.append(f"{key}:")
                    for k, v in value.items():
                        lines.append(f"  {k}: {v}")
                else:
                    lines.append(f"{key}: {value}")
        
        # Add basic calculations if available
        if context.calculations and 'basic_metrics' in context.calculations:
            lines.append("Calculated Metrics:")
            for k, v in context.calculations['basic_metrics'].items():
                lines.append(f"  {k}: {v}")
        
        return "\n".join(lines)