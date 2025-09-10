"""
Pipeline context object that carries data between stages
"""

from typing import Dict, Any, List, Optional
from datetime import datetime


class PipelineContext:
    """Context object passed between pipeline stages"""
    
    def __init__(self):
        """Initialize empty context"""
        self.timestamp = datetime.now()
        self.raw_data: Dict[str, Any] = {}
        self.summary: str = ""
        self.enhanced_data: Dict[str, Any] = {}
        self.questions: List[str] = []
        self.analysis_plan: List[Dict[str, str]] = []
        self.calculations: Dict[str, Any] = {}
        self.validation_results: Dict[str, Any] = {}
        self.report_sections: Dict[str, str] = {}
        self.final_report: str = ""
        self.title: str = ""
        self.stage_outputs: Dict[str, Any] = {}
        self.errors: List[str] = []
    
    def add_stage_output(self, stage_name: str, output: Any):
        """Add output from a specific stage"""
        self.stage_outputs[stage_name] = output
    
    def get_stage_output(self, stage_name: str) -> Optional[Any]:
        """Get output from a specific stage"""
        return self.stage_outputs.get(stage_name)
    
    def add_error(self, error: str):
        """Add an error message"""
        self.errors.append(f"[{datetime.now().isoformat()}] {error}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'raw_data': self.raw_data,
            'summary': self.summary,
            'enhanced_data': self.enhanced_data,
            'questions': self.questions,
            'analysis_plan': self.analysis_plan,
            'calculations': self.calculations,
            'validation_results': self.validation_results,
            'report_sections': self.report_sections,
            'final_report': self.final_report,
            'title': self.title,
            'stage_outputs': self.stage_outputs,
            'errors': self.errors
        }