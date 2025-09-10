"""
Stages 8-11: Report Generation
AI generates the final report section by section, with dynamic title
"""

from typing import Dict, Any
import sys
import os
from datetime import datetime
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from .base_stage import BaseStage
from ..context import PipelineContext
from ai_analyst import AIAnalyst


class ReportGenerationStage(BaseStage):
    """AI generates the final report through multiple sub-stages"""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize with AI analyst"""
        super().__init__(config_path)
        self.ai_analyst = AIAnalyst(config_path)
    
    def execute(self, context: PipelineContext) -> PipelineContext:
        """
        Generate the complete report through sub-stages:
        - Stage 8: Generate appendix
        - Stage 9: Generate sections
        - Stage 10: Compile report
        - Stage 11: Generate title
        """
        self.log_stage_start()
        
        try:
            # Stage 8: Generate appendix with supporting data
            appendix = self._generate_appendix(context)
            
            # Stage 9: Generate each section
            sections = self._generate_sections(context)
            
            # Stage 10: Compile full report
            full_report = self._compile_report(sections, appendix, context)
            
            # Stage 11: Generate dynamic title
            title = self._generate_title(context, sections)
            
            # Store results
            context.report_sections = sections
            context.final_report = full_report
            context.title = title
            
            # Store stage output
            context.add_stage_output('report_generation', {
                'sections_generated': len(sections),
                'report_length': len(full_report),
                'title': title
            })
            
            self.logger.info(f"Generated report: '{title}'")
            
        except Exception as e:
            return self.handle_error(context, e)
        
        self.log_stage_end()
        return context
    
    def _generate_appendix(self, context: PipelineContext) -> str:
        """Stage 8: Generate appendix with methodology and data sources"""
        
        prompt = f"""Generate an appendix for a Japan FX/macro report with the following information:

Data Sources Used:
- FRED Economic Data (CPI, GDP)
- Alpha Vantage (FX rates)
- Bank of Japan (policy information)
- Reuters, Nikkei (news)

Validation Results:
- Confidence Score: {context.validation_results.get('confidence_score', 70)}/100
- Issues Found: {len(context.validation_results.get('issues', []))}

Questions Investigated: {len(context.questions)}
Calculations Performed: {len(context.calculations)}

Write a brief, professional appendix (150-200 words) covering:
1. Methodology overview
2. Data sources and timestamps
3. Key assumptions
4. Limitations and caveats

Format with clear sections."""
        
        appendix = self.ai_analyst._call_openai(prompt, max_tokens=300)
        return appendix
    
    def _generate_sections(self, context: PipelineContext) -> Dict[str, str]:
        """Stage 9: Generate each report section"""
        sections = {}
        
        # Executive Summary
        sections['executive_summary'] = self._generate_executive_summary(context)
        
        # Market Analysis
        sections['market_analysis'] = self._generate_market_analysis(context)
        
        # Key Findings
        sections['key_findings'] = self._generate_key_findings(context)
        
        # Risk Assessment
        sections['risk_assessment'] = self._generate_risk_assessment(context)
        
        # Outlook
        sections['outlook'] = self._generate_outlook(context)
        
        return sections
    
    def _generate_executive_summary(self, context: PipelineContext) -> str:
        """Generate executive summary section"""
        
        fx_rates = context.raw_data.get('fx_rates', {})
        sentiment = context.raw_data.get('sentiment_score', 50)
        confidence = context.validation_results.get('confidence_score', 70)
        
        prompt = f"""Write an executive summary for a Japan FX/macro report.

Current Conditions:
- USD/JPY: {fx_rates.get('USD/JPY', 147.25)}
- Market Sentiment: {sentiment}/100
- Analysis Confidence: {confidence}/100

Key Questions Investigated:
{chr(10).join([f"- {q}" for q in context.questions[:3]])}

Main Findings:
{self._summarize_calculations(context.calculations)}

Write a professional, evidence-based executive summary (200-250 words) that:
1. States the market view clearly (bullish/bearish/neutral on yen)
2. Highlights 2-3 key supporting factors with specific data
3. Notes main risks
4. Provides actionable takeaway

Be specific and data-driven. Avoid generic statements."""
        
        return self.ai_analyst._call_openai(prompt, max_tokens=400)
    
    def _generate_market_analysis(self, context: PipelineContext) -> str:
        """Generate detailed market analysis section"""
        
        # Build analysis context
        analysis_points = []
        for key, value in context.calculations.items():
            if key.startswith('analysis_'):
                if isinstance(value, dict):
                    analysis_points.append(value.get('calculation', '')[:200])
        
        prompt = f"""Write the Market Analysis section of a Japan FX report.

Market Summary:
{context.summary}

Detailed Analysis Performed:
{chr(10).join(analysis_points[:3])}

Enhanced Data Available:
{', '.join(context.enhanced_data.keys())}

Write a detailed market analysis (300-400 words) covering:
1. Current FX positioning and drivers
2. Macro backdrop and implications
3. Technical levels and flows
4. Cross-asset context (equities, bonds)

Use specific numbers and cite data sources. Focus on evidence-based analysis."""
        
        return self.ai_analyst._call_openai(prompt, max_tokens=600)
    
    def _generate_key_findings(self, context: PipelineContext) -> str:
        """Generate key findings section"""
        
        prompt = f"""Based on the analysis, generate Key Findings section.

Questions Answered:
{chr(10).join([f"{i+1}. {q}" for i, q in enumerate(context.questions[:4])])}

Validation Results:
- Strengths: {', '.join(context.validation_results.get('strengths', [])[:2])}
- Concerns: {', '.join(context.validation_results.get('issues', [])[:2])}

