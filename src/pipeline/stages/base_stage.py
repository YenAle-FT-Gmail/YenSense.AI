"""
Base stage class for pipeline stages
"""

from abc import ABC, abstractmethod
from typing import Optional
import logging
import yaml

from ..context import PipelineContext


class BaseStage(ABC):
    """Abstract base class for pipeline stages"""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize stage with configuration"""
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.logger = logging.getLogger(self.__class__.__name__)
        self.stage_name = self.__class__.__name__
    
    @abstractmethod
    def execute(self, context: PipelineContext) -> PipelineContext:
        """
        Execute the stage processing
        
        Args:
            context: Pipeline context with data from previous stages
            
        Returns:
            Updated context with this stage's results
        """
        pass
    
    def log_stage_start(self):
        """Log stage execution start"""
        self.logger.info(f"Starting {self.stage_name}")
    
    def log_stage_end(self):
        """Log stage execution end"""
        self.logger.info(f"Completed {self.stage_name}")
    
    def handle_error(self, context: PipelineContext, error: Exception) -> PipelineContext:
        """
        Handle errors during stage execution
        
        Args:
            context: Current pipeline context
            error: Exception that occurred
            
        Returns:
            Updated context with error information
        """
        error_msg = f"Error in {self.stage_name}: {str(error)}"
        self.logger.error(error_msg)
        context.add_error(error_msg)
        return context