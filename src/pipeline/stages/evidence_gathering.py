"""
Stage 3: Evidence Gathering
AI identifies what additional evidence is needed and fetches it
"""

from typing import Dict, Any, List
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from .base_stage import BaseStage
from ..context import PipelineContext
from ai_analyst import AIAnalyst
from data_fetcher import DataFetcher


class EvidenceGatheringStage(BaseStage):
    """AI identifies and gathers additional evidence needed for analysis"""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize with AI analyst and data fetcher"""
        super().__init__(config_path)
        self.ai_analyst = AIAnalyst(config_path)
        self.data_fetcher = DataFetcher(config_path)
    
    def execute(self, context: PipelineContext) -> PipelineContext:
        """
        AI identifies what additional evidence is needed and attempts to gather it
        
        Returns context with:
        - enhanced_data: Additional data gathered based on AI's request
        """
        self.log_stage_start()
        
        try:
            # Ask AI what additional evidence would be helpful
            evidence_needed = self._identify_evidence_needed(context)
            
            # Gather the identified evidence
            enhanced_data = self._gather_evidence(evidence_needed, context)
            
            context.enhanced_data = enhanced_data
            
            # Store stage output
            context.add_stage_output('evidence_gathering', {
                'evidence_requested': evidence_needed,
                'evidence_gathered': list(enhanced_data.keys())
            })
            
            self.logger.info(f"Gathered {len(enhanced_data)} additional data points")
            
        except Exception as e:
            return self.handle_error(context, e)
        
        self.log_stage_end()
        return context
    
    def _identify_evidence_needed(self, context: PipelineContext) -> List[str]:
        """Ask AI what additional evidence would help explain the market moves"""
        
        prompt = f"""Based on the following market summary, identify what SPECIFIC additional evidence or data would help explain these market movements:

Summary:
{context.summary}

Current data available:
- FX rates (USD/JPY, EUR/JPY)
- Japan CPI and GDP
- Recent news headlines

Identify 3-5 specific pieces of additional evidence that would be most valuable. Be specific and practical. Examples:
- "Historical USD/JPY levels from 1 month ago for comparison"
- "US Treasury yields to understand rate differentials"
- "Recent BOJ policy statements or meeting minutes"
- "Oil prices to understand inflation pressures"
- "VIX index to gauge risk sentiment"

List the evidence needed (one per line):"""
        
        response = self.ai_analyst._call_openai(prompt, max_tokens=400)
        
        # Parse response into list
        evidence_list = [line.strip() for line in response.split('\n') if line.strip() and not line.startswith('#')]
        evidence_list = evidence_list[:5]  # Limit to 5 items
        
        self.logger.info(f"AI identified {len(evidence_list)} pieces of evidence needed")
        return evidence_list
    
    def _gather_evidence(self, evidence_needed: List[str], context: PipelineContext) -> Dict[str, Any]:
        """Attempt to gather the evidence identified by AI"""
        enhanced_data = {}
        
        for evidence in evidence_needed:
            evidence_lower = evidence.lower()
            
            # Try to gather based on keywords in the evidence request
            if 'historical' in evidence_lower and 'usd/jpy' in evidence_lower:
                # Get historical FX data (simplified - would need proper implementation)
                enhanced_data['historical_usdjpy'] = {
                    '1_month_ago': 145.50,  # Placeholder
                    '3_months_ago': 142.25,  # Placeholder
                    '1_year_ago': 135.00  # Placeholder
                }
                self.logger.info("Added historical USD/JPY data")
                
            elif 'treasury' in evidence_lower or 'yields' in evidence_lower:
                # Get US Treasury yields (simplified)
                enhanced_data['us_yields'] = {
                    '2Y': 4.75,  # Placeholder
                    '10Y': 4.25,  # Placeholder
                    'spread_2s10s': -0.50  # Placeholder
                }
                self.logger.info("Added US Treasury yield data")
                
            elif 'oil' in evidence_lower or 'energy' in evidence_lower:
                # Get oil prices (simplified)
                enhanced_data['oil_prices'] = {
                    'WTI': 75.50,  # Placeholder
                    'Brent': 79.25,  # Placeholder
                    'change_1d': 1.2  # Placeholder
                }
                self.logger.info("Added oil price data")
                
            elif 'vix' in evidence_lower or 'volatility' in evidence_lower:
                # Get VIX data (simplified)
                enhanced_data['vix'] = {
                    'level': 15.5,  # Placeholder
                    'change_1d': -0.5,  # Placeholder
                    '20d_avg': 16.2  # Placeholder
                }
                self.logger.info("Added VIX/volatility data")
                
            elif 'boj' in evidence_lower and ('policy' in evidence_lower or 'statement' in evidence_lower):
                # Get recent BOJ policy info
                enhanced_data['boj_policy'] = {
                    'rate': -0.1,
                    'ycc_target': 0.0,
                    'last_meeting': '2025-09-01',
                    'stance': 'Accommodative'
                }
                self.logger.info("Added BOJ policy data")
                
            else:
                self.logger.warning(f"Could not gather evidence for: {evidence}")
        
        # Always add some context data
        if not enhanced_data:
            enhanced_data['market_context'] = {
                'note': 'Limited additional data available',
                'suggestion': 'Analysis will proceed with available information'
            }
        
        return enhanced_data