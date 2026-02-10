"""
Odds extraction flow.

Handles extraction of betting odds from sports websites including
match odds, over/under, Asian handicap, and other betting markets.
"""

from src.sites.base.flow import BaseFlow


class OddsExtractionFlow(BaseFlow):
    """Betting odds extraction flow."""
    
    async def extract_match_odds(self):
        """Extract basic match odds (1X2)."""
        odds = {}
        
        # Home win odds
        home_win = await self.selector_engine.find(self.page, "home_win_odds")
        odds['home_win'] = await home_win.inner_text() if home_win else None
        
        # Draw odds
        draw = await self.selector_engine.find(self.page, "draw_odds")
        odds['draw'] = await draw.inner_text() if draw else None
        
        # Away win odds
        away_win = await self.selector_engine.find(self.page, "away_win_odds")
        odds['away_win'] = await away_win.inner_text() if away_win else None
        
        return odds
    
    async def extract_over_under_odds(self):
        """Extract over/under odds for various lines."""
        over_under_odds = {}
        
        # Find all over/under markets
        markets = await self.selector_engine.find_all(self.page, "over_under_market")
        
        for market in markets:
            market_info = {}
            
            # Extract line value
            line = await market.query_selector(".ou_line")
            line_value = await line.inner_text() if line else None
            
            # Extract over odds
            over_odds = await market.query_selector(".over_odds")
            over_value = await over_odds.inner_text() if over_odds else None
            
            # Extract under odds
            under_odds = await market.query_selector(".under_odds")
            under_value = await under_odds.inner_text() if under_odds else None
            
            if line_value:
                market_info['line'] = line_value
                market_info['over'] = over_value
                market_info['under'] = under_value
                over_under_odds[line_value] = market_info
        
        return over_under_odds
    
    async def extract_asian_handicap_odds(self):
        """Extract Asian handicap odds."""
        handicap_odds = {}
        
        # Find all handicap markets
        markets = await self.selector_engine.find_all(self.page, "handicap_market")
        
        for market in markets:
            market_info = {}
            
            # Extract handicap line
            line = await market.query_selector(".handicap_line")
            line_value = await line.inner_text() if line else None
            
            # Extract home odds
            home_odds = await market.query_selector(".home_handicap_odds")
            home_value = await home_odds.inner_text() if home_odds else None
            
            # Extract away odds
            away_odds = await market.query_selector(".away_handicap_odds")
            away_value = await away_odds.inner_text() if away_odds else None
            
            if line_value:
                market_info['line'] = line_value
                market_info['home'] = home_value
                market_info['away'] = away_value
                handicap_odds[line_value] = market_info
        
        return handicap_odds
    
    async def extract_both_teams_to_score_odds(self):
        """Extract both teams to score (BTTS) odds."""
        btts_odds = {}
        
        # Yes odds
        yes_odds = await self.selector_engine.find(self.page, "btts_yes_odds")
        btts_odds['yes'] = await yes_odds.inner_text() if yes_odds else None
        
        # No odds
        no_odds = await self.selector_engine.find(self.page, "btts_no_odds")
        btts_odds['no'] = await no_odds.inner_text() if no_odds else None
        
        return btts_odds
    
    async def extract_correct_score_odds(self):
        """Extract correct score odds."""
        correct_score_odds = {}
        
        # Find all correct score options
        scores = await self.selector_engine.find_all(self.page, "correct_score_option")
        
        for score in scores:
            # Extract score
            score_text = await score.query_selector(".score_text")
            score_value = await score_text.inner_text() if score_text else None
            
            # Extract odds
            odds = await score.query_selector(".score_odds")
            odds_value = await odds.inner_text() if odds else None
            
            if score_value and odds_value:
                correct_score_odds[score_value] = odds_value
        
        return correct_score_odds
    
    async def extract_bookmaker_comparison(self):
        """Extract odds comparison from multiple bookmakers."""
        bookmaker_comparison = {}
        
        # Find all bookmaker sections
        bookmakers = await self.selector_engine.find_all(self.page, "bookmaker_section")
        
        for bookmaker in bookmakers:
            bookmaker_info = {}
            
            # Extract bookmaker name
            name = await bookmaker.query_selector(".bookmaker_name")
            bookmaker_name = await name.inner_text() if name else None
            
            # Extract 1X2 odds
            home_win = await bookmaker.query_selector(".home_win_odds")
            draw = await bookmaker.query_selector(".draw_odds")
            away_win = await bookmaker.query_selector(".away_win_odds")
            
            if bookmaker_name:
                bookmaker_info['home_win'] = await home_win.inner_text() if home_win else None
                bookmaker_info['draw'] = await draw.inner_text() if draw else None
                bookmaker_info['away_win'] = await away_win.inner_text() if away_win else None
                bookmaker_comparison[bookmaker_name] = bookmaker_info
        
        return bookmaker_comparison
    
    async def extract_odds_movement(self):
        """Extract odds movement history."""
        odds_movement = []
        
        # Find all odds movement entries
        movements = await self.selector_engine.find_all(self.page, "odds_movement_entry")
        
        for movement in movements:
            movement_info = {}
            
            # Extract timestamp
            timestamp = await movement.query_selector(".movement_time")
            movement_info['timestamp'] = await timestamp.inner_text() if timestamp else None
            
            # Extract odds values
            home_odds = await movement.query_selector(".home_odds_movement")
            draw_odds = await movement.query_selector(".draw_odds_movement")
            away_odds = await movement.query_selector(".away_odds_movement")
            
            movement_info['home_odds'] = await home_odds.inner_text() if home_odds else None
            movement_info['draw_odds'] = await draw_odds.inner_text() if draw_odds else None
            movement_info['away_odds'] = await away_odds.inner_text() if away_odds else None
            
            odds_movement.append(movement_info)
        
        return odds_movement
