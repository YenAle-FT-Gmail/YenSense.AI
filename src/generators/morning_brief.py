#!/usr/bin/env python3
"""
Morning Brief Generator for YenSense AI
Creates daily TTS-ready scripts with SSML markup
"""

import logging
import os
from datetime import datetime
from typing import Dict, Any

import yaml
from gtts import gTTS
from core.ai_analyst import AIAnalyst


class MorningBriefGenerator:
    """Generate daily morning meeting scripts with TTS"""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize morning brief generator"""
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.logger = logging.getLogger(__name__)
        self.output_dir = "data/output/briefs"
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Initialize AI analyst
        self.ai_analyst = AIAnalyst(config_path)
    
    def _format_number(self, number: float, decimals: int = 2) -> str:
        """Format number for speech"""
        if number >= 1000:
            return f"{number:,.{decimals}f}"
        return f"{number:.{decimals}f}"
    
    def _generate_greeting(self) -> str:
        """Generate morning greeting with date"""
        now = datetime.now()
        day_name = now.strftime("%A")
        date_str = now.strftime("%B %d, %Y")
        
        greeting = f"""<speak>
Good morning, and welcome to today's YenSense AI morning brief.
<break time="500ms"/>
It's {day_name}, {date_str}, and I'm here with your Japan macro and FX update.
<break time="700ms"/>
</speak>"""
        return greeting
    
    def _generate_fx_section(self, fx_data: Dict[str, float], ai_commentary: str) -> str:
        """Generate AI-powered FX market commentary"""
        usd_jpy = fx_data.get('USD/JPY', 147.25)
        eur_jpy = fx_data.get('EUR/JPY', 158.90)
        
        fx_section = f"""<speak>
Let's start with the foreign exchange markets.
<break time="500ms"/>
Dollar-yen is currently trading at {self._format_number(usd_jpy)}, 
and Euro-yen is at {self._format_number(eur_jpy)}.
<break time="500ms"/>
{ai_commentary}
<break time="700ms"/>
For our retail listeners, this means it takes about {int(usd_jpy)} yen to buy one US dollar.
<break time="700ms"/>
</speak>"""
        return fx_section
    
    def _generate_macro_section(self, macro_data: Dict[str, Any], ai_commentary: str) -> str:
        """Generate AI-powered macro economic commentary"""
        cpi = macro_data.get('japan_cpi', 106.5)
        gdp = macro_data.get('japan_gdp', 4231.14)
        
        macro_section = f"""<speak>
Moving to Japan's macroeconomic indicators.
<break time="500ms"/>
The Consumer Price Index stands at {self._format_number(cpi, 1)}, 
and Japan's GDP is approximately {self._format_number(gdp, 0)} billion dollars.
<break time="500ms"/>
{ai_commentary}
<break time="700ms"/>
</speak>"""
        return macro_section
    
    def _generate_news_section(self, all_data: Dict[str, Any], ai_commentary: str) -> str:
        """Generate AI-powered news summary section"""        
        news_section = f"""<speak>
Now for today's market news and analysis.
<break time="500ms"/>
{ai_commentary}
<break time="700ms"/>
</speak>"""
        return news_section
    
    def _generate_sentiment_section(self, sentiment_score: int, ai_outlook: str) -> str:
        """Generate AI-powered sentiment analysis and outlook"""        
        sentiment_section = f"""<speak>
Our proprietary YenSense sentiment indicator stands at {sentiment_score} out of 100.
<break time="500ms"/>
{ai_outlook}
<break time="700ms"/>
</speak>"""
        return sentiment_section
    
    def _generate_closing(self) -> str:
        """Generate closing remarks"""
        closing = """<speak>
