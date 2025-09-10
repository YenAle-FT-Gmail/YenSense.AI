#!/usr/bin/env python3
"""
YenSense AI - Main Orchestration Script
Coordinates data fetching, report generation, and scheduling
"""

import argparse
import logging
import logging.handlers
import os
import sys
import time
from datetime import datetime
import subprocess

import schedule
import pytz
import yaml

# Add script directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.data_fetcher import DataFetcher
from generators.morning_brief import MorningBriefGenerator
from generators.weekly_report import WeeklyReportGenerator
from pipeline.orchestrator import AnalysisPipeline


class YenSenseAI:
    """Main orchestrator for YenSense AI system"""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize YenSense AI system"""
        self.config_path = config_path
        self.load_config()
        self.setup_logging()
        
        # Initialize components
        self.data_fetcher = DataFetcher(config_path)
        self.morning_brief = MorningBriefGenerator(config_path)
        self.weekly_report = WeeklyReportGenerator(config_path)
        
        # Set timezone
        self.timezone = pytz.timezone(self.config['schedule']['timezone'])
        
        self.logger.info("YenSense AI initialized successfully")
    
    def load_config(self):
        """Load configuration from YAML file"""
        with open(self.config_path, 'r') as f:
            self.config = yaml.safe_load(f)
    
    def setup_logging(self):
        """Setup logging configuration"""
        log_file = self.config['logging']['file']
        if os.path.dirname(log_file):
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        # Create logger
        self.logger = logging.getLogger('YenSenseAI')
        self.logger.setLevel(getattr(logging, self.config['logging']['level']))
        
        # File handler with rotation
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=self.config['logging']['max_size_mb'] * 1024 * 1024,
            backupCount=self.config['logging']['backup_count']
        )
        file_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        )
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        )
        
        # Add handlers
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        # Set logging for modules
        logging.getLogger('data_fetcher').setLevel(logging.INFO)
        logging.getLogger('morning_brief').setLevel(logging.INFO)
        logging.getLogger('weekly_report').setLevel(logging.INFO)
    
    def run_morning_brief(self):
        """Execute morning brief generation"""
        self.logger.info("=" * 50)
        self.logger.info("Starting Daily Morning Brief Generation")
        self.logger.info(f"Time: {datetime.now(self.timezone).strftime('%Y-%m-%d %H:%M:%S %Z')}")
        
        try:
            # Fetch latest data
            self.logger.info("Fetching latest market data...")
            data = self.data_fetcher.fetch_all_data()
            
            # Generate morning brief segments
            self.logger.info("Generating domain-specific segments...")
            segments = self.morning_brief.generate_segments(data)
            
            # Save brief and generate multi-voice audio
            self.logger.info("Saving brief and generating multi-voice audio...")
            result = self.morning_brief.save_brief(segments, data)
            
            self.logger.info(f"Morning brief completed successfully!")
            self.logger.info(f"Text file: {result['text_file']}")
            self.logger.info(f"Audio file: {result['audio_file']}")
            
            # Deploy to GitHub Pages if enabled
            if self.config['github_pages']['enabled']:
                self.deploy_to_github_pages(result['text_file'], 'morning')
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error generating morning brief: {e}", exc_info=True)
            return None
    
    def run_weekly_report(self):
        """Execute weekly report generation using new pipeline"""
        self.logger.info("=" * 50)
        self.logger.info("Starting Weekly Strategist Report Generation (Pipeline Mode)")
        self.logger.info(f"Time: {datetime.now(self.timezone).strftime('%Y-%m-%d %H:%M:%S %Z')}")
        
        try:
            # Use new multi-stage pipeline for weekly reports
            self.logger.info("Initializing multi-stage analysis pipeline...")
            pipeline = AnalysisPipeline(self.config_path)
            
            # Run the complete pipeline
            self.logger.info("Running analysis pipeline (8 stages)...")
            context = pipeline.run(save_context=True)
            
            # Check if pipeline succeeded
            if not context.final_report:
                self.logger.error("Pipeline failed to generate report")
                return None
            
            # Use the pipeline-generated report
            self.logger.info(f"Pipeline complete. Report title: {context.title}")
            
            # Save the report using existing infrastructure
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d")
            
            # Save markdown report
            md_file = f"data/output/reports/report_{timestamp}.md"
            os.makedirs(os.path.dirname(md_file), exist_ok=True)
            with open(md_file, 'w') as f:
                f.write(context.final_report)
            self.logger.info(f"Saved markdown report: {md_file}")
            
            # Generate HTML version with charts
            self.logger.info("Generating HTML version with charts...")
            html_report = self.weekly_report._generate_html_wrapper(
                context.final_report,
                context.raw_data
            )
            
            html_file = f"data/output/reports/report_{timestamp}.html"
            with open(html_file, 'w') as f:
                f.write(html_report)
            self.logger.info(f"Saved HTML report: {html_file}")
            
            result = {
                'markdown_file': md_file,
                'html_file': html_file,
                'title': context.title
            }
            
            # Deploy to GitHub Pages if enabled
            if self.config['github_pages']['enabled']:
                self.deploy_to_github_pages(html_file, 'weekly')
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error in pipeline report generation: {e}", exc_info=True)
            self.logger.info("Falling back to original report generation...")
            
            # Fallback to original method
            self.logger.info("Fetching comprehensive market data...")
            data = self.data_fetcher.fetch_all_data()
            
            # Generate reports
            self.logger.info("Generating weekly strategist report...")
            result = self.weekly_report.save_reports(data)
            
            self.logger.info(f"Weekly report completed successfully!")
            self.logger.info(f"Markdown file: {result['markdown_file']}")
            self.logger.info(f"HTML file: {result['html_file']}")
            
            # Deploy to GitHub Pages if enabled
            if self.config['github_pages']['enabled']:
                self.deploy_to_github_pages(result['html_file'], 'weekly')
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error generating weekly report: {e}", exc_info=True)
            return None
    
    def deploy_to_github_pages(self, file_path: str, report_type: str):
        """Deploy reports to GitHub Pages"""
        try:
            self.logger.info(f"Deploying {report_type} report to GitHub Pages...")
            
            # Create docs directory if it doesn't exist
            docs_dir = self.config['github_pages']['directory']
            os.makedirs(docs_dir, exist_ok=True)
            
            # Copy file to docs directory
            import shutil
            filename = os.path.basename(file_path)
            dest_path = os.path.join(docs_dir, filename)
            shutil.copy2(file_path, dest_path)
            
            # Create or update index.html
            self.update_github_pages_index(docs_dir, report_type, filename)
            
            # Use ghp-import to deploy (requires git repository)
            try:
                subprocess.run([
                    'ghp-import', '-n', '-p', '-f',
                    '-b', self.config['github_pages']['branch'],
                    docs_dir
                ], check=True, capture_output=True, text=True)
                
                self.logger.info(f"Successfully deployed to GitHub Pages")
            except subprocess.CalledProcessError as e:
                self.logger.warning(f"GitHub Pages deployment failed: {e}")
                self.logger.info("Please ensure you have initialized a git repository and ghp-import is installed")
            
        except Exception as e:
            self.logger.error(f"Error deploying to GitHub Pages: {e}")
    
    def update_github_pages_index(self, docs_dir: str, report_type: str, filename: str):
        """Update GitHub Pages index.html with latest reports"""
        index_path = os.path.join(docs_dir, 'index.html')
        
        # Create basic index if it doesn't exist
        if not os.path.exists(index_path):
            index_content = """<!DOCTYPE html>
