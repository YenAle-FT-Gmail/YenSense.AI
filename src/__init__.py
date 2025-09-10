"""
YenSense AI - Japan Macro & FX Intelligence
Professional-grade analysis tool for Japan macroeconomic and foreign exchange markets
"""

from .main import YenSenseAI
from .data_fetcher import DataFetcher
from .morning_brief import MorningBriefGenerator
from .weekly_report import WeeklyReportGenerator
from .ai_analyst import AIAnalyst

__version__ = "1.0.0"
__all__ = [
    "YenSenseAI",
    "DataFetcher", 
    "MorningBriefGenerator",
    "WeeklyReportGenerator",
    "AIAnalyst"
]