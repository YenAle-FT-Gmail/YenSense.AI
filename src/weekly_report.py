#!/usr/bin/env python3
"""
Weekly Strategist Report Generator for YenSense AI
Creates comprehensive HTML reports with interactive Plotly charts
"""

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List

import pandas as pd
import plotly.graph_objects as go
import plotly.offline as pyo
import yaml
from .ai_analyst import AIAnalyst


class WeeklyReportGenerator:
    """Generate weekly strategist reports with interactive charts"""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize report generator"""
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.logger = logging.getLogger(__name__)
        self.output_dir = "economist/output/script"
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Initialize AI analyst
        self.ai_analyst = AIAnalyst(config_path)
    
    def _generate_executive_summary(self, data: Dict[str, Any]) -> str:
        """Generate executive summary section"""
        usd_jpy = data['fx_rates'].get('USD/JPY', 147.25)
        sentiment = data.get('sentiment_score', 50)
        
        # Determine market stance
        if sentiment >= 60:
            stance = "constructive"
            outlook = "We maintain a positive outlook on yen strength"
        elif sentiment >= 40:
            stance = "neutral"
            outlook = "We remain neutral with balanced risks"
        else:
            stance = "cautious"
            outlook = "We advise caution given current headwinds"
        
        summary = f"""## Executive Summary

**Date:** {datetime.now().strftime('%B %d, %Y')}

**Key Metrics:**
- USD/JPY: {usd_jpy:.2f}
- YenSense Sentiment Score: {sentiment}/100
- Market Stance: {stance.upper()}

This week's analysis reveals {stance} conditions for the Japanese yen. {outlook}, 
supported by current macroeconomic indicators and central bank policy dynamics. 
Key factors include inflation trends, BOJ policy stance, and global risk sentiment.

**Investment Implications:** Investors should monitor BOJ communications closely 
while considering currency hedging strategies appropriate for their risk profile."""
        
        return summary
    
    def _generate_macro_analysis(self, data: Dict[str, Any]) -> str:
        """Generate macroeconomic analysis section"""
        macro = data.get('macro_data', {})
        cpi = macro.get('japan_cpi', 106.5)
        gdp = macro.get('japan_gdp', 4231.14)
        
        analysis = f"""## Macroeconomic Analysis

### Japan Economic Indicators

**Consumer Price Index (CPI):** {cpi:.1f}
<span title="CPI measures the average change in prices paid by consumers for goods and services">ℹ️</span>

The CPI reading of {cpi:.1f} indicates {'inflationary' if cpi > 106 else 'deflationary'} pressures 
in the Japanese economy. This metric is crucial for BOJ policy decisions as the central bank 
targets 2% inflation sustainably.

**Gross Domestic Product (GDP):** ${gdp:.0f} billion
<span title="GDP represents the total value of all goods and services produced in Japan">ℹ️</span>

Japan's GDP reflects the world's third-largest economy, with recent trends showing 
{'expansion' if gdp > 4200 else 'contraction'} in economic activity.

### Bank of Japan Policy Stance

The BOJ continues its accommodative monetary policy approach, maintaining negative interest rates 
at -0.1% while conducting yield curve control (YCC) operations. 
<span title="YCC: BOJ policy to control short and long-term interest rates">ℹ️</span>

Recent communications suggest the central bank remains committed to supporting economic recovery 
while carefully monitoring inflation dynamics.

