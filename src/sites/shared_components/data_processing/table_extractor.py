"""
Shared table extraction processor for reusable table processing across sites.

This module provides comprehensive table extraction functionality that can be easily
integrated into any site scraper for extracting and processing table data.
"""

from typing import Dict, Any, Optional, List, Callable, Union, Tuple
from datetime import datetime, timedelta
import asyncio
import json
import re
from urllib.parse import urlparse

from src.sites.base.component_interface import BaseProcessor, ProcessorContext, ProcessorResult


class TableExtractionProcessor(BaseProcessor):
    """Shared table extraction processor for cross-site usage."""
    
    def __init__(
        self,
        processor_id: str = "shared_table_extractor",
        name: str = "Shared Table Extraction Processor",
        version: str = "1.0.0",
        description: str = "Reusable table extraction processor for multiple sites"
    ):
        """
        Initialize shared table extraction processor.
        
        Args:
            processor_id: Unique identifier for the processor
            name: Human-readable name for the processor
            version: Processor version
            description: Processor description
        """
        super().__init__(
            processor_id=processor_id,
            name=name,
            version=version,
            description=description,
            processor_type="TABLE_EXTRACTION"
        )
        
        # Table extraction configurations for different sites
        self._site_configs: Dict[str, Dict[str, Any]] = {}
        
        # Extraction state and statistics
        self._extraction_stats: Dict[str, Dict[str, Any]] = {}
        
        # Callback handlers
        self._extraction_callbacks: Dict[str, List[Callable]] = {}
        
        # Component metadata
        self._supported_sites = [
            'wikipedia', 'financial_sites', 'sports_sites', 'data_portals',
            'ecommerce', 'research_sites', 'government', 'education'
        ]
        
        # Common table patterns and selectors
        self._table_selectors = [
            'table', '[class*="table"]', '[data-table]',
            '.data-table', '.stats-table', '.results-table'
        ]
        
        self._header_selectors = [
            'thead tr', 'tr:first-child', 'th', '[class*="header"]',
            '.table-header', '.row-header'
        ]
        
        self._row_selectors = [
            'tbody tr', 'tr:not(:first-child)', '[class*="row"]',
            '.table-row', '.data-row'
        ]
        
        self._cell_selectors = [
            'td', 'th', '[class*="cell"]', '.table-cell',
            '.data-cell'
        ]
    
    async def initialize(self, context: ProcessorContext) -> bool:
        """
        Initialize shared table extraction processor.
        
        Args:
            context: Processor context
            
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            # Load table extraction configurations from context
            config = context.config_manager.get_config(context.environment) if context.config_manager else {}
            
            # Initialize default site configurations
            await self._initialize_default_configs()
            
            # Load custom site configurations
            custom_configs = config.get('table_extraction_site_configs', {})
            for site, site_config in custom_configs.items():
                self.register_site(site, site_config)
            
            self._log_operation("initialize", f"Shared table extraction processor initialized with {len(self._site_configs)} site configurations")
            return True
            
        except Exception as e:
            self._log_operation("initialize", f"Shared table extraction initialization failed: {str(e)}", "error")
            return False
    
    async def execute(self, **kwargs) -> ProcessorResult:
        """
        Execute table extraction for a specific site.
        
        Args:
            **kwargs: Extraction parameters including 'site', 'page', 'table_selector', etc.
            
        Returns:
            Table extraction result
        """
        try:
            start_time = datetime.utcnow()
            
            # Extract parameters
            site = kwargs.get('site')
            page = kwargs.get('page')
            table_selector = kwargs.get('table_selector')
            auto_detect = kwargs.get('auto_detect', True)
            extract_headers = kwargs.get('extract_headers', True)
            clean_data = kwargs.get('clean_data', True)
            max_tables = kwargs.get('max_tables', 10)
            
            if not site:
                return ProcessorResult(
                    success=False,
                    data={'error': 'Site parameter is required'},
                    errors=['Site parameter is required']
                )
            
            if not page:
                return ProcessorResult(
                    success=False,
                    data={'error': 'Page parameter is required'},
                    errors=['Page parameter is required']
                )
            
            # Initialize extraction stats
            self._initialize_extraction_stats(site)
            
            # Perform table extraction
            extraction_result = await self._extract_tables(
                site, page, table_selector, auto_detect, extract_headers, clean_data, max_tables
            )
            
            end_time = datetime.utcnow()
            execution_time = (end_time - start_time).total_seconds() * 1000
            
            # Update statistics
            self._update_extraction_stats(site, extraction_result, execution_time)
            
            # Call extraction callbacks
            await self._call_extraction_callbacks(site, extraction_result)
            
            return ProcessorResult(
                success=extraction_result['success'],
                data={
                    'site': site,
                    'extraction_timestamp': start_time.isoformat(),
                    **extraction_result
                },
                execution_time_ms=execution_time
            )
            
        except Exception as e:
            self._log_operation("execute", f"Table extraction failed: {str(e)}", "error")
            return ProcessorResult(
                success=False,
                data={'error': str(e)},
                errors=[str(e)]
            )
    
    def register_site(self, site: str, config: Dict[str, Any]) -> None:
        """
        Register table extraction configuration for a site.
        
        Args:
            site: Site identifier
            config: Table extraction configuration
        """
        self._site_configs[site] = {
            'table_selector': config.get('table_selector'),
            'header_selector': config.get('header_selector'),
            'row_selector': config.get('row_selector'),
            'cell_selector': config.get('cell_selector'),
            'exclude_selectors': config.get('exclude_selectors', []),
            'include_empty_cells': config.get('include_empty_cells', False),
            'clean_data': config.get('clean_data', True),
            'normalize_headers': config.get('normalize_headers', True),
            'detect_data_types': config.get('detect_data_types', True),
            'merge_duplicate_headers': config.get('merge_duplicate_headers', True),
            'max_rows': config.get('max_rows', 1000),
            'max_columns': config.get('max_columns', 50)
        }
        
        self._log_operation("register_site", f"Registered table extraction configuration for site: {site}")
    
    async def _initialize_default_configs(self) -> None:
        """Initialize default table extraction configurations for common sites."""
        default_configs = {
            'wikipedia': {
                'table_selector': 'table.wikitable, table.infobox',
                'header_selector': 'thead tr, tr:first-child',
                'row_selector': 'tbody tr, tr:not(:first-child)',
                'cell_selector': 'td, th',
                'exclude_selectors': ['.navbox', '.metadata'],
                'clean_data': True,
                'normalize_headers': True,
                'detect_data_types': True
            },
            'financial_sites': {
                'table_selector': 'table.data-table, .financial-table, table',
                'header_selector': 'thead tr, tr:first-child',
                'row_selector': 'tbody tr, tr:not(:first-child)',
                'cell_selector': 'td, th',
                'clean_data': True,
                'detect_data_types': True,
                'merge_duplicate_headers': False
            },
            'sports_sites': {
                'table_selector': 'table.stats-table, .scores-table, table',
                'header_selector': 'thead tr, tr:first-child',
                'row_selector': 'tbody tr, tr:not(:first-child)',
                'cell_selector': 'td, th',
                'clean_data': True,
                'detect_data_types': True
            },
            'ecommerce': {
                'table_selector': 'table.product-table, .comparison-table, table',
                'header_selector': 'thead tr, tr:first-child',
                'row_selector': 'tbody tr, tr:not(:first-child)',
                'cell_selector': 'td, th',
                'clean_data': True,
                'detect_data_types': True
            },
            'data_portals': {
                'table_selector': 'table.data-table, table',
                'header_selector': 'thead tr, tr:first-child',
                'row_selector': 'tbody tr, tr:not(:first-child)',
                'cell_selector': 'td, th',
                'clean_data': True,
                'detect_data_types': True,
                'max_rows': 500
            }
        }
        
        for site, config in default_configs.items():
            if site not in self._site_configs:
                self._site_configs[site] = config
    
    def _initialize_extraction_stats(self, site: str) -> None:
        """Initialize extraction statistics for a site."""
        if site not in self._extraction_stats:
            self._extraction_stats[site] = {
                'extractions_performed': 0,
                'total_tables_extracted': 0,
                'total_rows_extracted': 0,
                'total_columns_extracted': 0,
                'total_cells_extracted': 0,
                'average_extraction_time_ms': 0.0,
                'last_extraction_time': None,
                'success_count': 0,
                'error_count': 0
            }
    
    async def _extract_tables(
        self, site: str, page, table_selector: str, auto_detect: bool,
        extract_headers: bool, clean_data: bool, max_tables: int
    ) -> Dict[str, Any]:
        """Perform table extraction."""
        try:
            config = self._site_configs[site]
            
            # Auto-detect table selector if not provided
            if not table_selector and auto_detect:
                table_selector = await self._detect_table_selector(page)
                table_selector = table_selector or config.get('table_selector')
            
            if not table_selector:
                return {
                    'success': False,
                    'error': 'No table selector found or provided'
                }
            
            # Find all tables
            table_elements = await page.query_selector_all(table_selector)
            if not table_elements:
                return {
                    'success': False,
                    'error': 'No tables found on the page'
                }
            
            # Limit number of tables
            table_elements = table_elements[:max_tables]
            
            # Extract data from each table
            extracted_tables = []
            total_rows = 0
            total_columns = 0
            total_cells = 0
            
            for i, table_element in enumerate(table_elements):
                table_data = await self._extract_single_table(
                    page, table_element, config, extract_headers, clean_data, i
                )
                
                if table_data['success']:
                    extracted_tables.append(table_data['data'])
                    total_rows += table_data['data'].get('row_count', 0)
                    total_columns += table_data['data'].get('column_count', 0)
                    total_cells += table_data['data'].get('cell_count', 0)
            
            return {
                'success': True,
                'tables_extracted': extracted_tables,
                'table_count': len(extracted_tables),
                'total_rows': total_rows,
                'total_columns': total_columns,
                'total_cells': total_cells,
                'table_selector_used': table_selector
            }
            
        except Exception as e:
            self._log_operation("_extract_tables", f"Table extraction failed for {site}: {str(e)}", "error")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _detect_table_selector(self, page) -> Optional[str]:
        """Auto-detect the best table selector for the page."""
        try:
            for selector in self._table_selectors:
                elements = await page.query_selector_all(selector)
                if elements:
                    # Check if these are actually data tables
                    for element in elements[:3]:  # Check first 3 elements
                        rows = await element.query_selector_all('tr')
                        if len(rows) > 2:  # At least header + 2 data rows
                            return selector
            
            return None
            
        except Exception as e:
            self._log_operation("_detect_table_selector", f"Table selector detection failed: {str(e)}", "error")
            return None
    
    async def _extract_single_table(
        self, page, table_element, config: Dict[str, Any], 
        extract_headers: bool, clean_data: bool, table_index: int
    ) -> Dict[str, Any]:
        """Extract data from a single table."""
        try:
            # Extract table metadata
            table_metadata = await self._extract_table_metadata(page, table_element, table_index)
            
            # Extract headers
            headers = []
            if extract_headers:
                headers = await self._extract_table_headers(page, table_element, config)
            
            # Extract rows
            rows = await self._extract_table_rows(page, table_element, config, headers)
            
            # Clean and process data
            if clean_data:
                headers = [self._clean_cell_data(header) for header in headers]
                rows = [[self._clean_cell_data(cell) for cell in row] for row in rows]
            
            # Detect data types if requested
            data_types = {}
            if config.get('detect_data_types', True) and rows:
                data_types = self._detect_column_data_types(rows, headers)
            
            # Create table data structure
            table_data = {
                'table_index': table_index,
                'metadata': table_metadata,
                'headers': headers,
                'rows': rows,
                'data_types': data_types,
                'row_count': len(rows),
                'column_count': len(headers) if headers else (len(rows[0]) if rows else 0),
                'cell_count': len(rows) * (len(headers) if headers else (len(rows[0]) if rows else 0))
            }
            
            return {
                'success': True,
                'data': table_data
            }
            
        except Exception as e:
            self._log_operation("_extract_single_table", f"Single table extraction failed: {str(e)}", "error")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def _extract_table_metadata(self, page, table_element, table_index: int) -> Dict[str, Any]:
        """Extract metadata from a table."""
        try:
            metadata = {
                'table_index': table_index,
                'table_html': await table_element.inner_html(),
                'table_class': await table_element.get_attribute('class') or '',
                'table_id': await table_element.get_attribute('id') or ''
            }
            
            # Extract caption if present
            caption_element = await table_element.query_selector('caption')
            if caption_element:
                metadata['caption'] = await caption_element.text_content()
            
            # Extract summary attribute
            summary = await table_element.get_attribute('summary')
            if summary:
                metadata['summary'] = summary
            
            return metadata
            
        except Exception as e:
            self._log_operation("_extract_table_metadata", f"Table metadata extraction failed: {str(e)}", "error")
            return {'table_index': table_index}
    
    async def _extract_table_headers(self, page, table_element, config: Dict[str, Any]) -> List[str]:
        """Extract headers from a table."""
        try:
            headers = []
            
            # Try different header selectors
            header_selectors = [
                config.get('header_selector'),
                'thead tr',
                'tr:first-child',
                'th'
            ]
            
            for selector in header_selectors:
                if not selector:
                    continue
                
                header_elements = await table_element.query_selector_all(selector)
                if header_elements:
                    # Get text from header cells
                    for element in header_elements:
                        header_text = await element.text_content()
                        if header_text and header_text.strip():
                            headers.append(header_text.strip())
                    
                    # If we found headers, break
                    if headers:
                        break
            
            # If still no headers, try to extract from first row
            if not headers:
                first_row = await table_element.query_selector('tr')
                if first_row:
                    cells = await first_row.query_selector_all('th, td')
                    for cell in cells:
                        cell_text = await cell.text_content()
                        if cell_text and cell_text.strip():
                            headers.append(cell_text.strip())
            
            return headers
            
        except Exception as e:
            self._log_operation("_extract_table_headers", f"Table header extraction failed: {str(e)}", "error")
            return []
    
    async def _extract_table_rows(self, page, table_element, config: Dict[str, Any], headers: List[str]) -> List[List[str]]:
        """Extract rows from a table."""
        try:
            rows = []
            
            # Get row selector
            row_selector = config.get('row_selector', 'tbody tr, tr:not(:first-child)')
            
            # Find all row elements
            row_elements = await table_element.query_selector_all(row_selector)
            
            # Limit number of rows
            max_rows = config.get('max_rows', 1000)
            row_elements = row_elements[:max_rows]
            
            for row_element in row_elements:
                row_data = []
                
                # Get cells from this row
                cell_selector = config.get('cell_selector', 'td, th')
                cell_elements = await row_element.query_selector_all(cell_selector)
                
                # Limit number of columns
                max_columns = config.get('max_columns', 50)
                cell_elements = cell_elements[:max_columns]
                
                for cell_element in cell_elements:
                    cell_text = await cell_element.text_content()
                    
                    # Skip empty cells if not including them
                    if not config.get('include_empty_cells', False) and not cell_text.strip():
                        row_data.append('')
                    else:
                        row_data.append(cell_text.strip())
                
                # Only add row if it has data
                if row_data and any(cell.strip() for cell in row_data):
                    rows.append(row_data)
            
            return rows
            
        except Exception as e:
            self._log_operation("_extract_table_rows", f"Table row extraction failed: {str(e)}", "error")
            return []
    
    def _clean_cell_data(self, cell_data: str) -> str:
        """Clean and normalize cell data."""
        try:
            if not cell_data:
                return ''
            
            # Remove extra whitespace
            cell_data = re.sub(r'\s+', ' ', cell_data)
            
            # Remove leading/trailing whitespace
            cell_data = cell_data.strip()
            
            # Remove common non-printable characters
            cell_data = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', cell_data)
            
            return cell_data
            
        except Exception:
            return cell_data or ''
    
    def _detect_column_data_types(self, rows: List[List[str]], headers: List[str]) -> Dict[str, str]:
        """Detect data types for table columns."""
        try:
            if not rows or not headers:
                return {}
            
            data_types = {}
            num_columns = min(len(headers), len(rows[0]) if rows else 0)
            
            for col_index in range(num_columns):
                column_values = []
                
                # Collect non-empty values from this column
                for row in rows:
                    if col_index < len(row) and row[col_index].strip():
                        column_values.append(row[col_index].strip())
                
                # Detect data type based on values
                data_type = self._detect_data_type(column_values)
                data_types[headers[col_index]] = data_type
            
            return data_types
            
        except Exception as e:
            self._log_operation("_detect_column_data_types", f"Data type detection failed: {str(e)}", "error")
            return {}
    
    def _detect_data_type(self, values: List[str]) -> str:
        """Detect data type for a list of values."""
        try:
            if not values:
                return 'unknown'
            
            # Check for numeric values
            numeric_count = 0
            for value in values:
                try:
                    float(value.replace(',', '').replace('$', '').replace('%', ''))
                    numeric_count += 1
                except ValueError:
                    pass
            
            if numeric_count / len(values) > 0.8:
                return 'numeric'
            
            # Check for dates
            date_count = 0
            for value in values:
                if self._looks_like_date(value):
                    date_count += 1
            
            if date_count / len(values) > 0.8:
                return 'date'
            
            # Check for URLs
            url_count = 0
            for value in values:
                if value.startswith(('http://', 'https://', 'www.')):
                    url_count += 1
            
            if url_count / len(values) > 0.8:
                return 'url'
            
            # Check for emails
            email_count = 0
            for value in values:
                if '@' in value and '.' in value.split('@')[-1]:
                    email_count += 1
            
            if email_count / len(values) > 0.8:
                return 'email'
            
            return 'text'
            
        except Exception:
            return 'unknown'
    
    def _looks_like_date(self, value: str) -> bool:
        """Check if a value looks like a date."""
        try:
            # Common date patterns
            date_patterns = [
                r'\d{1,2}/\d{1,2}/\d{4}',  # MM/DD/YYYY
                r'\d{4}-\d{2}-\d{2}',      # YYYY-MM-DD
                r'\d{1,2}\s+\w+\s+\d{4}', # DD Month YYYY
                r'\w+\s+\d{1,2},\s+\d{4}', # Month DD, YYYY
            ]
            
            for pattern in date_patterns:
                if re.search(pattern, value):
                    return True
            
            return False
            
        except Exception:
            return False
    
    def _update_extraction_stats(self, site: str, result: Dict[str, Any], execution_time: float) -> None:
        """Update extraction statistics for a site."""
        try:
            if site not in self._extraction_stats:
                return
            
            stats = self._extraction_stats[site]
            stats['extractions_performed'] += 1
            stats['last_extraction_time'] = datetime.utcnow()
            
            if result['success']:
                stats['success_count'] += 1
                stats['total_tables_extracted'] += result.get('table_count', 0)
                stats['total_rows_extracted'] += result.get('total_rows', 0)
                stats['total_columns_extracted'] += result.get('total_columns', 0)
                stats['total_cells_extracted'] += result.get('total_cells', 0)
            else:
                stats['error_count'] += 1
            
            # Update average execution time
            total_time = stats.get('total_execution_time', 0) + execution_time
            stats['total_execution_time'] = total_time
            stats['average_extraction_time_ms'] = total_time / stats['extractions_performed']
            
        except Exception as e:
            self._log_operation("_update_extraction_stats", f"Failed to update extraction stats: {str(e)}", "error")
    
    def add_extraction_callback(self, site: str, callback: Callable) -> None:
        """Add callback for table extraction events."""
        if site not in self._extraction_callbacks:
            self._extraction_callbacks[site] = []
        self._extraction_callbacks[site].append(callback)
    
    async def _call_extraction_callbacks(self, site: str, data: Dict[str, Any]) -> None:
        """Call extraction callbacks for site."""
        if site in self._extraction_callbacks:
            for callback in self._extraction_callbacks[site]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(site, data)
                    else:
                        callback(site, data)
                except Exception as e:
                    self._log_operation("_call_extraction_callbacks", f"Extraction callback failed for {site}: {str(e)}", "error")
    
    def get_supported_sites(self) -> List[str]:
        """Get list of supported sites."""
        return list(self._supported_sites)
    
    def get_site_config(self, site: str) -> Optional[Dict[str, Any]]:
        """Get table extraction configuration for a site."""
        return self._site_configs.get(site)
    
    def get_extraction_stats(self, site: str) -> Optional[Dict[str, Any]]:
        """Get extraction statistics for a site."""
        if site not in self._extraction_stats:
            return None
        
        stats = self._extraction_stats[site].copy()
        if 'last_extraction_time' in stats and isinstance(stats['last_extraction_time'], datetime):
            stats['last_extraction_time'] = stats['last_extraction_time'].isoformat()
        
        return stats
    
    def reset_extraction_stats(self, site: str) -> None:
        """Reset extraction statistics for a site."""
        if site in self._extraction_stats:
            del self._extraction_stats[site]
    
    async def cleanup(self) -> None:
        """Clean up shared table extraction processor."""
        try:
            # Clear all stats and callbacks
            self._extraction_stats.clear()
            self._extraction_callbacks.clear()
            
            self._log_operation("cleanup", "Shared table extraction processor cleaned up")
            
        except Exception as e:
            self._log_operation("cleanup", f"Shared table extraction cleanup failed: {str(e)}", "error")


# Factory function for easy processor creation
def create_table_extraction_processor() -> TableExtractionProcessor:
    """Create a shared table extraction processor."""
    return TableExtractionProcessor()


# Component metadata for discovery
COMPONENT_METADATA = {
    'id': 'shared_table_extractor',
    'name': 'Shared Table Extraction Processor',
    'version': '1.0.0',
    'type': 'TABLE_EXTRACTION',
    'description': 'Reusable table extraction processor for multiple sites',
    'supported_sites': ['wikipedia', 'financial_sites', 'sports_sites', 'data_portals', 'ecommerce', 'research_sites', 'government', 'education'],
    'features': [
        'multi_site_support',
        'auto_table_detection',
        'header_extraction',
        'data_type_detection',
        'data_cleaning',
        'statistics_tracking',
        'callback_system',
        'metadata_extraction'
    ],
    'dependencies': [],
    'configuration_required': [],
    'optional_configuration': ['table_selector', 'header_selector', 'row_selector', 'extract_headers', 'clean_data', 'max_rows']
}
