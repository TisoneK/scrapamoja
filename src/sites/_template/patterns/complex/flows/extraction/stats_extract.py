"""
Statistics extraction flow.

Handles extraction of match statistics, player statistics,
team statistics, and performance metrics from sports websites.
"""

from src.sites.base.flow import BaseFlow


class StatsExtractionFlow(BaseFlow):
    """Statistics extraction flow."""
    
    async def extract_match_statistics(self):
        """Extract comprehensive match statistics."""
        stats = {}
        
        # Possession statistics
        home_possession = await self.selector_engine.find(self.page, "home_possession")
        away_possession = await self.selector_engine.find(self.page, "away_possession")
        
        stats['possession'] = {
            'home': await home_possession.inner_text() if home_possession else None,
            'away': await away_possession.inner_text() if away_possession else None
        }
        
        # Shots statistics
        home_shots = await self.selector_engine.find(self.page, "home_shots")
        away_shots = await self.selector_engine.find(self.page, "away_shots")
        home_shots_on_target = await self.selector_engine.find(self.page, "home_shots_on_target")
        away_shots_on_target = await self.selector_engine.find(self.page, "away_shots_on_target")
        
        stats['shots'] = {
            'home': {
                'total': await home_shots.inner_text() if home_shots else None,
                'on_target': await home_shots_on_target.inner_text() if home_shots_on_target else None
            },
            'away': {
                'total': await away_shots.inner_text() if away_shots else None,
                'on_target': await away_shots_on_target.inner_text() if away_shots_on_target else None
            }
        }
        
        # Fouls and cards
        home_fouls = await self.selector_engine.find(self.page, "home_fouls")
        away_fouls = await self.selector_engine.find(self.page, "away_fouls")
        home_yellow_cards = await self.selector_engine.find(self.page, "home_yellow_cards")
        away_yellow_cards = await self.selector_engine.find(self.page, "away_yellow_cards")
        home_red_cards = await self.selector_engine.find(self.page, "home_red_cards")
        away_red_cards = await self.selector_engine.find(self.page, "away_red_cards")
        
        stats['discipline'] = {
            'home': {
                'fouls': await home_fouls.inner_text() if home_fouls else None,
                'yellow_cards': await home_yellow_cards.inner_text() if home_yellow_cards else None,
                'red_cards': await home_red_cards.inner_text() if home_red_cards else None
            },
            'away': {
                'fouls': await away_fouls.inner_text() if away_fouls else None,
                'yellow_cards': await away_yellow_cards.inner_text() if away_yellow_cards else None,
                'red_cards': await away_red_cards.inner_text() if away_red_cards else None
            }
        }
        
        return stats
    
    async def extract_player_statistics(self):
        """Extract individual player statistics."""
        players_stats = []
        
        # Find all player stat rows
        player_rows = await self.selector_engine.find_all(self.page, "player_stats_row")
        
        for row in player_rows:
            player_stats = {}
            
            # Player basic info
            name = await row.query_selector(".player_name")
            number = await row.query_selector(".player_number")
            position = await row.query_selector(".player_position")
            
            player_stats['name'] = await name.inner_text() if name else None
            player_stats['number'] = await number.inner_text() if number else None
            player_stats['position'] = await position.inner_text() if position else None
            
            # Performance stats
            goals = await row.query_selector(".player_goals")
            assists = await row.query_selector(".player_assists")
            shots = await row.query_selector(".player_shots")
            passes = await row.query_selector(".player_passes")
            
            player_stats['goals'] = await goals.inner_text() if goals else None
            player_stats['assists'] = await assists.inner_text() if assists else None
            player_stats['shots'] = await shots.inner_text() if shots else None
            player_stats['passes'] = await passes.inner_text() if passes else None
            
            players_stats.append(player_stats)
        
        return players_stats
    
    async def extract_team_statistics(self):
        """Extract team-level statistics."""
        team_stats = {}
        
        # Home team stats
        home_stats = {}
        home_wins = await self.selector_engine.find(self.page, "home_team_wins")
        home_draws = await self.selector_engine.find(self.page, "home_team_draws")
        home_losses = await self.selector_engine.find(self.page, "home_team_losses")
        
        home_stats['wins'] = await home_wins.inner_text() if home_wins else None
        home_stats['draws'] = await home_draws.inner_text() if home_draws else None
        home_stats['losses'] = await home_losses.inner_text() if home_losses else None
        
        # Away team stats
        away_stats = {}
        away_wins = await self.selector_engine.find(self.page, "away_team_wins")
        away_draws = await self.selector_engine.find(self.page, "away_team_draws")
        away_losses = await self.selector_engine.find(self.page, "away_team_losses")
        
        away_stats['wins'] = await away_wins.inner_text() if away_wins else None
        away_stats['draws'] = await away_draws.inner_text() if away_draws else None
        away_stats['losses'] = await away_losses.inner_text() if away_losses else None
        
        team_stats['home'] = home_stats
        team_stats['away'] = away_stats
        
        return team_stats
    
    async def extract_head_to_head_statistics(self):
        """Extract head-to-head statistics between teams."""
        h2h_stats = {}
        
        # Total matches played
        total_matches = await self.selector_engine.find(self.page, "h2h_total_matches")
        h2h_stats['total_matches'] = await total_matches.inner_text() if total_matches else None
        
        # Home team wins in H2H
        home_wins = await self.selector_engine.find(self.page, "h2h_home_wins")
        h2h_stats['home_wins'] = await home_wins.inner_text() if home_wins else None
        
        # Away team wins in H2H
        away_wins = await self.selector_engine.find(self.page, "h2h_away_wins")
        h2h_stats['away_wins'] = await away_wins.inner_text() if away_wins else None
        
        # Draws in H2H
        draws = await self.selector_engine.find(self.page, "h2h_draws")
        h2h_stats['draws'] = await draws.inner_text() if draws else None
        
        # Recent H2H matches
        recent_matches = []
        match_elements = await self.selector_engine.find_all(self.page, "h2h_recent_match")
        
        for match in match_elements:
            match_info = {}
            
            date = await match.query_selector(".match_date")
            home_score = await match.query_selector(".home_score")
            away_score = await match.query_selector(".away_score")
            
            match_info['date'] = await date.inner_text() if date else None
            match_info['home_score'] = await home_score.inner_text() if home_score else None
            match_info['away_score'] = await away_score.inner_text() if away_score else None
            
            recent_matches.append(match_info)
        
        h2h_stats['recent_matches'] = recent_matches
        
        return h2h_stats
    
    async def extract_form_statistics(self):
        """Extract team form statistics (last N games)."""
        form_stats = {}
        
        # Home team form
        home_form = []
        home_form_elements = await self.selector_engine.find_all(self.page, "home_team_form")
        
        for element in home_form_elements:
            result = await element.get_attribute('data-result')
            if result:
                home_form.append(result)
        
        # Away team form
        away_form = []
        away_form_elements = await self.selector_engine.find_all(self.page, "away_team_form")
        
        for element in away_form_elements:
            result = await element.get_attribute('data-result')
            if result:
                away_form.append(result)
        
        form_stats['home_form'] = home_form
        form_stats['away_form'] = away_form
        
        return form_stats