That concludes today's YenSense AI morning brief.
<break time="500ms"/>
Remember, this analysis is for informational purposes only and not financial advice.
<break time="500ms"/>
For detailed analysis and interactive charts, 
visit our weekly strategist report on YenSense AI's website.
<break time="700ms"/>
Have a productive trading day, and we'll see you tomorrow.
<break time="500ms"/>
Sources for today's data include: 
FRED Economic Data, Alpha Vantage, Bank of Japan, Reuters, and Nikkei Asia.
</speak>"""
        return closing
    
    def generate_script(self, data: Dict[str, Any]) -> str:
        """Generate complete morning brief script with AI analysis"""
        self.logger.info("Generating AI-powered morning brief script")
        
        # Get AI-powered commentary
        ai_commentary = self.ai_analyst.generate_morning_commentary(data)
        
        # Build script sections with AI insights
        script_parts = [
            self._generate_greeting(),
            self._generate_fx_section(data.get('fx_rates', {}), ai_commentary['fx_commentary']),
            self._generate_macro_section(data.get('macro_data', {}), ai_commentary['macro_commentary']),
            self._generate_news_section(data, ai_commentary['news_commentary']),
            self._generate_sentiment_section(data.get('sentiment_score', 50), ai_commentary['market_outlook']),
            self._generate_closing()
        ]
        
        # Combine all parts
        full_script = "\n".join(script_parts)
        
        # Also create plain text version (without SSML tags)
        plain_script = full_script
        for tag in ['<speak>', '</speak>', '<break time="500ms"/>', '<break time="700ms"/>']:
            plain_script = plain_script.replace(tag, '')
        plain_script = ' '.join(plain_script.split())  # Clean up whitespace
        
        # Calculate reading time
        word_count = len(plain_script.split())
        wpm = self.config['output']['morning_brief']['target_wpm']
        duration_minutes = word_count / wpm
        
        self.logger.info(f"Script generated: {word_count} words, ~{duration_minutes:.1f} minutes")
        
        return full_script
    
    def generate_tts(self, script: str, output_filename: str) -> str:
        """Generate TTS audio file from script"""
        self.logger.info(f"Generating TTS audio: {output_filename}")
        
        # Remove SSML tags for gTTS (it doesn't support SSML)
        plain_text = script
        for tag in ['<speak>', '</speak>', '<break time="500ms"/>', '<break time="700ms"/>']:
            plain_text = plain_text.replace(tag, ' ')
        plain_text = ' '.join(plain_text.split())
        
        # Generate TTS
        try:
            tts = gTTS(text=plain_text, lang='en', slow=False)
            audio_path = os.path.join(self.output_dir, output_filename)
            tts.save(audio_path)
            self.logger.info(f"TTS audio saved: {audio_path}")
            return audio_path
        except Exception as e:
            self.logger.error(f"Error generating TTS: {e}")
            return ""
    
    def save_script(self, script: str, data: Dict[str, Any]) -> Dict[str, str]:
        """Save script and generate audio"""
        date_str = datetime.now().strftime("%Y%m%d")
        
        # Save text script
        text_filename = f"morning_brief_{date_str}.txt"
        text_path = os.path.join(self.output_dir, text_filename)
        
        with open(text_path, 'w') as f:
            f.write(script)
            f.write("\n\n---\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n")
            f.write(f"Sentiment Score: {data.get('sentiment_score', 50)}/100\n")
            f.write("Data Sources: FRED, Alpha Vantage, BOJ, Reuters, Nikkei Asia\n")
            f.write("Disclaimer: This content is for informational purposes only and not financial advice.\n")
        
        self.logger.info(f"Script saved: {text_path}")
        
        # Generate audio
        audio_filename = f"morning_brief_{date_str}.mp3"
        audio_path = self.generate_tts(script, audio_filename)
        
        return {
            'text_file': text_path,
            'audio_file': audio_path,
            'date': date_str
        }


if __name__ == "__main__":
    # Test the morning brief generator
    logging.basicConfig(level=logging.INFO)
    
    # Sample data for testing
    test_data = {
        'fx_rates': {'USD/JPY': 147.25, 'EUR/JPY': 158.90},
        'macro_data': {'japan_cpi': 106.5, 'japan_gdp': 4231.14},
        'boj_news': [{'title': 'BOJ Maintains Policy Stance', 'source': 'Bank of Japan'}],
        'reuters_news': [{'title': 'Yen Steadies After Recent Volatility', 'source': 'Reuters'}],
        'sentiment_score': 55
    }
    
    generator = MorningBriefGenerator()
    script = generator.generate_script(test_data)
    result = generator.save_script(script, test_data)
    print(f"Generated files: {result}")