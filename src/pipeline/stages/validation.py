"""
Stage 7: Validation
AI validates the analysis and checks for logical consistency
"""

from typing import Dict, Any, List
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from .base_stage import BaseStage
from ..context import PipelineContext
from core.ai_analyst_report import AIAnalystReport


class ValidationStage(BaseStage):
    """AI validates analysis for logical consistency and accuracy"""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize with AI analyst"""
        super().__init__(config_path)
        self.ai_analyst = AIAnalystReport(config_path)
    
    def execute(self, context: PipelineContext) -> PipelineContext:
        """
        AI validates the analysis and conclusions
        
        Returns context with:
        - validation_results: Validation findings and any corrections needed
        """
        self.log_stage_start()
        
        try:
            # Validate the analysis
            validation_results = self._validate_analysis(context)
            
            context.validation_results = validation_results
            
            # Store stage output
            context.add_stage_output('validation', {
                'validation_passed': validation_results.get('overall_valid', False),
                'issues_found': len(validation_results.get('issues', [])),
                'confidence_score': validation_results.get('confidence_score', 0)
            })
            
            self.logger.info(f"Validation complete: {validation_results.get('overall_valid', False)}")
            
        except Exception as e:
            return self.handle_error(context, e)
        
        self.log_stage_end()
        return context
    
    def _validate_analysis(self, context: PipelineContext) -> Dict[str, Any]:
        """Ask AI to validate the analysis"""
        
        # Build comprehensive analysis summary for validation
        analysis_summary = self._build_analysis_summary(context)
        
        prompt = f"""You are a critical financial analyst reviewing the following Japan market analysis. 
Your job is to CHECK FOR ERRORS, INCONSISTENCIES, and LOGICAL FLAWS.

Analysis Summary:
{analysis_summary}

Critically evaluate:
1. Do the calculations make sense?
2. Are the conclusions supported by the data?
3. Are there any contradictions?
4. What might be wrong or misleading?
5. What additional caveats should be noted?

Rate the overall analysis:
- Confidence Score (0-100): How confident are you in this analysis?
- Major Issues: List any serious problems
- Minor Issues: List any small concerns
- Strengths: What parts are well-supported?

Be skeptical and thorough. Challenge assumptions."""
        
        response = self.ai_analyst._call_openai(prompt, max_tokens=800)
        
        # Parse validation response
        validation_results = self._parse_validation(response)
        
        return validation_results
    
    def _build_analysis_summary(self, context: PipelineContext) -> str:
        """Build summary of analysis for validation"""
        lines = []
        
        # Summary
        if context.summary:
            lines.append("=== Initial Market Summary ===")
            lines.append(context.summary[:500])
            lines.append("")
        
        # Questions identified
        if context.questions:
            lines.append("=== Key Questions Identified ===")
            for i, q in enumerate(context.questions[:3], 1):
                lines.append(f"{i}. {q}")
            lines.append("")
        
        # Calculations performed
        if context.calculations:
            lines.append("=== Calculations & Analysis ===")
            
            # Basic metrics
            if 'basic_metrics' in context.calculations:
                metrics = context.calculations['basic_metrics']
                lines.append("Basic Metrics:")
                for k, v in list(metrics.items())[:5]:
                    lines.append(f"  {k}: {v}")
            
            # Specific analyses
            for key, value in context.calculations.items():
                if key.startswith('analysis_'):
                    lines.append(f"\n{key}:")
                    if isinstance(value, dict):
                        lines.append(f"  Question: {value.get('question', 'N/A')[:100]}")
                        calc = value.get('calculation', 'N/A')
                        if isinstance(calc, str):
                            lines.append(f"  Result: {calc[:200]}...")
            lines.append("")
        
        return "\n".join(lines)
    
    def _parse_validation(self, response: str) -> Dict[str, Any]:
        """Parse validation response from AI"""
        validation = {
            'overall_valid': True,
            'confidence_score': 70,
            'issues': [],
            'strengths': [],
            'caveats': []
        }
        
        lines = response.split('\n')
        current_section = None
        
        for line in lines:
            line_lower = line.lower()
            
            # Detect sections
            if 'confidence score' in line_lower or 'confidence:' in line_lower:
                # Try to extract number
                import re
                numbers = re.findall(r'\d+', line)
                if numbers:
                    validation['confidence_score'] = int(numbers[0])
            elif 'major issue' in line_lower or 'serious problem' in line_lower:
                current_section = 'major_issues'
            elif 'minor issue' in line_lower or 'small concern' in line_lower:
                current_section = 'minor_issues'
            elif 'strength' in line_lower or 'well-supported' in line_lower:
                current_section = 'strengths'
            elif 'caveat' in line_lower or 'note' in line_lower:
                current_section = 'caveats'
            elif line.strip() and current_section:
                # Add to appropriate section
                if current_section == 'major_issues' and line.strip().startswith('-'):
                    validation['issues'].append(f"MAJOR: {line.strip()[1:].strip()}")
                    validation['overall_valid'] = False
                elif current_section == 'minor_issues' and line.strip().startswith('-'):
                    validation['issues'].append(f"MINOR: {line.strip()[1:].strip()}")
                elif current_section == 'strengths' and line.strip().startswith('-'):
                    validation['strengths'].append(line.strip()[1:].strip())
                elif current_section == 'caveats' and line.strip().startswith('-'):
                    validation['caveats'].append(line.strip()[1:].strip())
        
        # Set overall validity based on confidence and issues
        if validation['confidence_score'] < 50 or len([i for i in validation['issues'] if i.startswith('MAJOR')]) > 0:
            validation['overall_valid'] = False
        
        # Ensure we have some feedback
        if not validation['issues'] and not validation['strengths']:
            validation['strengths'].append("Analysis appears logically consistent")
            validation['caveats'].append("Limited data available for comprehensive validation")
        
        return validation