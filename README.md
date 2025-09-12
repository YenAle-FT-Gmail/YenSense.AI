# YenSense AI - Japan Macro & FX Intelligence Platform

Professional-grade Japan market analysis powered by an 8-stage AI reasoning pipeline that mimics how real analysts think. Generates daily morning briefs and weekly strategist reports with true analytical depth, not just data summaries.

## 🚀 Key Innovation: Multi-Stage AI Pipeline

Unlike simple data summarizers, YenSense AI uses a sophisticated 8-stage reasoning pipeline:

1. **Data Collection** - Fetches FX rates, macro indicators, news from multiple sources
2. **Initial Summary** - AI generates factual summary of market events  
3. **Evidence Gathering** - AI identifies and fetches additional needed evidence
4. **Gap Identification** - AI finds questions, contradictions, gaps in understanding
5. **Reasoning** - AI determines what analysis would answer the questions
6. **Calculation** - AI performs actual calculations and analysis
7. **Validation** - AI validates conclusions for logical consistency
8. **Report Generation** - Multi-sub-stage report creation with dynamic titling

This approach produces evidence-based analysis where AI questions its assumptions, seeks additional data, and validates conclusions - just like a human analyst.

## Features

- **Daily Morning Brief**: Domain-specific podcast with multi-voice TTS covering rates, FX, repo, and economic outlook
- **Weekly Strategist Report**: Comprehensive HTML report with interactive Plotly charts, multi-stage AI analysis
- **Real-time Data Integration**: 
  - **FRED**: US Treasury curve, FX rates, macro data (authoritative source for US rates)
  - **JBOND**: Complete JGB yield curve 3M-40Y (authoritative source for JGB rates)  
  - **Tokyo Tanshi**: Repo rates, TONA, funding conditions
  - **Trading Economics**: Economic calendar with 2-month forward visibility via Selenium web scraping
  - **BOJ/Reuters/Nikkei**: Policy updates and market news
- **AI-Powered Analysis**: OpenAI GPT-5-mini for intelligent market insights
- **Sentiment Analysis**: Dynamic sentiment scoring based on multiple factors
- **Automated Scheduling**: Configurable daily and weekly report generation
- **GitHub Pages Deployment**: Optional automatic deployment to web

## Quick Start

### Prerequisites

- Python 3.11 or higher
- Chrome browser (for Selenium web scraping)
- ChromeDriver (automatically managed by webdriver-manager)
- Git (for GitHub Pages deployment)
- Internet connection for data fetching

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/YenSense.AI.git
cd YenSense.AI
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

Or create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Configuration

1. Edit `config.yaml` and add your API keys:

```yaml
api_keys:
  openai: "YOUR_OPENAI_KEY"       # REQUIRED - Get from https://platform.openai.com/api-keys
  alpha_vantage: "YOUR_KEY_HERE"  # Get from https://www.alphavantage.co/support/#api-key
  fred: "YOUR_KEY_HERE"           # Get from https://fred.stlouisfed.org/docs/api/api_key.html
  finnhub: "YOUR_KEY_HERE"        # Optional - Get from https://finnhub.io/register
```

**Important**: OpenAI API key is required for the AI analysis pipeline. The system uses GPT-4o-mini for reliable, cost-effective analysis.

### Usage

#### Generate Morning Brief (One-time)
```bash
python main.py --morning
```
Output files:
- `data/output/briefs/morning_brief_YYYYMMDD.txt` - SSML script
- `data/output/briefs/morning_brief_YYYYMMDD.mp3` - Audio file

#### Generate Weekly Report (One-time)
```bash
python main.py --weekly
```
This uses the new 8-stage AI pipeline to generate in-depth analysis.

Output files:
- `data/output/reports/report_YYYYMMDD.md` - Markdown report
- `data/output/reports/report_YYYYMMDD.html` - Interactive HTML report
- `pipeline_context_YYYYMMDD.json` - Debug context from pipeline execution

#### Test the AI Pipeline
```bash
python tests/test_pipeline.py
```
This runs the complete 8-stage pipeline and outputs diagnostic information.

#### Fetch Data Only
```bash
python main.py --fetch
```

#### Run Scheduled Jobs
```bash
python main.py --schedule
```
This will run:
- Daily morning brief at 10:00 AM JST
- Weekly report every Monday at 10:00 AM JST

Press `Ctrl+C` to stop the scheduler.

## Project Structure

