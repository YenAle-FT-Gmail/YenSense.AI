  CURRENTLY FETCHED:

  - FX: USD/JPY, EUR/JPY (spot rates only)
  - Macro: Japan CPI, Japan GDP, US GDP from FRED
  - Economic Calendar: Trading Economics via Selenium (G3 events, bond auctions, 2-month forward)
  - News: Placeholder links (not actual headlines)
  - BOJ: Placeholder links (not actual policy content)
  - Repo: None
  - Rates: None (JGB yields missing)

  MISSING CRITICAL DATA PER DOMAIN:

  RATES MARKETS

  Currently missing:
  - JGB yields (2Y, 5Y, 10Y, 30Y, 40Y curve)
  - US Treasury yields for comparison
  - BOJ operations data
  - curve shaped
  - Yield differentials

  Should include:
  - Current JGB yield levels with overnight changes
  - US Treasury yields (2Y, 5Y, 10Y) for spillover analysis
  - BOJ YCC operations/interventions
  - Rate differential calculations (US-Japan)
  - Historical context (1W, 1M changes)

  FOREIGN EXCHANGE

  Currently missing:
  - Overnight high/low ranges
  - Additional crosses (AUD/JPY, GBP/JPY, CAD/JPY)
  - Previous day closes for change calculations
  - Volatility indicators

  Should include:
  - All major JPY crosses with overnight ranges
  - Previous close for % change calculations
  - Cross-currency implied rates (EUR/USD via crosses)
  - Volatility measures (realized, implied if available)
  - Key technical levels

  REPO MARKETS

  Currently missing:
  - Everything (no repo data fetched)

  Should include:
  - GC repo rate
  - Repo-OIS spread
  - Special repo rates (specific JGB issues)
  - Cross-currency basis (USD/JPY funding)
  - BOJ repo operations

  ECONOMIST

  Currently missing:
  - Recent economic releases with actual vs expected
  - Real news headlines

  Should include:
  - Latest economic data releases (actual vs forecast vs previous)
  - Real news headlines about policy/economy
  - Market expectations/consensus

  Currently available:
  - Forward calendar via Trading Economics Selenium scraper (G3 economic events, bond auctions)
  - 2-month forward visibility with 24-hour caching
  - Automated filtering for high and low impact events

  DATA ENHANCEMENT NEEDED:

  Immediate fixes:
  1. Real news scraping - Get actual headlines, not placeholder links
  2. JGB yield data - Add MOF/Bloomberg proxy for yield curve
  3. Overnight ranges - Get high/low for FX pairs
  4. Repo data - Add basic repo rates and spreads

  Already completed:
  5. ✅ Economic calendar - Trading Economics Selenium scraper provides G3 economic events and bond auctions with 2-month forward visibility

  Quality improvements:
  1. Historical context - Previous day/week/month for comparison
  2. Cross-market data - VIX, DXY, oil for risk sentiment
  3. Technical levels - Basic support/resistance
  4. Time-series - Trend analysis capabilities