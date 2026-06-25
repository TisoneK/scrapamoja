"""
Context detection system for hierarchical selector management.

This module provides automatic detection of navigation contexts
based on DOM analysis and URL patterns.
"""

import re
import logging
from typing import Dict, List, Optional, Set, Tuple, Any
from urllib.parse import urlparse, parse_qs
from dataclasses import dataclass

from .context_manager import SelectorContext, DOMState
from .navigation_tracker import NavigationStateTracker


logger = logging.getLogger(__name__)


@dataclass
class ContextDetectionResult:
    """Result of context detection."""
    primary_context: Optional[str]
    secondary_context: Optional[str]
    tertiary_context: Optional[str]
    confidence: float
    evidence: List[str]
    metadata: Dict[str, Any]


class PrimaryContextDetector:
    """
    Detects primary navigation contexts (authentication, navigation, extraction, filtering).
    """
    
    # URL patterns for primary contexts
    URL_PATTERNS = {
        'authentication': [
            r'/login',
            r'/signin',
            r'/auth',
            r'/oauth',
            r'/consent',
            r'/cookie'
        ],
        'navigation': [
            r'/',
            r'/home',
            r'/menu',
            r'/sports',
            r'/categories'
        ],
        'extraction': [
            r'/match',
            r'/game',
            r'/event',
            r'/fixture',
            r'/live',
            r'/results'
        ],
        'filtering': [
            r'/filter',
            r'/search',
            r'/date',
            r'/competition',
            r'/league',
            r'/country'
        ]
    }
    
    # DOM element patterns for primary contexts
    DOM_PATTERNS = {
        'authentication': [
            'login',
            'signin',
            'password',
            'username',
            'email',
            'auth-form',
            'consent-dialog',
            'cookie-banner',
            'login-button'
        ],
        'navigation': [
            'nav',
            'menu',
            'sport-menu',
            'navigation',
            'header-nav',
            'main-menu',
            'sport-list'
        ],
        'extraction': [
            'match-list',
            'game-card',
            'event-item',
            'fixture',
            'live-match',
            'score-board',
            'match-details'
        ],
        'filtering': [
            'filter',
            'search',
            'date-filter',
            'competition-filter',
            'league-select',
            'country-filter',
            'search-box'
        ]
    }
    
    def __init__(self):
        """Initialize primary context detector."""
        # Compile regex patterns for efficiency
        self.compiled_url_patterns = {}
        for context, patterns in self.URL_PATTERNS.items():
            self.compiled_url_patterns[context] = [
                re.compile(pattern, re.IGNORECASE) for pattern in patterns
            ]
        
        self.compiled_dom_patterns = {}
        for context, patterns in self.DOM_PATTERNS.items():
            self.compiled_dom_patterns[context] = [
                re.compile(pattern, re.IGNORECASE) for pattern in patterns
            ]
    
    def detect_from_url(self, url: str) -> ContextDetectionResult:
        """
        Detect primary context from URL.
        
        Args:
            url: Current page URL
            
        Returns:
            ContextDetectionResult: Detection result
        """
        scores = {}
        evidence = {}
        
        for context, patterns in self.compiled_url_patterns.items():
            score = 0
            context_evidence = []
            
            for pattern in patterns:
                if pattern.search(url):
                    score += 1
                    context_evidence.append(f"URL pattern: {pattern.pattern}")
            
            scores[context] = score
            evidence[context] = context_evidence
        
        # Determine best match
        if not scores or max(scores.values()) == 0:
            return ContextDetectionResult(
                primary_context=None,
                secondary_context=None,
                tertiary_context=None,
                confidence=0.0,
                evidence=[],
                metadata={"method": "url", "url": url}
            )
        
        best_context = max(scores, key=scores.get)
        confidence = min(scores[best_context] / len(self.URL_PATTERNS[best_context]), 1.0)
        
        return ContextDetectionResult(
            primary_context=best_context,
            secondary_context=None,
            tertiary_context=None,
            confidence=confidence,
            evidence=evidence[best_context],
            metadata={"method": "url", "url": url, "scores": scores}
        )
    
    def detect_from_dom_content(self, html_content: str) -> ContextDetectionResult:
        """
        Detect primary context from DOM content.
        
        Args:
            html_content: HTML content of the page
            
        Returns:
            ContextDetectionResult: Detection result
        """
        content_lower = html_content.lower()
        scores = {}
        evidence = {}
        
        for context, patterns in self.compiled_dom_patterns.items():
            score = 0
            context_evidence = []
            
            for pattern in patterns:
                matches = pattern.findall(content_lower)
                if matches:
                    score += len(matches)
                    context_evidence.append(f"DOM pattern: {pattern.pattern} ({len(matches)} matches)")
            
            scores[context] = score
            evidence[context] = context_evidence
        
        # Determine best match
        if not scores or max(scores.values()) == 0:
            return ContextDetectionResult(
                primary_context=None,
                secondary_context=None,
                tertiary_context=None,
                confidence=0.0,
                evidence=[],
                metadata={"method": "dom", "content_length": len(html_content)}
            )
        
        best_context = max(scores, key=scores.get)
        
        # Normalize confidence based on content size
        max_possible_score = len(self.DOM_PATTERNS[best_context]) * 10  # Assume max 10 matches per pattern
        confidence = min(scores[best_context] / max_possible_score, 1.0)
        
        return ContextDetectionResult(
            primary_context=best_context,
            secondary_context=None,
            tertiary_context=None,
            confidence=confidence,
            evidence=evidence[best_context],
            metadata={"method": "dom", "scores": scores}
        )
    
    def detect_from_page_title(self, title: str) -> ContextDetectionResult:
        """
        Detect primary context from page title.
        
        Args:
            title: Page title
            
        Returns:
            ContextDetectionResult: Detection result
        """
        title_lower = title.lower()
        scores = {}
        evidence = {}
        
        for context, patterns in self.compiled_dom_patterns.items():
            score = 0
            context_evidence = []
            
            for pattern in patterns:
                if pattern.search(title_lower):
                    score += 2  # Weight title matches higher
                    context_evidence.append(f"Title pattern: {pattern.pattern}")
            
            scores[context] = score
            evidence[context] = context_evidence
        
        # Determine best match
        if not scores or max(scores.values()) == 0:
            return ContextDetectionResult(
                primary_context=None,
                secondary_context=None,
                tertiary_context=None,
                confidence=0.0,
                evidence=[],
                metadata={"method": "title", "title": title}
            )
        
        best_context = max(scores, key=scores.get)
        confidence = min(scores[best_context] / (len(self.DOM_PATTERNS[best_context]) * 2), 1.0)
        
        return ContextDetectionResult(
            primary_context=best_context,
            secondary_context=None,
            tertiary_context=None,
            confidence=confidence,
            evidence=evidence[best_context],
            metadata={"method": "title", "title": title}
        )