```
YenSense.AI/
├── src/                          # All source code
│   ├── core/                     # Core business logic
│   │   ├── ai_analyst_base.py   # Shared OpenAI utilities
│   │   ├── ai_analyst_brief.py  # Morning brief AI generation
│   │   ├── ai_analyst_report.py # Weekly report AI generation
│   │   └── data_fetcher.py      # Data source integrations
│   ├── generators/               # Report generators
│   │   ├── morning_brief.py     # Daily brief generator
│   │   └── weekly_report.py     # Weekly report generator
│   ├── pipeline/                 # 8-stage AI analysis pipeline
│   │   ├── orchestrator.py      # Pipeline controller
│   │   ├── context.py           # Context passing between stages
│   │   └── stages/              # Individual stage implementations
│   └── main.py                  # Main orchestration
├── tests/                        # Test suite
├── docs/                         # GitHub Pages web interface
├── data/                         # All data storage
│   ├── input/                   # Cached data by domain
│   │   ├── fx/                  # FX rates cache
│   │   ├── macro/               # Macroeconomic data cache
│   │   ├── economist/           # Economic analysis data cache
│   │   ├── news/                # News data cache
│   │   └── repo/                # Repurchase agreement market data
│   └── output/
│       ├── briefs/              # Daily morning brief outputs
│       └── reports/             # Weekly strategist report outputs
├── logs/                         # Application logs
├── config.yaml                   # Configuration (root level)
├── main.py                       # Entry point
└── requirements.txt              # Dependencies
```

**Note**: The `repo/` directory refers to **repurchase agreement markets** data, not code repositories.

## Data Sources

- **Foreign Exchange**: Alpha Vantage (USD/JPY, EUR/JPY)
- **Macroeconomic Data**: FRED (CPI, GDP, US Treasury rates)
- **Economic Calendar**: Trading Economics (G3 economic events, bond auctions) via Selenium web scraping
- **JGB Rates**: JBOND (complete yield curve 3M-40Y)
- **Repo Markets**: Tokyo Tanshi (funding rates, TONA)
- **Japan Policy**: Bank of Japan website
- **Market News**: Reuters RSS, Nikkei Asia
- **Additional Sources**: Configurable via config.yaml

## How the AI Pipeline Works

### Pipeline Execution Flow
1. **Data Collection**: Fetches current FX rates, macro data, news
2. **Initial Summary**: AI creates factual summary of market events
3. **Evidence Gathering**: AI identifies what additional data is needed and fetches it
4. **Gap Identification**: AI finds contradictions and unanswered questions
5. **Reasoning**: AI determines what analysis would answer the questions
6. **Calculation**: AI performs actual calculations and statistical analysis
7. **Validation**: AI critiques its own conclusions for logical consistency
8. **Report Generation**: Creates report with dynamic title based on findings

### AI Analysis Features
- **Self-Questioning**: AI identifies what it doesn't understand
- **Evidence-Based**: Must support conclusions with specific data
- **Self-Validation**: AI acts as its own critic
- **Dynamic Content**: Report focus changes based on market conditions

## Customization

### Modify Report Content
Edit the generator modules in `src/`:
- `src/generators/morning_brief.py` - Customize morning brief sections
- `src/generators/weekly_report.py` - Modify report structure and charts
- `src/pipeline/stages/` - Customize individual pipeline stages

### Add New Data Sources
1. Update `src/core/data_fetcher.py` with new fetch methods
2. Add configuration in `config.yaml`
3. Integrate into pipeline stages or report generators

### Change Schedule
Edit `config.yaml`:
```yaml
schedule:
  daily_brief_time: "10:00"  # 24-hour format
  weekly_report_day: "monday"
  weekly_report_time: "10:00"
  timezone: "Asia/Tokyo"
```

## GitHub Pages Deployment

1. Initialize git repository:
```bash
git init
git add .
git commit -m "Initial commit"
```

2. Create GitHub repository and push:
```bash
git remote add origin https://github.com/yourusername/YenSense.AI.git
git push -u origin main
```

3. Enable GitHub Pages deployment in config.yaml:
```yaml
github_pages:
  enabled: true
  branch: "gh-pages"
  directory: "docs"
```

4. Reports will auto-deploy when generated

## Testing

```bash
# Test the complete AI pipeline
python tests/test_pipeline.py

# Run with specific stages only
python -c "from src.pipeline.orchestrator import AnalysisPipeline; p = AnalysisPipeline(); p.run_partial(['DataCollectionStage', 'InitialSummaryStage'])"
```

## Troubleshooting

### OpenAI API Errors
- Ensure OpenAI API key is set in config.yaml
- **CRITICAL**: Model must be `gpt-5-mini` - DO NOT CHANGE this model name
- GPT-5-mini requires `max_completion_tokens` (not `max_tokens`)
- GPT-5-mini doesn't support custom temperature settings

### No Audio File Generated
- Ensure `gtts` is installed: `pip install gtts`
- Check internet connection (gTTS requires internet)

### API Rate Limits
- Add delays between requests in config.yaml
- Use cached data when limits are reached

### Missing Data
- Check `logs/system.log` for errors
- Verify API keys are correct in `config.yaml`
- Ensure internet connectivity
- Review pipeline context JSON files for debugging

## Support

For issues or questions:
1. Check the logs in `logs/system.log`
2. Review configuration in `config.yaml`
3. Ensure all dependencies are installed

## Disclaimer

This tool is for informational purposes only and does not constitute financial advice. Always consult with qualified financial professionals before making investment decisions.

## License

MIT License - See LICENSE file for details

## Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues for bugs and feature requests.

---

**YenSense AI** - Professional Japan Macro & FX Intelligence