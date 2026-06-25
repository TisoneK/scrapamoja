"""
API client for the adaptive selector failures API.

This module provides a Python client for interacting with the failures API.
It can be used by frontend applications or other services.

Story: 4.1 - View Proposed Selectors with Visual Preview
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
import json


class FailureAPIClient:
    """
    Client for interacting with the failures API.
    
    This client provides methods for:
    - Listing failures with filters
    - Getting failure details
    - Approving/rejecting alternatives
    """
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        """
        Initialize the API client.
        
        Args:
            base_url: Base URL of the API (defaults to local dev server)
        """
        self.base_url = base_url.rstrip("/")
    
    def _build_url(self, path: str) -> str:
        """Build full URL from path."""
        return f"{self.base_url}{path}"
    
    async def list_failures(
        self,
        sport: Optional[str] = None,
        site: Optional[str] = None,
        error_type: Optional[str] = None,
        severity: Optional[str] = None,
        flagged: Optional[bool] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        """
        List failures with optional filters.
        
        Args:
            sport: Filter by sport
            site: Filter by site
            error_type: Filter by error type
            severity: Filter by severity
            flagged: Filter by flagged status
            date_from: Filter from date
            date_to: Filter to date
            page: Page number
            page_size: Results per page
            
        Returns:
            API response with failures list
        """
        import aiohttp
        
        params = {"page": page, "page_size": page_size}
        if sport:
            params["sport"] = sport
        if site:
            params["site"] = site
        if error_type:
            params["error_type"] = error_type
        if severity:
            params["severity"] = severity
        if flagged is not None:
            params["flagged"] = str(flagged)
        if date_from:
            params["date_from"] = date_from.isoformat()
        if date_to:
            params["date_to"] = date_to.isoformat()
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                self._build_url("/failures"),
                params=params,
            ) as response:
                return await response.json()
    
    async def get_failure_detail(
        self,
        failure_id: int,
        include_alternatives: bool = True,
    ) -> Dict[str, Any]:
        """
        Get detailed information about a failure.
        
        Args:
            failure_id: The failure ID
            include_alternatives: Whether to include alternatives
            
        Returns:
            API response with failure details
        """
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                self._build_url(f"/failures/{failure_id}"),
                params={"include_alternatives": include_alternatives},
            ) as response:
                return await response.json()
    
    async def approve_selector(
        self,
        failure_id: int,
        selector: str,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Approve an alternative selector.
        
        Args:
            failure_id: The failure ID
            selector: The selector to approve
            notes: Optional approval notes
            
        Returns:
            API response
        """
        import aiohttp
        
        payload = {"selector": selector}
        if notes:
            payload["notes"] = notes
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self._build_url(f"/failures/{failure_id}/approve"),
                json=payload,
            ) as response:
                return await response.json()
    
    async def reject_selector(
        self,
        failure_id: int,
        selector: str,
        reason: str,
        suggested_alternative: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Reject an alternative selector.
        
        Args:
            failure_id: The failure ID
            selector: The selector to reject
            reason: Reason for rejection
            suggested_alternative: Optional suggested alternative
            
        Returns:
            API response
        """
        import aiohttp
        
        payload = {
            "selector": selector,
            "reason": reason,
        }
        if suggested_alternative:
            payload["suggested_alternative"] = suggested_alternative
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self._build_url(f"/failures/{failure_id}/reject"),
                json=payload,
            ) as response:
                return await response.json()
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check API health.
        
        Returns:
            Health status
        """
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            async with session.get(self._build_url("/health")) as response:
                return await response.json()
    
    async def flag_failure(
        self,
        failure_id: int,
        note: str,
    ) -> Dict[str, Any]:
        """
        Flag a selector failure for developer review.
        
        Args:
            failure_id: The failure ID
            note: Note explaining why this needs developer review
            
        Returns:
            API response
        """
        import aiohttp
        
        payload = {"note": note}
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self._build_url(f"/failures/{failure_id}/flag"),
                json=payload,
            ) as response:
                return await response.json()
    
    async def unflag_failure(
        self,
        failure_id: int,
    ) -> Dict[str, Any]:
        """
        Remove flag from a selector failure.
        
        Args:
            failure_id: The failure ID
            
        Returns:
            API response
        """
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            async with session.delete(
                self._build_url(f"/failures/{failure_id}/flag"),
            ) as response:
                return await response.json()


# Synchronous client for simpler use cases
class SyncFailureAPIClient:
    """Synchronous version of the failures API client."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")
    
    def _build_url(self, path: str) -> str:
        return f"{self.base_url}{path}"
    
    def list_failures(
        self,
        sport: Optional[str] = None,
        site: Optional[str] = None,
        error_type: Optional[str] = None,
        severity: Optional[str] = None,
        flagged: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        """List failures (synchronous)."""
        import requests
        
        params = {"page": page, "page_size": page_size}
        if sport:
            params["sport"] = sport
        if site:
            params["site"] = site
        if error_type:
            params["error_type"] = error_type
        if severity:
            params["severity"] = severity
        if flagged is not None:
            params["flagged"] = str(flagged)
        
        response = requests.get(self._build_url("/failures"), params=params)
        response.raise_for_status()
        return response.json()
    
    def get_failure_detail(
        self,
        failure_id: int,
        include_alternatives: bool = True,
    ) -> Dict[str, Any]:
        """Get failure detail (synchronous)."""
        import requests
        
        response = requests.get(
            self._build_url(f"/failures/{failure_id}"),
            params={"include_alternatives": include_alternatives},
        )
        response.raise_for_status()
        return response.json()
    
    def approve_selector(
        self,
        failure_id: int,
        selector: str,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Approve selector (synchronous)."""
        import requests
        
        payload = {"selector": selector}
        if notes:
            payload["notes"] = notes
        
        response = requests.post(
            self._build_url(f"/failures/{failure_id}/approve"),
            json=payload,
        )
        response.raise_for_status()
        return response.json()
    
    def reject_selector(
        self,
        failure_id: int,
        selector: str,
        reason: str,
        suggested_alternative: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Reject selector (synchronous)."""
        import requests
        
        payload = {
            "selector": selector,
            "reason": reason,
        }
        if suggested_alternative:
            payload["suggested_alternative"] = suggested_alternative
        
        response = requests.post(
            self._build_url(f"/failures/{failure_id}/reject"),
            json=payload,
        )
        response.raise_for_status()
        return response.json()
    
    def health_check(self) -> Dict[str, Any]:
        """Health check (synchronous)."""
        import requests
        
        response = requests.get(self._build_url("/health"))
        response.raise_for_status()
        return response.json()
    
    def flag_failure(
        self,
        failure_id: int,
        note: str,
    ) -> Dict[str, Any]:
        """Flag failure for developer review (synchronous)."""
        import requests
        
        payload = {"note": note}
        
        response = requests.post(
            self._build_url(f"/failures/{failure_id}/flag"),
            json=payload,
        )
        response.raise_for_status()
        return response.json()
    
    def unflag_failure(
        self,
        failure_id: int,
    ) -> Dict[str, Any]:
        """Remove flag from failure (synchronous)."""
        import requests
        
        response = requests.delete(
            self._build_url(f"/failures/{failure_id}/flag"),
        )
        response.raise_for_status()
        return response.json()