class SecondaryContextDetector:
    """
    Detects secondary navigation contexts within extraction.
    """
    
    # Patterns for extraction secondary contexts
    EXTRACTION_PATTERNS = {
        'match_list': [
            r'/matches',
            r'/games',
            r'/fixtures',
            r'/schedule',
            r'/live',
            r'match-list',
            'game-list',
            'fixture-list'
        ],
        'match_summary': [
            r'/summary',
            r'/overview',
            r'/details',
            r'/info',
            'match-summary',
            'game-details',
            'event-info'
        ],
        'match_h2h': [
            r'/h2h',
            r'/head-to-head',
            r'/history',
            r'/versus',
            r'/vs',
            'h2h-stats',
            'head-to-head'
        ],
        'match_odds': [
            r'/odds',
            r'/betting',
            r'/price',
            r'/market',
            r'/bookmaker',
            'odds-table',
            'betting-odds'
        ],
        'match_stats': [
            r'/stats',
            r'/statistics',
            r'/performance',
            r'/analysis',
            'match-stats',
            'game-stats',
            'statistical'
        ]
    }
    
    def __init__(self):
        """Initialize secondary context detector."""
        self.compiled_patterns = {}
        for context, patterns in self.EXTRACTION_PATTERNS.items():
            self.compiled_patterns[context] = [
                re.compile(pattern, re.IGNORECASE) for pattern in patterns
            ]
    
    def detect_from_url(self, url: str, primary_context: str) -> ContextDetectionResult:
        """
        Detect secondary context from URL.
        
        Args:
            url: Current page URL
            primary_context: Already detected primary context
            
        Returns:
            ContextDetectionResult: Detection result
        """
        if primary_context != 'extraction':
            return ContextDetectionResult(
                primary_context=primary_context,
                secondary_context=None,
                tertiary_context=None,
                confidence=0.0,
                evidence=[],
                metadata={"method": "url", "reason": "not_extraction_context"}
            )
        
        scores = {}
        evidence = {}
        
        for context, patterns in self.compiled_patterns.items():
            score = 0
            context_evidence = []
            
            for pattern in patterns:
                if pattern.search(url):
                    score += 1
                    context_evidence.append(f"URL pattern: {pattern.pattern}")
            
            scores[context] = score
            evidence[context] = context_evidence
        
        # Determine best match
        if not scores or max(scores.values()) == 0:
            return ContextDetectionResult(
                primary_context=primary_context,
                secondary_context=None,
                tertiary_context=None,
                confidence=0.0,
                evidence=[],
                metadata={"method": "url", "url": url}
            )
        
        best_context = max(scores, key=scores.get)
        confidence = min(scores[best_context] / len(self.EXTRACTION_PATTERNS[best_context]), 1.0)
        
        return ContextDetectionResult(
            primary_context=primary_context,
            secondary_context=best_context,
            tertiary_context=None,
            confidence=confidence,
            evidence=evidence[best_context],
            metadata={"method": "url", "url": url, "scores": scores}
        )
    
    def detect_from_dom_content(self, html_content: str, primary_context: str) -> ContextDetectionResult:
        """
        Detect secondary context from DOM content.
        
        Args:
            html_content: HTML content of the page
            primary_context: Already detected primary context
            
        Returns:
            ContextDetectionResult: Detection result
        """
        if primary_context != 'extraction':
            return ContextDetectionResult(
                primary_context=primary_context,
                secondary_context=None,
                tertiary_context=None,
                confidence=0.0,
                evidence=[],
                metadata={"method": "dom", "reason": "not_extraction_context"}
            )
        
        content_lower = html_content.lower()
        scores = {}
        evidence = {}
        
        for context, patterns in self.compiled_patterns.items():
            score = 0
            context_evidence = []
            
            for pattern in patterns:
                matches = pattern.findall(content_lower)
                if matches:
                    score += len(matches)
                    context_evidence.append(f"DOM pattern: {pattern.pattern} ({len(matches)} matches)")
            
            scores[context] = score
            evidence[context] = context_evidence
        
        # Determine best match
        if not scores or max(scores.values()) == 0:
            return ContextDetectionResult(
                primary_context=primary_context,
                secondary_context=None,
                tertiary_context=None,
                confidence=0.0,
                evidence=[],
                metadata={"method": "dom", "content_length": len(html_content)}
            )
        
        best_context = max(scores, key=scores.get)
        max_possible_score = len(self.EXTRACTION_PATTERNS[best_context]) * 5
        confidence = min(scores[best_context] / max_possible_score, 1.0)
        
        return ContextDetectionResult(
            primary_context=primary_context,
            secondary_context=best_context,
            tertiary_context=None,
            confidence=confidence,
            evidence=evidence[best_context],
            metadata={"method": "dom", "scores": scores}
        )


