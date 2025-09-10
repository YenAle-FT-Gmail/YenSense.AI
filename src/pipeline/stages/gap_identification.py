"""
Stage 4: Gap Identification
AI identifies questions, contradictions, and gaps in understanding
"""

from typing import List
import json
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from .base_stage import BaseStage
from ..context import PipelineContext
from ai_analyst import AIAnalyst


class GapIdentificationStage(BaseStage):
    """AI identifies gaps, contradictions, and key questions in the market narrative"""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize with AI analyst"""
        super().__init__(config_path)
        self.ai_analyst = AIAnalyst(config_path)
    
    def execute(self, context: PipelineContext) -> PipelineContext:
        """
        AI identifies key questions and gaps in understanding
        
        Returns context with:
        - questions: List of specific questions that need answering
        """
        self.log_stage_start()
        
        try:
            # Build comprehensive view for gap analysis
            questions = self._identify_gaps(context)
            
            context.questions = questions
            
            # Store stage output
            context.add_stage_output('gap_identification', {
                'questions_identified': len(questions),
                'question_categories': self._categorize_questions(questions)
            })
            
            self.logger.info(f"Identified {len(questions)} key questions")
            
        except Exception as e:
            return self.handle_error(context, e)
        
        self.log_stage_end()
        return context
    
    def _identify_gaps(self, context: PipelineContext) -> List[str]:
        """Ask AI to identify gaps and contradictions"""
        
        # Build data summary for AI
        data_summary = self._build_data_summary(context)
        
        prompt = f"""You are a senior financial analyst examining Japan market data. Identify KEY QUESTIONS and GAPS in the following information:

Market Summary:
{context.summary}

Available Data:
{data_summary}

Your task:
1. Identify what seems contradictory or unusual
2. Find gaps in the explanation - what's missing?
3. Question relationships between different data points
4. Identify what needs further investigation

Generate 5-7 SPECIFIC, ANALYTICAL questions. Examples of good questions:
- "Why did USD/JPY strengthen despite weak US data?"
- "What explains the divergence between CPI trends and BOJ policy stance?"
- "How does current positioning compare to previous BOJ policy shifts?"
- "What is driving the disconnect between equity and FX markets?"

Avoid generic questions. Focus on specific market dynamics that need explanation.

List your questions (one per line):"""
        
        response = self.ai_analyst._call_openai(prompt, max_tokens=600)
        
        # Parse response into list of questions
        questions = [line.strip() for line in response.split('\n') 
                    if line.strip() and '?' in line]
        
        # Ensure we have good questions
        if len(questions) < 3:
            # Add some fallback questions
            questions.extend([
                "What is driving the current USD/JPY level relative to rate differentials?",
                "How does current market positioning compare to historical norms?",
                "What are the key risks to the current market consensus?"
            ])
        
        return questions[:7]  # Limit to 7 questions
    
    def _build_data_summary(self, context: PipelineContext) -> str:
        """Build a summary of available data for the AI"""
        summary_parts = []
        
        # Raw data
        if context.raw_data:
            fx = context.raw_data.get('fx_rates', {})
            macro = context.raw_data.get('macro_data', {})
            summary_parts.append(f"FX: USD/JPY={fx.get('USD/JPY', 'N/A')}, EUR/JPY={fx.get('EUR/JPY', 'N/A')}")
            summary_parts.append(f"Macro: CPI={macro.get('japan_cpi', 'N/A')}, GDP=${macro.get('japan_gdp', 'N/A')}B")
            summary_parts.append(f"Sentiment Score: {context.raw_data.get('sentiment_score', 'N/A')}/100")
        
        # Enhanced data
        if context.enhanced_data:
            for key, value in context.enhanced_data.items():
                if isinstance(value, dict):
                    summary_parts.append(f"{key}: {json.dumps(value, indent=0)[:100]}...")
                else:
                    summary_parts.append(f"{key}: {str(value)[:100]}")
        
        return "\n".join(summary_parts)
    
    def _categorize_questions(self, questions: List[str]) -> dict:
        """Categorize questions by type"""
        categories = {
            'policy': 0,
            'technical': 0,
            'fundamental': 0,
            'positioning': 0,
            'risk': 0,
            'other': 0
        }
        
        for q in questions:
            q_lower = q.lower()
            if 'boj' in q_lower or 'policy' in q_lower or 'central bank' in q_lower:
                categories['policy'] += 1
            elif 'level' in q_lower or 'resistance' in q_lower or 'support' in q_lower:
                categories['technical'] += 1
            elif 'economy' in q_lower or 'gdp' in q_lower or 'inflation' in q_lower:
                categories['fundamental'] += 1
            elif 'position' in q_lower or 'flow' in q_lower or 'sentiment' in q_lower:
                categories['positioning'] += 1
            elif 'risk' in q_lower or 'tail' in q_lower or 'hedge' in q_lower:
                categories['risk'] += 1
            else:
                categories['other'] += 1
        
        return categories