<html>
<head>
    <title>YenSense AI - Japan Macro & FX Intelligence</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }
        .header {
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            text-align: center;
            margin-bottom: 30px;
        }
        h1 { color: #2c3e50; }
        .reports {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
        }
        .report-card {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        .report-card h2 { color: #34495e; }
        .report-link {
            display: inline-block;
            margin: 10px 0;
            padding: 10px 20px;
            background: #3498db;
            color: white;
            text-decoration: none;
            border-radius: 5px;
        }
        .report-link:hover { background: #2980b9; }
        .timestamp { color: #7f8c8d; font-size: 0.9em; }
    </style>
</head>
<body>
    <div class="header">
        <h1>YenSense AI</h1>
        <p>Professional Japan Macro & FX Intelligence</p>
        <p class="timestamp">Updated: """ + datetime.now().strftime('%Y-%m-%d %H:%M:%S JST') + """</p>
    </div>
    <div class="reports">
        <div class="report-card">
            <h2>Daily Morning Brief</h2>
            <p>2-3 minute audio brief with Japan macro updates and FX analysis</p>
            <div id="morning-links"></div>
        </div>
        <div class="report-card">
            <h2>Weekly Strategist Report</h2>
            <p>Comprehensive analysis with interactive charts and market outlook</p>
            <div id="weekly-links"></div>
        </div>
    </div>
</body>
</html>"""
            
            with open(index_path, 'w') as f:
                f.write(index_content)
        
        # Update with latest report link (simplified for MVP)
        self.logger.info(f"GitHub Pages index updated with {report_type} report: {filename}")
    
    def schedule_jobs(self):
        """Schedule recurring jobs"""
        self.logger.info("Setting up scheduled jobs...")
        
        # Schedule daily morning brief
        daily_time = self.config['schedule']['daily_brief_time']
        schedule.every().day.at(daily_time).do(self.run_morning_brief)
        self.logger.info(f"Daily morning brief scheduled at {daily_time} JST")
        
        # Schedule weekly report
        weekly_day = self.config['schedule']['weekly_report_day']
        weekly_time = self.config['schedule']['weekly_report_time']
        getattr(schedule.every(), weekly_day).at(weekly_time).do(self.run_weekly_report)
        self.logger.info(f"Weekly report scheduled for {weekly_day}s at {weekly_time} JST")
    
    def run_scheduler(self):
        """Run the scheduler loop"""
        self.logger.info("YenSense AI scheduler started")
        self.logger.info("Press Ctrl+C to stop")
        
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
        except KeyboardInterrupt:
            self.logger.info("Scheduler stopped by user")
        except Exception as e:
            self.logger.error(f"Scheduler error: {e}", exc_info=True)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='YenSense AI - Japan Macro & FX Intelligence')
    parser.add_argument('--morning', action='store_true', help='Run morning brief now')
    parser.add_argument('--weekly', action='store_true', help='Run weekly report now')
    parser.add_argument('--fetch', action='store_true', help='Fetch data only')
    parser.add_argument('--schedule', action='store_true', help='Run scheduled jobs')
    parser.add_argument('--config', default='config.yaml', help='Config file path')
    
    args = parser.parse_args()
    
    # Initialize system
    yensense = YenSenseAI(args.config)
    
    # Execute requested action
    if args.morning:
        yensense.run_morning_brief()
    elif args.weekly:
        yensense.run_weekly_report()
    elif args.fetch:
        fetcher = DataFetcher(args.config)
        data = fetcher.fetch_all_data()
        print("Data fetched successfully!")
        import json
        print(json.dumps(data, indent=2, default=str))
    elif args.schedule:
        yensense.schedule_jobs()
        yensense.run_scheduler()
    else:
        print("YenSense AI - Japan Macro & FX Intelligence")
        print("\nUsage:")
        print("  python main.py --morning    # Run morning brief now")
        print("  python main.py --weekly     # Run weekly report now")
        print("  python main.py --fetch      # Fetch data only")
        print("  python main.py --schedule   # Start scheduler")
        print("\nFor first-time setup:")
        print("  1. Install dependencies: pip install -r requirements.txt")
        print("  2. Configure API keys in config.yaml")
        print("  3. Run: python main.py --morning")


if __name__ == "__main__":
    main()