class TertiaryContextDetector:
    """
    Detects tertiary navigation contexts within match_stats.
    """
    
    # Patterns for match_stats tertiary contexts
    MATCH_STATS_PATTERNS = {
        'inc_ot': [
            r'/incidents',
            r'/overtime',
            r'/events',
            r'/timeline',
            'incidents-tab',
            'overtime-stats',
            'match-events'
        ],
        'ft': [
            r'/full-time',
            r'/final',
            r'/complete',
            r'/ft',
            'full-time-stats',
            'final-result',
            'complete-match'
        ],
        'q1': [
            r'/q1',
            r'/quarter1',
            r'/first-quarter',
            'q1-stats',
            'first-quarter',
            'quarter1-stats'
        ],
        'q2': [
            r'/q2',
            r'/quarter2',
            r'/second-quarter',
            'q2-stats',
            'second-quarter',
            'quarter2-stats'
        ],
        'q3': [
            r'/q3',
            r'/quarter3',
            r'/third-quarter',
            'q3-stats',
            'third-quarter',
            'quarter3-stats'
        ],
        'q4': [
            r'/q4',
            r'/quarter4',
            r'/fourth-quarter',
            'q4-stats',
            'fourth-quarter',
            'quarter4-stats'
        ]
    }
    
    def __init__(self):
        """Initialize tertiary context detector."""
        self.compiled_patterns = {}
        for context, patterns in self.MATCH_STATS_PATTERNS.items():
            self.compiled_patterns[context] = [
                re.compile(pattern, re.IGNORECASE) for pattern in patterns
            ]
    
    def detect_from_url(self, url: str, primary_context: str, secondary_context: str) -> ContextDetectionResult:
        """
        Detect tertiary context from URL.
        
        Args:
            url: Current page URL
            primary_context: Already detected primary context
            secondary_context: Already detected secondary context
            
        Returns:
            ContextDetectionResult: Detection result
        """
        if primary_context != 'extraction' or secondary_context != 'match_stats':
            return ContextDetectionResult(
                primary_context=primary_context,
                secondary_context=secondary_context,
                tertiary_context=None,
                confidence=0.0,
                evidence=[],
                metadata={"method": "url", "reason": "not_match_stats_context"}
            )
        
        scores = {}
        evidence = {}
        
        for context, patterns in self.compiled_patterns.items():
            score = 0
            context_evidence = []
            
            for pattern in patterns:
                if pattern.search(url):
                    score += 1
                    context_evidence.append(f"URL pattern: {pattern.pattern}")
            
            scores[context] = score
            evidence[context] = context_evidence
        
        # Determine best match
        if not scores or max(scores.values()) == 0:
            return ContextDetectionResult(
                primary_context=primary_context,
                secondary_context=secondary_context,
                tertiary_context=None,
                confidence=0.0,
                evidence=[],
                metadata={"method": "url", "url": url}
            )
        
        best_context = max(scores, key=scores.get)
        confidence = min(scores[best_context] / len(self.MATCH_STATS_PATTERNS[best_context]), 1.0)
        
        return ContextDetectionResult(
            primary_context=primary_context,
            secondary_context=secondary_context,
            tertiary_context=best_context,
            confidence=confidence,
            evidence=evidence[best_context],
            metadata={"method": "url", "url": url, "scores": scores}
        )
    
    def detect_from_dom_content(self, html_content: str, primary_context: str, secondary_context: str) -> ContextDetectionResult:
        """
        Detect tertiary context from DOM content.
        
        Args:
            html_content: HTML content of the page
            primary_context: Already detected primary context
            secondary_context: Already detected secondary context
            
        Returns:
            ContextDetectionResult: Detection result
        """
        if primary_context != 'extraction' or secondary_context != 'match_stats':
            return ContextDetectionResult(
                primary_context=primary_context,
                secondary_context=secondary_context,
                tertiary_context=None,
                confidence=0.0,
                evidence=[],
                metadata={"method": "dom", "reason": "not_match_stats_context"}
            )
        
        content_lower = html_content.lower()
        scores = {}
        evidence = {}
        
        for context, patterns in self.compiled_patterns.items():
            score = 0
            context_evidence = []
            
            for pattern in patterns:
                matches = pattern.findall(content_lower)
                if matches:
                    score += len(matches)
                    context_evidence.append(f"DOM pattern: {pattern.pattern} ({len(matches)} matches)")
            
            scores[context] = score
            evidence[context] = context_evidence
        
        # Determine best match
        if not scores or max(scores.values()) == 0:
            return ContextDetectionResult(
                primary_context=primary_context,
                secondary_context=secondary_context,
                tertiary_context=None,
                confidence=0.0,
                evidence=[],
                metadata={"method": "dom", "content_length": len(html_content)}
            )
        
        best_context = max(scores, key=scores.get)
        max_possible_score = len(self.MATCH_STATS_PATTERNS[best_context]) * 3
        confidence = min(scores[best_context] / max_possible_score, 1.0)
        
        return ContextDetectionResult(
            primary_context=primary_context,
            secondary_context=secondary_context,
            tertiary_context=best_context,
            confidence=confidence,
            evidence=evidence[best_context],
            metadata={"method": "dom", "scores": scores}
        )


