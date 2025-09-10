#!/usr/bin/env python3
"""
Test script for the multi-stage AI pipeline
"""

import sys
import os
import logging

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from pipeline.orchestrator import AnalysisPipeline
from pipeline.context import PipelineContext


def test_pipeline():
    """Test the complete pipeline"""
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger = logging.getLogger(__name__)
    
    logger.info("="*60)
    logger.info("TESTING MULTI-STAGE AI PIPELINE")
    logger.info("="*60)
    
    try:
        # Initialize pipeline
        logger.info("\nInitializing pipeline...")
        pipeline = AnalysisPipeline("config.yaml")
        
        # Run the pipeline
        logger.info("\nRunning complete pipeline (8 stages)...")
        context = pipeline.run(save_context=True)
        
        # Check results
        logger.info("\n" + "="*60)
        logger.info("PIPELINE RESULTS")
        logger.info("="*60)
        
        if context.title:
            logger.info(f"✓ Report Title: {context.title}")
        else:
            logger.warning("✗ No title generated")
        
        if context.summary:
            logger.info(f"✓ Initial Summary: {len(context.summary)} chars")
        else:
            logger.warning("✗ No summary generated")
        
        if context.questions:
            logger.info(f"✓ Questions Identified: {len(context.questions)}")
            for i, q in enumerate(context.questions[:3], 1):
                logger.info(f"  {i}. {q}")
        else:
            logger.warning("✗ No questions identified")
        
        if context.calculations:
            logger.info(f"✓ Calculations Performed: {len(context.calculations)}")
        else:
            logger.warning("✗ No calculations performed")
        
        if context.validation_results:
            confidence = context.validation_results.get('confidence_score', 0)
            logger.info(f"✓ Validation Confidence: {confidence}/100")
        else:
            logger.warning("✗ No validation performed")
        
        if context.final_report:
            logger.info(f"✓ Final Report: {len(context.final_report)} chars")
            
            # Save sample report
            output_file = "pipeline_test_report.md"
            with open(output_file, 'w') as f:
                f.write(f"# {context.title}\n\n")
                f.write(context.final_report)
            logger.info(f"✓ Saved test report to: {output_file}")
        else:
            logger.warning("✗ No report generated")
        
        if context.errors:
            logger.warning(f"⚠ Errors encountered: {len(context.errors)}")
            for error in context.errors[:3]:
                logger.warning(f"  - {error}")
        else:
            logger.info("✓ No errors encountered")
        
        logger.info("\n" + "="*60)
        logger.info("PIPELINE TEST COMPLETE")
        logger.info("="*60)
        
        return context
        
    except Exception as e:
        logger.error(f"Pipeline test failed: {e}", exc_info=True)
        return None


if __name__ == "__main__":
    test_pipeline()