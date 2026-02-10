"""
Date filtering flow.

Handles date-based filtering operations including date range selection,
specific date filtering, and time-based content filtering.
"""

from src.sites.base.flow import BaseFlow
from datetime import datetime, timedelta


class DateFilteringFlow(BaseFlow):
    """Date filtering operations flow."""
    
    async def filter_by_date_range(self, start_date: str, end_date: str):
        """Filter content by date range."""
        # Open date filter
        date_filter_button = await self.selector_engine.find(
            self.page, "date_filter_button"
        )
        
        if date_filter_button:
            await date_filter_button.click()
            await self.page.wait_for_timeout(1000)
        
        # Set start date
        start_date_input = await self.selector_engine.find(
            self.page, "start_date_input"
        )
        
        if start_date_input:
            await start_date_input.clear()
            await start_date_input.type(start_date)
        
        # Set end date
        end_date_input = await self.selector_engine.find(
            self.page, "end_date_input"
        )
        
        if end_date_input:
            await end_date_input.clear()
            await end_date_input.type(end_date)
        
        # Apply filter
        apply_button = await self.selector_engine.find(
            self.page, "apply_date_filter"
        )
        
        if apply_button:
            await apply_button.click()
            await self.page.wait_for_timeout(2000)
    
    async def filter_by_specific_date(self, date: str):
        """Filter content by a specific date."""
        # Open date filter
        date_filter_button = await self.selector_engine.find(
            self.page, "date_filter_button"
        )
        
        if date_filter_button:
            await date_filter_button.click()
            await self.page.wait_for_timeout(1000)
        
        # Select specific date option
        specific_date_radio = await self.selector_engine.find(
            self.page, "specific_date_radio"
        )
        
        if specific_date_radio:
            await specific_date_radio.click()
        
        # Set the date
        date_input = await self.selector_engine.find(
            self.page, "specific_date_input"
        )
        
        if date_input:
            await date_input.clear()
            await date_input.type(date)
        
        # Apply filter
        apply_button = await self.selector_engine.find(
            self.page, "apply_date_filter"
        )
        
        if apply_button:
            await apply_button.click()
            await self.page.wait_for_timeout(2000)
    
    async def filter_by_relative_date(self, relative_option: str):
        """Filter by relative date (today, yesterday, this week, etc.)."""
        relative_date_button = await self.selector_engine.find(
            self.page, f"relative_date_{relative_option}"
        )
        
        if relative_date_button:
            await relative_date_button.click()
            await self.page.wait_for_timeout(2000)
    
    async def filter_by_last_n_days(self, days: int):
        """Filter content for the last N days."""
        # Open date filter
        date_filter_button = await self.selector_engine.find(
            self.page, "date_filter_button"
        )
        
        if date_filter_button:
            await date_filter_button.click()
            await self.page.wait_for_timeout(1000)
        
        # Select last N days option
        last_days_radio = await self.selector_engine.find(
            self.page, "last_days_radio"
        )
        
        if last_days_radio:
            await last_days_radio.click()
        
        # Set number of days
        days_input = await self.selector_engine.find(
            self.page, "last_days_input"
        )
        
        if days_input:
            await days_input.clear()
            await days_input.type(str(days))
        
        # Apply filter
        apply_button = await self.selector_engine.find(
            self.page, "apply_date_filter"
        )
        
        if apply_button:
            await apply_button.click()
            await self.page.wait_for_timeout(2000)
    
    async def filter_by_time_of_day(self, time_range: str):
        """Filter content by time of day (morning, afternoon, evening)."""
        time_filter = await self.selector_engine.find(
            self.page, f"time_filter_{time_range}"
        )
        
        if time_filter:
            await time_filter.click()
            await self.page.wait_for_timeout(2000)
    
    async def clear_date_filter(self):
        """Clear all date filters."""
        clear_button = await self.selector_engine.find(
            self.page, "clear_date_filter"
        )
        
        if clear_button:
            await clear_button.click()
            await self.page.wait_for_timeout(2000)
    
    async def get_active_date_filters(self):
        """Get currently active date filters."""
        active_filters = {}
        
        # Check if date filter is active
        date_filter_active = await self.selector_engine.find(
            self.page, "date_filter_active"
        )
        
        if date_filter_active:
            # Get start date
            start_date = await self.selector_engine.find(
                self.page, "active_start_date"
            )
            if start_date:
                active_filters['start_date'] = await start_date.inner_text()
            
            # Get end date
            end_date = await self.selector_engine.find(
                self.page, "active_end_date"
            )
            if end_date:
                active_filters['end_date'] = await end_date.inner_text()
            
            # Get relative filter
            relative_filter = await self.selector_engine.find(
                self.page, "active_relative_filter"
            )
            if relative_filter:
                active_filters['relative_filter'] = await relative_filter.inner_text()
        
        return active_filters
    
    async def get_date_filter_options(self):
        """Get available date filter options."""
        options = {}
        
        # Get relative date options
        relative_options = await self.page.query_selector_all(".relative_date_option")
        for option in relative_options:
            option_text = await option.inner_text()
            option_value = await option.get_attribute('data-value')
            if option_text and option_value:
                options[option_text.strip()] = option_value
        
        # Get time range options
        time_options = await self.page.query_selector_all(".time_filter_option")
        for option in time_options:
            option_text = await option.inner_text()
            option_value = await option.get_attribute('data-value')
            if option_text and option_value:
                options[option_text.strip()] = option_value
        
        return options
