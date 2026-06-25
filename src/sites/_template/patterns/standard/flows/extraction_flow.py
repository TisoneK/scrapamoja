"""
Extraction flow for standard pattern.

Handles data extraction operations including table parsing,
list extraction, and structured data collection.
"""

from src.sites.base.flow import BaseFlow


class ExtractionFlow(BaseFlow):
    """Data extraction operations flow."""
    
    async def extract_table_data(self, table_selector: str):
        """Extract data from a table."""
        table = await self.selector_engine.find(self.page, table_selector)
        
        if not table:
            return []
        
        # Extract headers
        headers = []
        header_elements = await table.query_selector_all("thead th")
        for header in header_elements:
            header_text = await header.inner_text()
            headers.append(header_text.strip())
        
        # Extract rows
        rows_data = []
        row_elements = await table.query_selector_all("tbody tr")
        
        for row in row_elements:
            row_data = {}
            cell_elements = await row.query_selector_all("td")
            
            for i, cell in enumerate(cell_elements):
                if i < len(headers):
                    cell_text = await cell.inner_text()
                    row_data[headers[i]] = cell_text.strip()
            
            rows_data.append(row_data)
        
        return rows_data
    
    async def extract_list_data(self, list_selector: str):
        """Extract data from a list."""
        list_element = await self.selector_engine.find(self.page, list_selector)
        
        if not list_element:
            return []
        
        items = []
        item_elements = await list_element.query_selector_all("li")
        
        for item in item_elements:
            item_text = await item.inner_text()
            items.append(item_text.strip())
        
        return items
    
    async def extract_card_data(self, card_selector: str):
        """Extract data from card elements."""
        cards = await self.selector_engine.find_all(self.page, card_selector)
        
        if not cards:
            return []
        
        cards_data = []
        
        for card in cards:
            card_data = {}
            
            # Try to extract common card elements
            title = await card.query_selector(".card-title, h3, h4")
            if title:
                card_data['title'] = await title.inner_text()
            
            description = await card.query_selector(".card-description, p")
            if description:
                card_data['description'] = await description.inner_text()
            
            link = await card.query_selector("a")
            if link:
                card_data['url'] = await link.get_attribute('href')
            
            image = await card.query_selector("img")
            if image:
                card_data['image_url'] = await image.get_attribute('src')
            
            cards_data.append(card_data)
        
        return cards_data
    
    async def extract_form_data(self, form_selector: str):
        """Extract form field information."""
        form = await self.selector_engine.find(self.page, form_selector)
        
        if not form:
            return {}
        
        form_data = {}
        
        # Extract input fields
        inputs = await form.query_selector_all("input")
        for input_field in inputs:
            name = await input_field.get_attribute('name')
            field_type = await input_field.get_attribute('type')
            placeholder = await input_field.get_attribute('placeholder')
            
            if name:
                form_data[name] = {
                    'type': field_type or 'text',
                    'placeholder': placeholder,
                    'value': await input_field.input_value()
                }
        
        # Extract select fields
        selects = await form.query_selector_all("select")
        for select in selects:
            name = await select.get_attribute('name')
            if name:
                options = []
                option_elements = await select.query_selector_all("option")
                
                for option in option_elements:
                    option_value = await option.get_attribute('value')
                    option_text = await option.inner_text()
                    options.append({
                        'value': option_value,
                        'text': option_text
                    })
                
                form_data[name] = {
                    'type': 'select',
                    'options': options,
                    'selected': await select.input_value()
                }
        
        return form_data
