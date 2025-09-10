#!/usr/bin/env python3
"""
AI-Powered Market Analysis Engine for YenSense AI
Uses LLM to generate intelligent market commentary and insights
"""

import logging
from typing import Dict, Any, Optional

import requests
import yaml


class AIAnalyst:
    """AI-powered market analyst using LLM for intelligent commentary"""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize AI analyst with configuration"""
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.logger = logging.getLogger(__name__)
        self.api_key = self.config['api_keys'].get('openai')
        
        if not self.api_key or self.api_key == "YOUR_OPENAI_API_KEY":
            self.logger.warning("OpenAI API key not configured - using fallback analysis")
            self.use_ai = False
        else:
            self.use_ai = True
    
    def _call_openai(self, prompt: str, max_tokens: int = 1000) -> str:
        """Call OpenAI API for analysis"""
        if not self.use_ai:
            return self._fallback_analysis()
        
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        data = {
            'model': 'gpt-5-mini',
            'messages': [
                {
                    'role': 'system',
                    'content': '''You are a senior Japan macro and FX strategist at a major investment bank. 
                    You provide professional, insightful market analysis with specific data interpretation, 
                    historical context, and forward-looking views. Your analysis is sophisticated but 
                    accessible to both institutional and retail clients.'''
                },
                {
                    'role': 'user',
                    'content': prompt
                }
            ],
            'max_tokens': max_tokens,
            'temperature': 0.7
        }
        
        try:
            response = requests.post(
                'https://api.openai.com/v1/chat/completions',
                headers=headers,
                json=data,
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            return result['choices'][0]['message']['content'].strip()
            
        except Exception as e:
            self.logger.error(f"OpenAI API error: {e}")
            return self._fallback_analysis()
    
    def _fallback_analysis(self) -> str:
        """Fallback analysis when AI is unavailable"""
        return """Market conditions remain in focus as investors monitor central bank policy 
        divergence between the Fed and BOJ. Current data suggests cautious positioning 
        with attention to inflation trends and policy communications."""
    
    def analyze_fx_movements(self, fx_data: Dict[str, float], historical_data: Optional[Dict] = None) -> str:
        """Generate AI analysis of FX market movements"""
        usd_jpy = fx_data.get('USD/JPY', 147.25)
        eur_jpy = fx_data.get('EUR/JPY', 158.90)
        
        prompt = f"""
        Analyze the current FX market conditions for Japan:
        
        Current Rates:
        - USD/JPY: {usd_jpy}
        - EUR/JPY: {eur_jpy}
        
        Provide a 2-3 sentence professional analysis covering:
        1. What these levels indicate about yen strength/weakness
        2. Key drivers (policy divergence, risk sentiment, etc.)
        3. Near-term outlook or levels to watch
        
        Write for a mixed audience of institutional and sophisticated retail investors.
        """
        
        return self._call_openai(prompt, max_tokens=300)
    
    def analyze_macro_data(self, macro_data: Dict[str, Any]) -> str:
        """Generate AI analysis of macroeconomic indicators"""
        cpi = macro_data.get('japan_cpi', 106.5)
        gdp = macro_data.get('japan_gdp', 562987.8)
        
        prompt = f"""
        Analyze Japan's current macroeconomic indicators:
        
        Key Data:
        - Consumer Price Index: {cpi}
        - GDP: ${gdp} billion
        
        Provide a professional 3-4 sentence analysis covering:
        1. What this CPI level means for BOJ policy (they target 2% inflation)
        2. GDP implications for economic health
        3. How these factors influence yen outlook
        4. Policy implications or market expectations
        
        Include context about BOJ's inflation targeting and current policy stance.
        """
        
        return self._call_openai(prompt, max_tokens=400)
    
    def analyze_news_sentiment(self, news_data: Dict[str, Any]) -> str:
        """Generate AI analysis of news sentiment and implications"""
        # Collect all news headlines
        headlines = []
        for source in ['boj_news', 'reuters_news', 'nikkei_news']:
            if source in news_data and isinstance(news_data[source], list):
                for item in news_data[source][:2]:  # Top 2 from each source
                    if isinstance(item, dict):
                        headlines.append(f"- {item.get('title', '')} ({item.get('source', '')})")
        
        headlines_text = "\n".join(headlines) if headlines else "No major headlines available"
        
        prompt = f"""
        Analyze the current news sentiment for Japan markets:
        
        Recent Headlines:
        {headlines_text}
        
        Provide a 2-3 sentence analysis of:
        1. Overall sentiment toward Japan/yen from these headlines
        2. Any policy or economic implications
        3. Market positioning or risk factors to consider
        
        If headlines are limited, focus on general market themes affecting Japan.
        """
        
        return self._call_openai(prompt, max_tokens=300)
    
    def generate_morning_commentary(self, all_data: Dict[str, Any]) -> Dict[str, str]:
        """Generate comprehensive morning brief commentary"""
        self.logger.info("Generating AI-powered morning commentary")
        
        # Generate each section with AI analysis
        fx_analysis = self.analyze_fx_movements(all_data.get('fx_rates', {}))
        macro_analysis = self.analyze_macro_data(all_data.get('macro_data', {}))
        news_analysis = self.analyze_news_sentiment(all_data)
        
        # Generate outlook and sentiment
        sentiment_score = all_data.get('sentiment_score', 50)
        outlook_prompt = f"""
        Based on current Japan market conditions, provide a 2-sentence outlook:
        - Current sentiment score: {sentiment_score}/100
        - Key factors: FX positioning, macro data, policy expectations
        
        What should investors watch for today/this week?
        """
        outlook = self._call_openai(outlook_prompt, max_tokens=200)
        
        return {
            'fx_commentary': fx_analysis,
            'macro_commentary': macro_analysis,
            'news_commentary': news_analysis,
            'market_outlook': outlook
        }
    
    def generate_weekly_analysis(self, all_data: Dict[str, Any]) -> Dict[str, str]:
        """Generate comprehensive weekly strategist analysis"""
        self.logger.info("Generating AI-powered weekly analysis")
        
        fx_data = all_data.get('fx_rates', {})
        macro_data = all_data.get('macro_data', {})
        sentiment = all_data.get('sentiment_score', 50)
        
        # Executive summary
        exec_prompt = f"""
        Write an executive summary for a weekly Japan FX/macro strategist report:
        
        Current Conditions:
        - USD/JPY: {fx_data.get('USD/JPY', 147.25)}
        - Japan CPI: {macro_data.get('japan_cpi', 106.5)}
        - GDP: ${macro_data.get('japan_gdp', 562987.8)} billion
        - Market sentiment: {sentiment}/100
        
        Provide a 3-4 sentence professional summary with:
        1. Current market stance (bullish/bearish/neutral on yen)
        2. Key supporting factors
        3. Primary risks to monitor
        4. Investment implications
        
        Write for institutional clients.
        """
        
        executive_summary = self._call_openai(exec_prompt, max_tokens=400)
        
        # Detailed market analysis
        detailed_prompt = f"""
        Provide detailed weekly market analysis for Japan:
        
        Data Points:
        - USD/JPY: {fx_data.get('USD/JPY', 147.25)}
        - CPI: {macro_data.get('japan_cpi', 106.5)}
        - GDP: ${macro_data.get('japan_gdp', 562987.8)} billion
        
        Write 4-5 sentences covering:
        1. Technical and fundamental FX outlook
        2. Monetary policy implications (BOJ vs Fed)
        3. Key economic themes and data to watch
        4. Risk factors (global growth, geopolitics, etc.)
        5. Strategic recommendations
        
        Professional tone for sophisticated investors.
        """
        
        detailed_analysis = self._call_openai(detailed_prompt, max_tokens=600)
        
        # Risk assessment
        risk_prompt = f"""
        Assess key risks for Japan/yen positioning this week:
        
        Current sentiment: {sentiment}/100
        Market conditions: USD/JPY {fx_data.get('USD/JPY', 147.25)}
        
        Identify 3 key risks:
        1. Upside risks (what could strengthen yen)
        2. Downside risks (what could weaken yen)  
        3. Policy/event risks to monitor
        
        2-3 sentences total.
        """
        
        risk_assessment = self._call_openai(risk_prompt, max_tokens=300)
        
        return {
            'executive_summary': executive_summary,
            'detailed_analysis': detailed_analysis,
            'risk_assessment': risk_assessment
        }


if __name__ == "__main__":
    # Test the AI analyst
    logging.basicConfig(level=logging.INFO)
    
    # Sample data for testing
    test_data = {
        'fx_rates': {'USD/JPY': 147.25, 'EUR/JPY': 158.90},
        'macro_data': {'japan_cpi': 106.5, 'japan_gdp': 562987.8},
        'boj_news': [{'title': 'BOJ Maintains Policy Stance', 'source': 'Bank of Japan'}],
        'sentiment_score': 55
    }
    
    analyst = AIAnalyst()
    
    # Test morning commentary
    morning_analysis = analyst.generate_morning_commentary(test_data)
    print("=== Morning Commentary ===")
    for key, value in morning_analysis.items():
        print(f"{key}: {value}\n")
    
    # Test weekly analysis
    weekly_analysis = analyst.generate_weekly_analysis(test_data)
    print("=== Weekly Analysis ===")
    for key, value in weekly_analysis.items():
        print(f"{key}: {value}\n")