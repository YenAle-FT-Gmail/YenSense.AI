#!/usr/bin/env python3
"""
Morning Brief AI Analyst
Generates domain-specific market commentary for daily podcasts
"""

import logging
from typing import Dict, Any

from .ai_analyst_base import AIAnalystBase


class AIAnalystBrief(AIAnalystBase):
    """AI analyst specialized for morning brief generation"""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize brief analyst"""
        super().__init__(config_path)
        
        # Brief-specific system prompt
        self.brief_system_prompt = '''You are a seasoned Japan markets trader doing a morning podcast. 
        Your audience includes professional traders, institutional clients, and sophisticated retail investors.
        
        Style: Conversational but knowledgeable. Focus on actionable market color - what happened yesterday, 
        why it happened, and what to watch today. Be specific about levels, events, and catalysts.
        
        Avoid: Generic market-speak, unnecessary hedging, or filler content. If nothing notable happened, 
        just say so briefly. Don't pad analysis where there isn't any.'''
    
    def generate_rates_commentary(self, data: Dict[str, Any]) -> str:
        """Generate rates market commentary for morning brief"""
        
        # Extract relevant data
        macro_data = data.get('macro_data', {})
        fx_data = data.get('fx_rates', {})
        headlines = self._extract_headlines(data, limit=3)
        
        # Get JGB and US Treasury data if available
        jgb_10y = macro_data.get('jgb_10y', 0.25)  # Placeholder
        us_10y = macro_data.get('us_10y', 4.25)   # Placeholder
        
        headline_text = "\n".join([f"- {h['title']} ({h['source']})" for h in headlines]) if headlines else "No major rate-related headlines"
        
        prompt = f"""Generate podcast commentary about Japan rates markets.

Current levels:
- JGB 10Y: {self._format_number(jgb_10y, 2)}%
- US 10Y: {self._format_number(us_10y, 2)}%
- Rate differential: {self._format_number(us_10y - jgb_10y, 2)}bp

Recent headlines:
{headline_text}

Cover what matters:
1. Any notable JGB yield moves overnight/yesterday
2. US Treasury spillover effects (rates often move together)
3. BOJ policy implications or operations
4. What this means for USD/JPY carry dynamics

If rates were quiet, just say "JGB yields were little changed overnight, trading around {self._format_number(jgb_10y, 2)}%."

Be specific about moves, levels, and catalysts. No fluff.
"""
        
        return self._call_openai(prompt, max_tokens=500, system_prompt=self.brief_system_prompt)
    
    def generate_fx_commentary(self, data: Dict[str, Any]) -> str:
        """Generate FX market commentary covering all JPY crosses"""
        
        fx_data = data.get('fx_rates', {})
        headlines = self._extract_headlines(data, limit=3)
        
        # Extract FX levels
        usd_jpy = fx_data.get('USD/JPY', 147.25)
        eur_jpy = fx_data.get('EUR/JPY', 158.90)
        usd_jpy_prev = fx_data.get('USD/JPY_prev', 147.00)  # Previous close if available
        eur_jpy_prev = fx_data.get('EUR/JPY_prev', 158.50)
        
        # Calculate changes
        usd_jpy_chg = usd_jpy - usd_jpy_prev
        eur_jpy_chg = eur_jpy - eur_jpy_prev
        
        headline_text = "\n".join([f"- {h['title']} ({h['source']})" for h in headlines]) if headlines else "No major FX headlines"
        
        prompt = f"""Generate podcast commentary about Japan FX markets. Cover ALL yen crosses, not just individual pairs.

Current levels and changes:
- USD/JPY: {self._format_number(usd_jpy)} ({usd_jpy_chg:+.0f} pips from yesterday)
- EUR/JPY: {self._format_number(eur_jpy)} ({eur_jpy_chg:+.0f} pips from yesterday)

Recent FX-related news:
{headline_text}

Discuss:
1. Main theme across yen crosses (risk on/off, policy divergence, carry dynamics)
2. Which pairs moved most and WHY (specific catalysts, not just correlation)
3. Any divergences that tell a story (e.g., USD/JPY up but EUR/JPY down = euro weakness, not just yen weakness)
4. Positioning or volatility if notable

Connect the dots. Show relationships. If FX was quiet, just say "Yen crosses were range-bound overnight with limited volatility."

Don't give equal time to each pair - focus on what actually moved and why.
"""
        
        return self._call_openai(prompt, max_tokens=600, system_prompt=self.brief_system_prompt)
    
    def generate_repo_commentary(self, data: Dict[str, Any]) -> str:
        """Generate repo market commentary"""
        
        repo_data = data.get('repo_data', {})
        headlines = self._extract_headlines(data, limit=2)
        
        # Extract repo data (placeholders for now)
        gc_repo = repo_data.get('gc_repo_rate', 0.15)
        repo_spread = repo_data.get('repo_ois_spread', 5)  # basis points
        specials = repo_data.get('specials', [])
        
        headline_text = "\n".join([f"- {h['title']}" for h in headlines]) if headlines else "No repo-specific headlines"
        
        prompt = f"""Generate podcast commentary about Japan repo markets and funding conditions.

Current conditions:
- GC repo rate: {self._format_number(gc_repo, 2)}%
- Repo-OIS spread: {repo_spread}bp
- Special issues: {len(specials)} JGBs trading special

Recent news:
{headline_text}

Cover what's relevant:
1. Any funding stress or unusual repo rates
2. Specific JGB issues trading special (if any) and why
3. Quarter-end or month-end effects on funding
4. BOJ operations impact on repo markets
5. Cross-currency basis (USD/JPY funding) if notable

If repo markets are calm and functioning normally, just say "Repo markets were stable overnight with no funding stress" and keep it brief.

Only elaborate if there's actual news or stress. Don't manufacture analysis.
"""
        
        return self._call_openai(prompt, max_tokens=400, system_prompt=self.brief_system_prompt)
    
    def generate_economist_commentary(self, data: Dict[str, Any]) -> str:
        """Generate macro/economic commentary and outlook"""
        
        macro_data = data.get('macro_data', {})
        headlines = self._extract_headlines(data, limit=4)
        
        # Extract economic indicators
        cpi = macro_data.get('japan_cpi', 106.5)
        gdp = macro_data.get('japan_gdp', 4231.14)
        
        headline_text = "\n".join([f"- {h['title']} ({h['source']})" for h in headlines]) if headlines else "No major economic headlines"
        
        prompt = f"""Generate podcast commentary on Japan's economic outlook and policy implications.

Current indicators:
- Japan CPI: {self._format_number(cpi, 1)}
- Japan GDP: ¥{self._format_number(gdp, 0)} trillion

Recent economic news:
{headline_text}

Discuss:
1. Any fresh economic data releases and what they mean for BOJ policy
2. Inflation trends and distance from BOJ's 2% target
3. Growth outlook and global economic connections
4. Upcoming key data releases or BOJ meetings to watch
5. Policy implications for markets (rates, FX)

Forward-looking focus: What should traders watch this week? What data/events could change the narrative?

If no major economic news, focus on "what's next" - upcoming releases, BOJ meetings, or policy themes.

Be specific about dates, levels, and policy implications. Connect macro to markets.
"""
        
        return self._call_openai(prompt, max_tokens=600, system_prompt=self.brief_system_prompt)