class ContextDetectionEngine:
    """
    Main engine for context detection combining all detectors.
    """
    
    def __init__(self):
        """Initialize context detection engine."""
        self.primary_detector = PrimaryContextDetector()
        self.secondary_detector = SecondaryContextDetector()
        self.tertiary_detector = TertiaryContextDetector()
        
        logger.info("ContextDetectionEngine initialized")
    
    async def detect_context(
        self,
        url: str,
        html_content: Optional[str] = None,
        page_title: Optional[str] = None,
        previous_context: Optional[SelectorContext] = None
    ) -> ContextDetectionResult:
        """
        Detect context using all available methods.
        
        Args:
            url: Current page URL
            html_content: HTML content (optional)
            page_title: Page title (optional)
            previous_context: Previously detected context (optional)
            
        Returns:
            ContextDetectionResult: Best detection result
        """
        results = []
        
        # Primary context detection
        primary_results = []
        
        # From URL
        url_result = self.primary_detector.detect_from_url(url)
        primary_results.append(url_result)
        
        # From DOM content if available
        if html_content:
            dom_result = self.primary_detector.detect_from_dom_content(html_content)
            primary_results.append(dom_result)
        
        # From page title if available
        if page_title:
            title_result = self.primary_detector.detect_from_page_title(page_title)
            primary_results.append(title_result)
        
        # Select best primary result
        best_primary = max(
            [r for r in primary_results if r.primary_context],
            key=lambda r: r.confidence,
            default=ContextDetectionResult(
                primary_context=None, secondary_context=None, tertiary_context=None,
                confidence=0.0, evidence=[], metadata={}
            )
        )
        
        if not best_primary.primary_context:
            return ContextDetectionResult(
                primary_context=None,
                secondary_context=None,
                tertiary_context=None,
                confidence=0.0,
                evidence=["No primary context detected"],
                metadata={"method": "combined", "url": url}
            )
        
        # Secondary context detection (only if primary is extraction)
        secondary_result = ContextDetectionResult(
            primary_context=best_primary.primary_context,
            secondary_context=None,
            tertiary_context=None,
            confidence=0.0,
            evidence=[],
            metadata={}
        )
        
        if best_primary.primary_context == 'extraction':
            secondary_results = []
            
            # From URL
            url_sec_result = self.secondary_detector.detect_from_url(url, best_primary.primary_context)
            secondary_results.append(url_sec_result)
            
            # From DOM content if available
            if html_content:
                dom_sec_result = self.secondary_detector.detect_from_dom_content(html_content, best_primary.primary_context)
                secondary_results.append(dom_sec_result)
            
            # Select best secondary result
            secondary_result = max(
                [r for r in secondary_results if r.secondary_context],
                key=lambda r: r.confidence,
                default=secondary_result
            )
        
        # Tertiary context detection (only if secondary is match_stats)
        tertiary_result = ContextDetectionResult(
            primary_context=best_primary.primary_context,
            secondary_context=secondary_result.secondary_context,
            tertiary_context=None,
            confidence=0.0,
            evidence=[],
            metadata={}
        )
        
        if secondary_result.secondary_context == 'match_stats':
            tertiary_results = []
            
            # From URL
            url_tert_result = self.tertiary_detector.detect_from_url(
                url, best_primary.primary_context, secondary_result.secondary_context
            )
            tertiary_results.append(url_tert_result)
            
            # From DOM content if available
            if html_content:
                dom_tert_result = self.tertiary_detector.detect_from_dom_content(
                    html_content, best_primary.primary_context, secondary_result.secondary_context
                )
                tertiary_results.append(dom_tert_result)
            
            # Select best tertiary result
            tertiary_result = max(
                [r for r in tertiary_results if r.tertiary_context],
                key=lambda r: r.confidence,
                default=tertiary_result
            )
        
        # Combine results
        combined_evidence = []
        combined_evidence.extend(best_primary.evidence)
        combined_evidence.extend(secondary_result.evidence)
        combined_evidence.extend(tertiary_result.evidence)
        
        # Calculate overall confidence
        confidences = [
            best_primary.confidence,
            secondary_result.confidence,
            tertiary_result.confidence
        ]
        overall_confidence = sum(c for c in confidences if c > 0) / len([c for c in confidences if c > 0])
        
        return ContextDetectionResult(
            primary_context=best_primary.primary_context,
            secondary_context=secondary_result.secondary_context,
            tertiary_context=tertiary_result.tertiary_context,
            confidence=overall_confidence,
            evidence=combined_evidence,
            metadata={
                "method": "combined",
                "primary_confidence": best_primary.confidence,
                "secondary_confidence": secondary_result.confidence,
                "tertiary_confidence": tertiary_result.confidence,
                "url": url
            }
        )


# Global detection engine instance
_detection_engine: Optional[ContextDetectionEngine] = None


def get_context_detection_engine() -> ContextDetectionEngine:
    """
    Get the global context detection engine.
    
    Returns:
        ContextDetectionEngine: Global detection engine instance
    """
    global _detection_engine
    
    if _detection_engine is None:
        _detection_engine = ContextDetectionEngine()
    
    return _detection_engine