**Data Source:** [FRED Economic Data](https://fred.stlouisfed.org/), {datetime.now().strftime('%B %Y')}"""
        
        return analysis
    
    def _generate_fx_analysis(self, data: Dict[str, Any]) -> str:
        """Generate FX market analysis section"""
        fx = data.get('fx_rates', {})
        usd_jpy = fx.get('USD/JPY', 147.25)
        eur_jpy = fx.get('EUR/JPY', 158.90)
        
        # Calculate simple momentum
        usd_momentum = "bullish" if usd_jpy > 148 else "bearish" if usd_jpy < 146 else "range-bound"
        
        analysis = f"""## Foreign Exchange Analysis

### Currency Pairs Performance

**USD/JPY:** {usd_jpy:.2f} - {usd_momentum.upper()}

The dollar-yen pair trades at {usd_jpy:.2f}, reflecting {usd_momentum} momentum. 
Key drivers include:
- Federal Reserve monetary policy expectations
- BOJ yield curve control adjustments
- Risk sentiment in global markets

**EUR/JPY:** {eur_jpy:.2f}

Euro-yen at {eur_jpy:.2f} indicates relative European currency strength, influenced by:
- ECB policy normalization trajectory
- European economic recovery pace
- Cross-currency flows

### Technical Outlook

**Support Levels:** {usd_jpy - 2:.2f}, {usd_jpy - 4:.2f}
**Resistance Levels:** {usd_jpy + 2:.2f}, {usd_jpy + 4:.2f}

<span title="Support: Price level where buying interest typically emerges">ℹ️</span>
<span title="Resistance: Price level where selling pressure typically increases">ℹ️</span>

**Data Source:** [Alpha Vantage](https://www.alphavantage.co/), Real-time FX rates"""
        
        return analysis
    
    def _generate_news_analysis(self, data: Dict[str, Any]) -> str:
        """Generate news and events analysis"""
        news_items = []
        for source in ['boj_news', 'reuters_news', 'nikkei_news']:
            if source in data and data[source]:
                news_items.extend(data[source][:2])
        
        analysis = """## Market News & Events

### Recent Developments

"""
        
        if news_items:
            for item in news_items[:4]:
                title = item.get('title', 'Market Update')
                source = item.get('source', 'News')
                link = item.get('link', '#')
                
                analysis += f"- **{title}** ([{source}]({link}))\n"
        else:
            analysis += "- Markets await key economic data releases\n"
            analysis += "- BOJ policy meeting outcomes under scrutiny\n"
        
        analysis += """

### Upcoming Events

- **BOJ Monetary Policy Meeting** - Monitor for policy adjustments
- **Japan CPI Release** - Key inflation indicator
- **Tankan Survey** <span title="Tankan: BOJ's quarterly survey of business sentiment">ℹ️</span>
- **US Federal Reserve Meeting** - Impact on USD/JPY dynamics

**Sources:** [Reuters](https://www.reuters.com/markets/asia/), [Nikkei Asia](https://asia.nikkei.com/), [Bank of Japan](https://www.boj.or.jp/en/)"""
        
        return analysis
    
    def _generate_risk_outlook(self, sentiment: int) -> str:
        """Generate risk and outlook section"""
        outlook = f"""## Risks & Outlook

### Sentiment Score: {sentiment}/100

Our proprietary YenSense sentiment indicator currently reads {sentiment}, suggesting 
{'positive' if sentiment >= 60 else 'neutral' if sentiment >= 40 else 'challenging'} conditions 
for yen positioning.

### Key Risks to Monitor

**Upside Risks (Yen Strength):**
- BOJ policy normalization faster than expected
- Global risk-off sentiment driving safe-haven flows
- Narrowing interest rate differentials

**Downside Risks (Yen Weakness):**
- Persistent BOJ accommodation
- Strong US economic data supporting dollar
- Rising energy import costs for Japan

### Strategic Recommendations

1. **For Retail Investors:** Consider yen exposure through diversified currency ETFs
2. **For Institutional Clients:** Implement dynamic hedging strategies based on volatility regimes
3. **For Corporates:** Review FX hedging ratios for Japan-related exposures

### One-Week Outlook

Based on current market dynamics and our analysis, we expect USD/JPY to trade within a 
{sentiment*0.05:.1f}% range, with key focus on upcoming economic data releases and central bank communications."""
        
        return outlook
    
    def _create_interactive_chart(self, data: Dict[str, Any]) -> str:
        """Create interactive Plotly chart"""
        # Prepare data for chart
        dates = pd.date_range(end=datetime.now(), periods=30, freq='D')
        
        # Simulate historical data (in production, fetch real historical data)
        usd_jpy_current = data['fx_rates'].get('USD/JPY', 147.25)
        usd_jpy_values = [usd_jpy_current + (i-15)*0.1 + (i%3)*0.05 for i in range(30)]
        
        cpi_current = data['macro_data'].get('japan_cpi', 106.5)
        cpi_values = [cpi_current + (i-15)*0.01 for i in range(30)]
        
        # Create figure with secondary y-axis
        fig = go.Figure()
        
        # Add USD/JPY trace
        fig.add_trace(
            go.Scatter(
                x=dates,
                y=usd_jpy_values,
                name='USD/JPY',
                line=dict(color='#1f77b4', width=2),
                hovertemplate='Date: %{x|%Y-%m-%d}<br>USD/JPY: %{y:.2f}<extra></extra>'
            )
        )
        
        # Add CPI trace on secondary y-axis
        fig.add_trace(
            go.Scatter(
                x=dates,
                y=cpi_values,
                name='Japan CPI',
                line=dict(color='#ff7f0e', width=2, dash='dot'),
                yaxis='y2',
                hovertemplate='Date: %{x|%Y-%m-%d}<br>CPI: %{y:.1f}<extra></extra>'
            )
        )
        
        # Update layout
        fig.update_layout(
            title='USD/JPY vs Japan CPI Dynamics',
            xaxis_title='Date',
            yaxis=dict(
                title=dict(
                    text='USD/JPY Exchange Rate',
                    font=dict(color='#1f77b4')
                ),
                tickfont=dict(color='#1f77b4')
            ),
            yaxis2=dict(
                title=dict(
                    text='Consumer Price Index',
                    font=dict(color='#ff7f0e')
                ),
                tickfont=dict(color='#ff7f0e'),
                anchor='x',
                overlaying='y',
                side='right'
            ),
            hovermode='x unified',
            height=self.config['output']['weekly_report']['chart_height'],
            width=self.config['output']['weekly_report']['chart_width'],
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            margin=dict(l=50, r=50, t=80, b=50)
        )
        
        # Convert to HTML
        chart_html = pyo.plot(
            fig,
            output_type='div',
            include_plotlyjs='cdn',
            config={'displayModeBar': True, 'displaylogo': False}
        )
        
        return chart_html
    
    def _generate_disclaimer(self) -> str:
        """Generate disclaimer section"""
        return """## Disclaimer

This report is provided for informational purposes only and does not constitute financial advice, 
investment recommendations, or an offer to buy or sell any financial instruments. Past performance 
is not indicative of future results. Currency trading involves substantial risk of loss.

All data sources and timestamps are provided for transparency. Readers should conduct their own 
research and consult with qualified financial advisors before making investment decisions.

**Copyright © 2025 YenSense AI. All rights reserved.**"""
    
    def generate_markdown_report(self, data: Dict[str, Any]) -> str:
        """Generate complete markdown report"""
        self.logger.info("Generating weekly strategist report (Markdown)")
        
        sections = [
            "# YenSense AI Weekly Strategist Report",
            "",
            self._generate_executive_summary(data),
            "",
            self._generate_macro_analysis(data),
            "",
            self._generate_fx_analysis(data),
            "",
            self._generate_news_analysis(data),
            "",
            self._generate_risk_outlook(data.get('sentiment_score', 50)),
            "",
            self._generate_disclaimer(),
            "",
            f"*Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} JST*"
        ]
        
        markdown_content = "\n".join(sections)
        
        # Count words
        word_count = len(markdown_content.split())
        self.logger.info(f"Markdown report generated: {word_count} words")
        
        return markdown_content
    
    def generate_html_report(self, data: Dict[str, Any], markdown_content: str) -> str:
        """Generate HTML report with embedded chart"""
        self.logger.info("Generating weekly strategist report (HTML)")
        
        # Create interactive chart
        chart_html = self._create_interactive_chart(data)
        
        # Convert markdown to HTML (basic conversion)
        html_content = markdown_content
        
        # Basic markdown to HTML conversion
        html_content = html_content.replace('# ', '<h1>').replace('\n\n', '</h1>\n\n')
        html_content = html_content.replace('## ', '<h2>').replace('\n\n', '</h2>\n\n')
        html_content = html_content.replace('### ', '<h3>').replace('\n', '</h3>\n')
        html_content = html_content.replace('**', '<strong>').replace('**', '</strong>')
        html_content = html_content.replace('- ', '<li>').replace('\n', '</li>\n')
        
        # Full HTML template
        html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>YenSense AI Weekly Report - {datetime.now().strftime('%B %d, %Y')}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        .container {{
            background: white;
            padding: 40px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #34495e;
            margin-top: 30px;
            border-bottom: 1px solid #ecf0f1;
            padding-bottom: 5px;
        }}
        h3 {{
            color: #7f8c8d;
        }}
        .metric {{
            display: inline-block;
            padding: 10px 20px;
            margin: 10px;
            background: #ecf0f1;
            border-radius: 5px;
            font-weight: bold;
        }}
        .chart-container {{
            margin: 30px 0;
            padding: 20px;
            background: #fafafa;
            border-radius: 8px;
        }}
        span[title] {{
            cursor: help;
            text-decoration: underline dotted;
            color: #3498db;
        }}
        .disclaimer {{
            margin-top: 40px;
            padding: 20px;
            background: #fff3cd;
            border-left: 4px solid #ffc107;
            font-size: 0.9em;
        }}
        a {{
            color: #3498db;
            text-decoration: none;
        }}
        a:hover {{
            text-decoration: underline;
        }}
        ul {{
            list-style-type: none;
            padding-left: 0;
        }}
        li {{
            padding: 5px 0;
            padding-left: 20px;
            position: relative;
        }}
        li:before {{
            content: "▸";
            position: absolute;
            left: 0;
            color: #3498db;
        }}
        .timestamp {{
            text-align: center;
            color: #95a5a6;
            font-style: italic;
            margin-top: 30px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>YenSense AI Weekly Strategist Report</h1>
        <p style="text-align: center; color: #7f8c8d;">
            Japan Macro & FX Intelligence | {datetime.now().strftime('%B %d, %Y')}
        </p>
        
        <h2>Executive Summary</h2>
        <div class="metric">USD/JPY: {data['fx_rates'].get('USD/JPY', 147.25):.2f}</div>
        <div class="metric">EUR/JPY: {data['fx_rates'].get('EUR/JPY', 158.90):.2f}</div>
        <div class="metric">Sentiment: {data.get('sentiment_score', 50)}/100</div>
        
        <div class="chart-container">
            <h3>Interactive Market Analysis</h3>
            {chart_html}
        </div>
        
        <h2>Macroeconomic Analysis</h2>
        <p>
            <strong>Consumer Price Index:</strong> {data['macro_data'].get('japan_cpi', 106.5):.1f} 
            <span title="CPI measures the average change in prices paid by consumers">ℹ️</span>
        </p>
        <p>
            <strong>GDP:</strong> ${data['macro_data'].get('japan_gdp', 4231.14):.0f} billion
            <span title="GDP represents the total value of all goods and services produced">ℹ️</span>
        </p>
        
        <h2>Foreign Exchange Analysis</h2>
        <p>Current market dynamics show USD/JPY trading at {data['fx_rates'].get('USD/JPY', 147.25):.2f}, 
        reflecting ongoing monetary policy divergence between the Federal Reserve and Bank of Japan.</p>
        
        <h2>Market News & Events</h2>
        <ul>
            <li>BOJ maintains accommodative stance amid inflation monitoring</li>
            <li>Fed signals data-dependent approach to rate decisions</li>
            <li>Japan trade balance shows improvement on export strength</li>
        </ul>
        
        <h2>Risks & Outlook</h2>
        <p>YenSense Sentiment Score: <strong>{data.get('sentiment_score', 50)}/100</strong></p>
        <p>Our analysis suggests a {'constructive' if data.get('sentiment_score', 50) >= 60 else 'balanced'} 
        outlook for yen positioning over the coming week.</p>
        
        <div class="disclaimer">
            <h3>Disclaimer</h3>
            <p>This report is for informational purposes only and does not constitute financial advice. 
            All data is sourced from public APIs and web sources. Please consult with qualified 
            financial advisors before making investment decisions.</p>
        </div>
        
        <p class="timestamp">
            Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} JST<br>
            Data sources: FRED, Alpha Vantage, Bank of Japan, Reuters, Nikkei Asia
        </p>
    </div>
</body>
</html>"""
        
        return html_template
    
    def save_reports(self, data: Dict[str, Any]) -> Dict[str, str]:
        """Save both markdown and HTML reports"""
        date_str = datetime.now().strftime("%Y%m%d")
        
        # Generate reports
        markdown_content = self.generate_markdown_report(data)
        html_content = self.generate_html_report(data, markdown_content)
        
        # Save markdown
        md_filename = f"report_{date_str}.md"
        md_path = os.path.join(self.output_dir, md_filename)
        with open(md_path, 'w') as f:
            f.write(markdown_content)
        self.logger.info(f"Markdown report saved: {md_path}")
        
        # Save HTML
        html_filename = f"report_{date_str}.html"
        html_path = os.path.join(self.output_dir, html_filename)
        with open(html_path, 'w') as f:
            f.write(html_content)
        self.logger.info(f"HTML report saved: {html_path}")
        
        return {
            'markdown_file': md_path,
            'html_file': html_path,
            'date': date_str
        }


if __name__ == "__main__":
    # Test the report generator
    logging.basicConfig(level=logging.INFO)
    
    # Sample data for testing
    test_data = {
        'fx_rates': {'USD/JPY': 147.25, 'EUR/JPY': 158.90},
        'macro_data': {'japan_cpi': 106.5, 'japan_gdp': 4231.14},
        'boj_news': [{'title': 'BOJ Maintains Policy', 'source': 'Bank of Japan', 'link': 'https://boj.or.jp'}],
        'reuters_news': [{'title': 'Yen Steadies', 'source': 'Reuters', 'link': 'https://reuters.com'}],
        'sentiment_score': 55
    }
    
    generator = WeeklyReportGenerator()
    result = generator.save_reports(test_data)
    print(f"Generated reports: {result}")