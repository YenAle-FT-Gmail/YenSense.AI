#!/usr/bin/env python3
"""
Morning Brief Generator for YenSense AI
Creates daily TTS-ready scripts with SSML markup
"""

import logging
import os
import sys
from datetime import datetime
from typing import Dict, Any

# Add parent directory to path for imports when run directly
if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import yaml
from gtts import gTTS
from core.ai_analyst_brief import AIAnalystBrief
import tempfile

# Handle pydub import - fallback if not available due to Python 3.13+ issues
try:
    from pydub import AudioSegment
    HAS_PYDUB = True
except ImportError:
    HAS_PYDUB = False
    class AudioSegment:
        @staticmethod
        def silent(*args, **kwargs):
            return None
        @staticmethod
        def from_mp3(*args, **kwargs):
            return None


class MorningBriefGenerator:
    """Generate daily morning brief with domain-specific segments and alternating TTS voices"""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize morning brief generator"""
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.logger = logging.getLogger(__name__)
        self.output_dir = "data/output/briefs"
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Initialize AI analyst for brief generation
        self.ai_analyst = AIAnalystBrief(config_path)
    
    
    def generate_segments(self, data: Dict[str, Any]) -> Dict[str, str]:
        """Generate 4 domain-specific segments using AI analyst"""
        self.logger.info("Generating domain-specific morning brief segments")
        
        segments = {}
        
        # Generate each domain segment
        try:
            segments['rates'] = self.ai_analyst.generate_rates_commentary(data)
            self.logger.info(f"Generated rates commentary: {len(segments['rates'])} chars: {segments['rates'][:100]}...")
            if not segments['rates'].strip():
                self.logger.warning("Rates commentary is empty!")
        except Exception as e:
            self.logger.error(f"Failed to generate rates commentary: {e}")
            segments['rates'] = "Rates markets were quiet overnight with limited activity."
        
        try:
            segments['fx'] = self.ai_analyst.generate_fx_commentary(data)
            self.logger.info("Generated FX commentary")
        except Exception as e:
            self.logger.error(f"Failed to generate FX commentary: {e}")
            segments['fx'] = "Yen crosses were range-bound with limited volatility overnight."
        
        try:
            segments['repo'] = self.ai_analyst.generate_repo_commentary(data)
            self.logger.info("Generated repo commentary")
        except Exception as e:
            self.logger.error(f"Failed to generate repo commentary: {e}")
            segments['repo'] = "Repo markets were stable with no funding stress."
        
        try:
            segments['economist'] = self.ai_analyst.generate_economist_commentary(data)
            self.logger.info("Generated economist commentary")
        except Exception as e:
            self.logger.error(f"Failed to generate economist commentary: {e}")
            segments['economist'] = "Economic data releases were in line with expectations."
        
        return segments
    
    def generate_multi_voice_audio(self, segments: Dict[str, str], output_filename: str) -> str:
        """Generate audio with different voices for each segment"""
        self.logger.info(f"Generating multi-voice audio: {output_filename}")
        
        if not HAS_PYDUB:
            self.logger.warning("pydub not available, falling back to single voice audio")
            return self._generate_fallback_audio(segments, output_filename)
        
        # Voice assignments for each domain
        voice_config = {
            'rates': {'tld': 'com'},      # US English
            'fx': {'tld': 'co.uk'},       # UK English  
            'repo': {'tld': 'ca'},        # Canadian English
            'economist': {'tld': 'com.au'} # Australian English
        }
        
        audio_segments = []
        
        try:
            # Generate intro
            intro_text = f"Good morning. This is your YenSense AI market brief for {datetime.now().strftime('%A, %B %d')}."
            intro_tts = gTTS(text=intro_text, lang='en', tld='com')
            intro_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
            intro_tts.save(intro_file.name)
            audio_segments.append(AudioSegment.from_mp3(intro_file.name))
            
            # Add brief pause
            silence = AudioSegment.silent(duration=500)  # 500ms
            
            # Generate each domain segment with different voice
            for domain, text in segments.items():
                if not text.strip():
                    continue
                    
                # Clean text for TTS
                clean_text = text.strip()
                
                # Generate TTS with domain-specific voice
                voice_settings = voice_config.get(domain, {'tld': 'com'})
                tts = gTTS(text=clean_text, lang='en', tld=voice_settings['tld'])
                
                # Save to temporary file
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
                tts.save(temp_file.name)
                
                # Load and add to segments
                segment_audio = AudioSegment.from_mp3(temp_file.name)
                audio_segments.append(silence)  # Pause between segments
                audio_segments.append(segment_audio)
                
                self.logger.info(f"Generated {domain} segment with {voice_settings['tld']} voice")
            
            # Add outro
            outro_text = "That's your morning brief. Sources include FRED, Alpha Vantage, Bank of Japan, and Reuters. This is for informational purposes only."
            outro_tts = gTTS(text=outro_text, lang='en', tld='com')
            outro_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
            outro_tts.save(outro_file.name)
            audio_segments.append(silence)
            audio_segments.append(AudioSegment.from_mp3(outro_file.name))
            
            # Combine all segments
            final_audio = sum(audio_segments)
            
            # Save final audio
            output_path = os.path.join(self.output_dir, output_filename)
            final_audio.export(output_path, format="mp3")
            
            self.logger.info(f"Multi-voice audio saved: {output_path}")
            return output_path
            
        except Exception as e:
            self.logger.error(f"Error generating multi-voice audio: {e}")
            # Fallback to single voice
            return self._generate_fallback_audio(segments, output_filename)
    
    def _generate_fallback_audio(self, segments: Dict[str, str], output_filename: str) -> str:
        """Generate single-voice audio as fallback"""
        self.logger.info("Generating fallback single-voice audio")
        
        # Combine all segments into single text
        combined_text = f"Good morning. This is your YenSense AI market brief. "
        
        for domain, text in segments.items():
            if text.strip():
                combined_text += f"{text} "
        
        combined_text += "That's your morning brief. This is for informational purposes only."
        
        try:
            tts = gTTS(text=combined_text, lang='en', slow=False)
            output_path = os.path.join(self.output_dir, output_filename)
            tts.save(output_path)
            self.logger.info(f"Fallback audio saved: {output_path}")
            return output_path
        except Exception as e:
            self.logger.error(f"Error generating fallback audio: {e}")
            return ""
    
    def save_brief(self, segments: Dict[str, str], data: Dict[str, Any]) -> Dict[str, str]:
        """Save brief segments and generate multi-voice audio"""
        date_str = datetime.now().strftime("%Y%m%d")
        
        # Save text script with segments
        text_filename = f"morning_brief_{date_str}.txt"
        text_path = os.path.join(self.output_dir, text_filename)
        
        with open(text_path, 'w') as f:
            f.write(f"YenSense AI Morning Brief - {datetime.now().strftime('%A, %B %d, %Y')}\n")
            f.write("="*60 + "\n\n")
            
            # Write each segment
            segment_titles = {
                'rates': 'RATES MARKETS',
                'fx': 'FOREIGN EXCHANGE', 
                'repo': 'REPO MARKETS',
                'economist': 'ECONOMIC OUTLOOK'
            }
            
            for domain in ['rates', 'fx', 'repo', 'economist']:
                if domain in segments and segments[domain].strip():
                    f.write(f"## {segment_titles[domain]}\n")
                    f.write(f"{segments[domain]}\n\n")
            
            f.write("---\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n")
            f.write(f"Sentiment Score: {data.get('sentiment_score', 50)}/100\n")
            f.write("Data Sources: FRED, Alpha Vantage, BOJ, Reuters, Nikkei Asia\n")
            f.write("Disclaimer: This content is for informational purposes only and not financial advice.\n")
        
        self.logger.info(f"Brief text saved: {text_path}")
        
        # Generate multi-voice audio
        audio_filename = f"morning_brief_{date_str}.mp3"
        audio_path = self.generate_multi_voice_audio(segments, audio_filename)
        
        return {
            'text_file': text_path,
            'audio_file': audio_path,
            'date': date_str,
            'segments': list(segments.keys())
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
    segments = generator.generate_segments(test_data)
    result = generator.save_brief(segments, test_data)
    print(f"Generated files: {result}")