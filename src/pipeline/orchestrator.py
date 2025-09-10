"""
Pipeline orchestrator that manages the multi-stage analysis flow
"""

import logging
from typing import List, Optional
import json
import os
from datetime import datetime

from .context import PipelineContext
from .stages import (
    DataCollectionStage,
    InitialSummaryStage,
    EvidenceGatheringStage,
    GapIdentificationStage,
    ReasoningStage,
    CalculationStage,
    ValidationStage,
    ReportGenerationStage
)


class AnalysisPipeline:
    """Orchestrates the multi-stage AI analysis pipeline"""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize pipeline with all stages"""
        self.config_path = config_path
        self.logger = logging.getLogger(__name__)
        
        # Initialize all stages
        self.stages = [
            DataCollectionStage(config_path),
            InitialSummaryStage(config_path),
            EvidenceGatheringStage(config_path),
            GapIdentificationStage(config_path),
            ReasoningStage(config_path),
            CalculationStage(config_path),
            ValidationStage(config_path),
            ReportGenerationStage(config_path)
        ]
        
        self.logger.info(f"Initialized pipeline with {len(self.stages)} stages")
    
    def run(self, save_context: bool = True) -> PipelineContext:
        """
        Run the complete analysis pipeline
        
        Args:
            save_context: Whether to save context to file for debugging
            
        Returns:
            Completed pipeline context with all results
        """
        self.logger.info("="*50)
        self.logger.info("Starting YenSense AI Analysis Pipeline")
        self.logger.info(f"Timestamp: {datetime.now().isoformat()}")
        self.logger.info("="*50)
        
        # Initialize context
        context = PipelineContext()
        
        # Execute each stage sequentially
        for i, stage in enumerate(self.stages, 1):
            stage_name = stage.__class__.__name__
            
            self.logger.info(f"\n--- Stage {i}/{len(self.stages)}: {stage_name} ---")
            
            try:
                # Execute stage
                context = stage.execute(context)
                
                # Check for critical errors
                if self._should_abort(context, stage_name):
                    self.logger.error(f"Critical error in {stage_name}, aborting pipeline")
                    break
                    
            except Exception as e:
                self.logger.error(f"Unexpected error in {stage_name}: {e}")
                context.add_error(f"Pipeline error in {stage_name}: {str(e)}")
                
                # Decide whether to continue or abort
                if i <= 2:  # Critical early stages
                    self.logger.error("Error in critical stage, aborting pipeline")
                    break
                else:
                    self.logger.warning("Continuing pipeline despite error")
        
        # Save context if requested
        if save_context:
            self._save_context(context)
        
        # Log completion
        self.logger.info("\n" + "="*50)
        self.logger.info("Pipeline Execution Complete")
        self.logger.info(f"Final Report Title: {context.title}")
        self.logger.info(f"Report Length: {len(context.final_report)} characters")
        self.logger.info(f"Total Errors: {len(context.errors)}")
        self.logger.info("="*50)
        
        return context
    
    def run_partial(self, stages_to_run: List[str]) -> PipelineContext:
        """
        Run only specific stages of the pipeline
        
        Args:
            stages_to_run: List of stage class names to run
            
        Returns:
            Pipeline context after running specified stages
        """
        context = PipelineContext()
        
        for stage in self.stages:
            if stage.__class__.__name__ in stages_to_run:
                self.logger.info(f"Running stage: {stage.__class__.__name__}")
                context = stage.execute(context)
        
        return context
    
    def _should_abort(self, context: PipelineContext, stage_name: str) -> bool:
        """
        Determine if pipeline should abort based on errors
        
        Args:
            context: Current pipeline context
            stage_name: Name of stage that just completed
            
        Returns:
            True if pipeline should abort
        """
        # Check for critical data missing
        if stage_name == "DataCollectionStage" and not context.raw_data:
            return True
        
        # Check for validation failure
        if stage_name == "ValidationStage":
            validation = context.validation_results
            if validation and validation.get('confidence_score', 100) < 30:
                self.logger.warning("Very low confidence score, but continuing")
        
        # Check for too many errors
        if len(context.errors) > 10:
            return True
        
        return False
    
    def _save_context(self, context: PipelineContext):
        """Save context to file for debugging"""
        try:
            # Create logs directory if it doesn't exist
            os.makedirs("logs/pipeline_contexts", exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"logs/pipeline_contexts/pipeline_context_{timestamp}.json"
            
            # Convert context to serializable format
            context_dict = context.to_dict()
            
            # Save to file
            with open(filename, 'w') as f:
                json.dump(context_dict, f, indent=2, default=str)
            
            self.logger.info(f"Saved pipeline context to {filename}")
            
        except Exception as e:
            self.logger.error(f"Failed to save context: {e}")


def run_pipeline(config_path: str = "config.yaml") -> PipelineContext:
    """
    Convenience function to run the complete pipeline
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        Completed pipeline context
    """
    pipeline = AnalysisPipeline(config_path)
    return pipeline.run()