Write 3-5 KEY FINDINGS (bullet points, 2-3 sentences each) that:
1. Answer the main questions raised
2. Highlight surprising or important insights
3. Are supported by specific data/calculations
4. Have clear market implications

Format as:
• Finding 1: [specific insight with data]
• Finding 2: [specific insight with data]
(etc.)"""
        
        return self.ai_analyst._call_openai(prompt, max_tokens=400)
    
    def _generate_risk_assessment(self, context: PipelineContext) -> str:
        """Generate risk assessment section"""
        
        prompt = f"""Generate Risk Assessment section for Japan FX report.

Current Sentiment: {context.raw_data.get('sentiment_score', 50)}/100
Validation Confidence: {context.validation_results.get('confidence_score', 70)}/100
Key Caveats: {', '.join(context.validation_results.get('caveats', [])[:2])}

Identify and assess:
1. Upside risks for yen (what could strengthen it)
2. Downside risks for yen (what could weaken it)
3. Event risks (BOJ, Fed, data releases)
4. Tail risks (low probability, high impact)

Write 200-250 words. Be specific about:
- Risk triggers
- Probability assessment
- Potential market impact (in pips/percentage)

Format with clear subsections."""
        
        return self.ai_analyst._call_openai(prompt, max_tokens=400)
    
    def _generate_outlook(self, context: PipelineContext) -> str:
        """Generate market outlook section"""
        
        prompt = f"""Generate the Outlook section for Japan FX report.

Current Levels:
- USD/JPY: {context.raw_data.get('fx_rates', {}).get('USD/JPY', 147.25)}
- Sentiment: {context.raw_data.get('sentiment_score', 50)}/100

Analysis Confidence: {context.validation_results.get('confidence_score', 70)}/100

Write the outlook (150-200 words) covering:
1. Base case scenario for next week
2. Key levels to watch (support/resistance)
3. Data/events to monitor
4. Recommended positioning

Be specific with:
- Price targets/ranges
- Timeframes
- Conviction level

End with one clear, actionable recommendation."""
        
        return self.ai_analyst._call_openai(prompt, max_tokens=300)
    
    def _compile_report(self, sections: Dict[str, str], appendix: str, context: PipelineContext) -> str:
        """Stage 10: Compile all sections into final report"""
        
        report_parts = []
        
        # Add header
        report_parts.append(f"# YenSense AI Weekly Strategist Report")
        report_parts.append(f"**Date:** {datetime.now().strftime('%B %d, %Y')}")
        report_parts.append("")
        
        # Add sections in order
        report_parts.append("## Executive Summary")
        report_parts.append(sections['executive_summary'])
        report_parts.append("")
        
        report_parts.append("## Market Analysis")
        report_parts.append(sections['market_analysis'])
        report_parts.append("")
        
        report_parts.append("## Key Findings")
        report_parts.append(sections['key_findings'])
        report_parts.append("")
        
        report_parts.append("## Risk Assessment")
        report_parts.append(sections['risk_assessment'])
        report_parts.append("")
        
        report_parts.append("## Outlook")
        report_parts.append(sections['outlook'])
        report_parts.append("")
        
        # Add appendix
        report_parts.append("## Appendix: Methodology & Data")
        report_parts.append(appendix)
        report_parts.append("")
        
        # Add disclaimer
        report_parts.append("---")
        report_parts.append("*Disclaimer: This report is for informational purposes only and does not constitute financial advice.*")
        
        return "\n".join(report_parts)
    
    def _generate_title(self, context: PipelineContext, sections: Dict[str, str]) -> str:
        """Stage 11: Generate dynamic, compelling title"""
        
        prompt = f"""Generate a compelling, specific title for this Japan FX report.

Executive Summary (first 200 chars):
{sections['executive_summary'][:200]}

Key Theme from Analysis:
{context.questions[0] if context.questions else 'Japan FX Dynamics'}

Current Market:
- USD/JPY: {context.raw_data.get('fx_rates', {}).get('USD/JPY', 147.25)}
- Sentiment: {context.raw_data.get('sentiment_score', 50)}/100

Generate a title that is:
1. Specific and informative (not generic)
2. 8-12 words
3. Captures the main theme/finding
4. Professional but engaging

Good examples:
- "BOJ's Patience Tested as 150 Becomes the New Battleground"
- "Yen Weakness Persists Despite Intervention Risks at Multi-Decade Lows"
- "Rate Differential Trumps Haven Flows in USD/JPY Push Higher"

Bad examples:
- "Weekly Japan Report"
- "FX Update"

Title:"""
        
        title = self.ai_analyst._call_openai(prompt, max_tokens=50)
        
        # Clean up title
        title = title.strip().strip('"').strip("'")
        
        # Fallback if title generation fails
        if not title or len(title) < 10:
            title = f"Japan FX Analysis: USD/JPY at {context.raw_data.get('fx_rates', {}).get('USD/JPY', 147.25)}"
        
        return title
    
    def _summarize_calculations(self, calculations: Dict[str, Any]) -> str:
        """Summarize key calculations for prompts"""
        summary_parts = []
        
        if 'basic_metrics' in calculations:
            metrics = calculations['basic_metrics']
            if 'usdjpy_1m_change_pct' in metrics:
                summary_parts.append(f"USD/JPY 1M change: {metrics['usdjpy_1m_change_pct']}%")
            if 'rate_differential_10y' in metrics:
                summary_parts.append(f"US-Japan 10Y spread: {metrics['rate_differential_10y']}%")
        
        return ", ".join(summary_parts) if summary_parts else "Various calculations performed"