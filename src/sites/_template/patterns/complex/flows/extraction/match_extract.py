"""
Match extraction flow.

Handles extraction of match data including scores, teams, match
details, and related information from match pages.
"""

from src.sites.base.flow import BaseFlow


class MatchExtractionFlow(BaseFlow):
    """Match data extraction flow."""
    
    async def extract_match_basic_info(self):
        """Extract basic match information."""
        match_info = {}
        
        # Extract teams
        home_team = await self.selector_engine.find(self.page, "home_team_name")
        away_team = await self.selector_engine.find(self.page, "away_team_name")
        
        match_info['home_team'] = await home_team.inner_text() if home_team else None
        match_info['away_team'] = await away_team.inner_text() if away_team else None
        
        # Extract score
        home_score = await self.selector_engine.find(self.page, "home_team_score")
        away_score = await self.selector_engine.find(self.page, "away_team_score")
        
        match_info['home_score'] = await home_score.inner_text() if home_score else None
        match_info['away_score'] = await away_score.inner_text() if away_score else None
        
        # Extract match time/status
        match_time = await self.selector_engine.find(self.page, "match_time")
        match_status = await self.selector_engine.find(self.page, "match_status")
        
        match_info['match_time'] = await match_time.inner_text() if match_time else None
        match_info['match_status'] = await match_status.inner_text() if match_status else None
        
        # Extract competition info
        competition = await self.selector_engine.find(self.page, "competition_name")
        match_info['competition'] = await competition.inner_text() if competition else None
        
        return match_info
    
    async def extract_match_events(self):
        """Extract match events (goals, cards, substitutions)."""
        events = []
        
        event_elements = await self.selector_engine.find_all(self.page, "match_event")
        
        for element in event_elements:
            event = {}
            
            # Extract event time
            event_time = await element.query_selector(".event-time")
            event['time'] = await event_time.inner_text() if event_time else None
            
            # Extract event type
            event_type = await element.query_selector(".event-type")
            event['type'] = await event_type.inner_text() if event_type else None
            
            # Extract player name
            player = await element.query_selector(".event-player")
            event['player'] = await player.inner_text() if player else None
            
            # Extract team
            team = await element.query_selector(".event-team")
            event['team'] = await team.inner_text() if team else None
            
            events.append(event)
        
        return events
    
    async def extract_match_lineups(self):
        """Extract team lineups."""
        lineups = {'home': [], 'away': []}
        
        # Extract home lineup
        home_players = await self.selector_engine.find_all(self.page, "home_lineup_player")
        for player_element in home_players:
            player_info = await self._extract_player_info(player_element)
            lineups['home'].append(player_info)
        
        # Extract away lineup
        away_players = await self.selector_engine.find_all(self.page, "away_lineup_player")
        for player_element in away_players:
            player_info = await self._extract_player_info(player_element)
            lineups['away'].append(player_info)
        
        return lineups
    
    async def _extract_player_info(self, player_element):
        """Extract player information from player element."""
        player_info = {}
        
        # Player name
        name = await player_element.query_selector(".player_name")
        player_info['name'] = await name.inner_text() if name else None
        
        # Player number
        number = await player_element.query_selector(".player_number")
        player_info['number'] = await number.inner_text() if number else None
        
        # Player position
        position = await player_element.query_selector(".player_position")
        player_info['position'] = await position.inner_text() if position else None
        
        return player_info
    
    async def extract_match_venue(self):
        """Extract match venue information."""
        venue_info = {}
        
        # Stadium name
        stadium = await self.selector_engine.find(self.page, "stadium_name")
        venue_info['stadium'] = await stadium.inner_text() if stadium else None
        
        # City
        city = await self.selector_engine.find(self.page, "stadium_city")
        venue_info['city'] = await city.inner_text() if city else None
        
        # Capacity
        capacity = await self.selector_engine.find(self.page, "stadium_capacity")
        venue_info['capacity'] = await capacity.inner_text() if capacity else None
        
        return venue_info
    
    async def extract_match_officials(self):
        """Extract match officials information."""
        officials = {}
        
        # Referee
        referee = await self.selector_engine.find(self.page, "referee_name")
        officials['referee'] = await referee.inner_text() if referee else None
        
        # Assistant referees
        assistant1 = await self.selector_engine.find(self.page, "assistant_referee_1")
        assistant2 = await self.selector_engine.find(self.page, "assistant_referee_2")
        
        officials['assistant_referees'] = []
        if assistant1:
            officials['assistant_referees'].append(await assistant1.inner_text())
        if assistant2:
            officials['assistant_referees'].append(await assistant2.inner_text())
        
        # Fourth official
        fourth_official = await self.selector_engine.find(self.page, "fourth_official")
        officials['fourth_official'] = await fourth_official.inner_text() if fourth_official else None
        
        return officials
