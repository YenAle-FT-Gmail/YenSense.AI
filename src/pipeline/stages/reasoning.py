"""
Stage 5: Reasoning
AI determines what analysis is needed to answer the questions
"""

from typing import List, Dict
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from .base_stage import BaseStage
from ..context import PipelineContext
from core.ai_analyst_report import AIAnalystReport


class ReasoningStage(BaseStage):
    """AI reasons about what analysis is needed to answer identified questions"""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize with AI analyst"""
        super().__init__(config_path)
        self.ai_analyst = AIAnalystReport(config_path)
    
    def execute(self, context: PipelineContext) -> PipelineContext:
        """
        AI determines what specific analysis would answer the questions
        
        Returns context with:
        - analysis_plan: List of specific analyses to perform
        """
        self.log_stage_start()
        
        try:
            # Create analysis plan for each question
            analysis_plan = self._create_analysis_plan(context)
            
            context.analysis_plan = analysis_plan
            
            # Store stage output
            context.add_stage_output('reasoning', {
                'analyses_planned': len(analysis_plan),
                'analysis_types': self._categorize_analyses(analysis_plan)
            })
            
            self.logger.info(f"Created plan for {len(analysis_plan)} analyses")
            
        except Exception as e:
            return self.handle_error(context, e)
        
        self.log_stage_end()
        return context
    
    def _create_analysis_plan(self, context: PipelineContext) -> List[Dict[str, str]]:
        """Ask AI to create specific analysis plan for each question"""
        
        questions_text = "\n".join([f"{i+1}. {q}" for i, q in enumerate(context.questions)])
        
        prompt = f"""You are a senior financial analyst. For each question below, determine what SPECIFIC analysis would help answer it.

Questions to answer:
{questions_text}

Available data:
- Current and historical FX rates
- Japan macro data (CPI, GDP)
- US Treasury yields
- Market sentiment indicators
- News and policy information

For each question, specify:
1. What calculation or comparison to perform
2. What data points to use
3. What the result would tell us

Be specific and practical. Focus on simple, meaningful analyses.

Format your response as:
Question 1: [brief restatement]
Analysis: [specific analysis to perform]
Data needed: [specific data points]
Insight: [what this tells us]

Question 2: ...
(continue for all questions)"""
        
        response = self.ai_analyst._call_openai(prompt, max_tokens=1200)
        
        # Parse response into structured analysis plan
        analysis_plan = self._parse_analysis_plan(response, context.questions)
        
        return analysis_plan
    
    def _parse_analysis_plan(self, response: str, questions: List[str]) -> List[Dict[str, str]]:
        """Parse AI response into structured analysis plan"""
        plan = []
        
        # Split by "Question" markers
        sections = response.split('Question')[1:]  # Skip empty first element
        
        for i, section in enumerate(sections):
            if i >= len(questions):
                break
                
            analysis_item = {
                'question': questions[i] if i < len(questions) else 'Unknown question',
                'analysis': '',
                'data_needed': '',
                'insight': ''
            }
            
            lines = section.strip().split('\n')
            for line in lines:
                line_lower = line.lower()
                if 'analysis:' in line_lower:
                    analysis_item['analysis'] = line.split(':', 1)[1].strip()
                elif 'data needed:' in line_lower or 'data:' in line_lower:
                    analysis_item['data_needed'] = line.split(':', 1)[1].strip()
                elif 'insight:' in line_lower or 'tells us:' in line_lower:
                    analysis_item['insight'] = line.split(':', 1)[1].strip()
            
            # Ensure we have at least some analysis
            if not analysis_item['analysis']:
                analysis_item['analysis'] = f"Compare current levels to historical averages"
            
            plan.append(analysis_item)
        
        # If parsing failed, create simple fallback plan
        if not plan:
            for q in questions[:3]:
                plan.append({
                    'question': q,
                    'analysis': 'Analyze current vs historical levels',
                    'data_needed': 'Current and historical data points',
                    'insight': 'Understand if current levels are unusual'
                })
        
        return plan
    
    def _categorize_analyses(self, analysis_plan: List[Dict[str, str]]) -> Dict[str, int]:
        """Categorize types of analyses planned"""
        categories = {
            'comparison': 0,
            'correlation': 0,
            'trend': 0,
            'calculation': 0,
            'other': 0
        }
        
        for item in analysis_plan:
            analysis_text = item.get('analysis', '').lower()
            if 'compar' in analysis_text or 'versus' in analysis_text or 'vs' in analysis_text:
                categories['comparison'] += 1
            elif 'correlat' in analysis_text or 'relationship' in analysis_text:
                categories['correlation'] += 1
            elif 'trend' in analysis_text or 'change' in analysis_text or 'movement' in analysis_text:
                categories['trend'] += 1
            elif 'calculat' in analysis_text or 'compute' in analysis_text:
                categories['calculation'] += 1
            else:
                categories['other'] += 1
        
        return categories