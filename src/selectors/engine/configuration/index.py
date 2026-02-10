"""
Semantic index for fast selector lookup and resolution.

This module provides indexing functionality for semantic selector names,
enabling fast lookup independent of file location and supporting conflict detection.
"""

import asyncio
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from datetime import datetime

from ...models.selector_config import (
    SelectorConfiguration,
    SemanticSelector,
    SemanticIndexEntry,
    ResolutionContext,
    ConfigurationState
)


class ISemanticIndex(ABC):
    """Interface for semantic selector indexing."""
    
    @abstractmethod
    async def build_index(self, configurations: Dict[str, SelectorConfiguration]) -> Dict[str, SemanticIndexEntry]:
        """Build semantic index from loaded configurations."""
        pass
    
    @abstractmethod
    def lookup_selector(self, semantic_name: str, context: Optional[str] = None) -> Optional[SemanticIndexEntry]:
        """Look up a selector by semantic name."""
        pass
    
    @abstractmethod
    def find_conflicts(self) -> Dict[str, List[SemanticIndexEntry]]:
        """Find conflicting selector names."""
        pass
    
    @abstractmethod
    async def update_index(self, file_path: str, config: SelectorConfiguration) -> None:
        """Update index for a specific configuration."""
        pass
    
    @abstractmethod
    async def remove_from_index(self, file_path: str) -> None:
        """Remove entries for a specific configuration."""
        pass


class SemanticIndex(ISemanticIndex):
    """Implementation for semantic selector indexing."""
    
    def __init__(self):
        """Initialize the semantic index."""
        self._index: Dict[str, SemanticIndexEntry] = {}
        self._context_index: Dict[str, Dict[str, SemanticIndexEntry]] = {}
        self._file_index: Dict[str, Set[str]] = {}
        self._correlation_counter = 0
    
    def _generate_correlation_id(self) -> str:
        """Generate a unique correlation ID for tracking operations."""
        self._correlation_counter += 1
        return f"semantic_index_{self._correlation_counter}_{datetime.now().isoformat()}"
    
    async def build_index(self, configurations: Dict[str, SelectorConfiguration]) -> Dict[str, SemanticIndexEntry]:
        """Build semantic index from loaded configurations."""
        correlation_id = self._generate_correlation_id()
        
        # Clear existing index
        self._index.clear()
        self._context_index.clear()
        self._file_index.clear()
        
        # Build index from all configurations
        for file_path, config in configurations.items():
            await self._add_configuration_to_index(file_path, config, correlation_id)
        
        return self._index.copy()
    
    def lookup_selector(self, semantic_name: str, context: Optional[str] = None) -> Optional[SemanticIndexEntry]:
        """Look up a selector by semantic name."""
        if context:
            # Context-aware lookup
            if context in self._context_index and semantic_name in self._context_index[context]:
                return self._context_index[context][semantic_name]
            
            # Try parent context lookup
            parent_contexts = self._get_parent_contexts(context)
            for parent_context in parent_contexts:
                if (parent_context in self._context_index and 
                    semantic_name in self._context_index[parent_context]):
                    return self._context_index[parent_context][semantic_name]
        
        # Global lookup
        return self._index.get(semantic_name)
    
    def find_conflicts(self) -> Dict[str, List[SemanticIndexEntry]]:
        """Find conflicting selector names."""
        conflicts: Dict[str, List[SemanticIndexEntry]] = {}
        
        # Group entries by semantic name
        name_groups: Dict[str, List[SemanticIndexEntry]] = {}
        for entry in self._index.values():
            if entry.semantic_name not in name_groups:
                name_groups[entry.semantic_name] = []
            name_groups[entry.semantic_name].append(entry)
        
        # Find conflicts (multiple entries with same name)
        for name, entries in name_groups.items():
            if len(entries) > 1:
                # Check if they're in different contexts
                contexts = set(entry.context for entry in entries)
                if len(contexts) > 1:
                    conflicts[name] = entries
        
        return conflicts
    
    async def update_index(self, file_path: str, config: SelectorConfiguration) -> None:
        """Update index for a specific configuration."""
        correlation_id = self._generate_correlation_id()
        
        # Remove existing entries for this file
        await self.remove_from_index(file_path)
        
        # Add new entries
        await self._add_configuration_to_index(file_path, config, correlation_id)
    
    async def remove_from_index(self, file_path: str) -> None:
        """Remove entries for a specific configuration."""
        if file_path not in self._file_index:
            return
        
        semantic_names_to_remove = self._file_index[file_path]
        
        for semantic_name in semantic_names_to_remove:
            if semantic_name in self._index:
                entry = self._index[semantic_name]
                
                # Remove from main index
                del self._index[semantic_name]
                
                # Remove from context index
                if entry.context in self._context_index:
                    if semantic_name in self._context_index[entry.context]:
                        del self._context_index[entry.context][semantic_name]
                    
                    # Clean up empty context entries
                    if not self._context_index[entry.context]:
                        del self._context_index[entry.context]
        
        # Remove from file index
        del self._file_index[file_path]
    
    def get_selectors_by_context(self, context: str) -> List[SemanticIndexEntry]:
        """Get all selectors for a specific context."""
        if context not in self._context_index:
            return []
        
        return list(self._context_index[context].values())
    
    def get_available_contexts(self) -> List[str]:
        """Get all available contexts."""
        return list(self._context_index.keys())
    
    def get_index_stats(self) -> Dict[str, int]:
        """Get index statistics."""
        return {
            "total_selectors": len(self._index),
            "total_contexts": len(self._context_index),
            "total_files": len(self._file_index),
            "conflicts": len(self.find_conflicts())
        }
    
    async def _add_configuration_to_index(self, file_path: str, config: SelectorConfiguration, correlation_id: str) -> None:
        """Add a configuration to the index."""
        # Track semantic names for this file
        semantic_names = set()
        
        # Add selectors to index
        for selector_name, selector in config.selectors.items():
            # Create index entry
            entry = SemanticIndexEntry(
                semantic_name=selector_name,
                context=selector.context,
                file_path=file_path,
                resolved_selector=selector,
                last_modified=datetime.now().isoformat()
            )
            
            # Add to main index
            self._index[selector_name] = entry
            
            # Add to context index
            if selector.context not in self._context_index:
                self._context_index[selector.context] = {}
            self._context_index[selector.context][selector_name] = entry
            
            semantic_names.add(selector_name)
        
        # Track which semantic names belong to this file
        self._file_index[file_path] = semantic_names
    
    def _get_parent_contexts(self, context: str) -> List[str]:
        """Get parent contexts for context-aware lookup."""
        parts = context.split('.')
        parent_contexts = []
        
        for i in range(len(parts) - 1, 0, -1):
            parent_context = '.'.join(parts[:i])
            parent_contexts.append(parent_context)
        
        return parent_contexts
    
    def validate_selector_context(self, semantic_name: str, context: str) -> bool:
        """Validate that a selector is appropriate for a context."""
        entry = self.lookup_selector(semantic_name)
        if not entry:
            return False
        
        # Check if selector context matches or is a parent of the requested context
        if entry.context == context:
            return True
        
        # Check if selector context is a parent of the requested context
        if context.startswith(entry.context + '.'):
            return True
        
        return False
    
    def suggest_selectors(self, partial_name: str, context: Optional[str] = None, limit: int = 10) -> List[str]:
        """Suggest selector names based on partial match."""
        suggestions = []
        
        # Get candidate selectors
        candidates = self._index.values()
        if context:
            candidates = [entry for entry in candidates if entry.context == context]
        
        # Find partial matches
        for entry in candidates:
            if partial_name.lower() in entry.semantic_name.lower():
                suggestions.append(entry.semantic_name)
                if len(suggestions) >= limit:
                    break
        
        return suggestions
    
    def get_selector_usage_stats(self) -> Dict[str, Dict[str, int]]:
        """Get usage statistics for selectors by context."""
        stats: Dict[str, Dict[str, int]] = {}
        
        for context, selectors in self._context_index.items():
            stats[context] = {
                "selector_count": len(selectors),
                "unique_templates": len(set(s.resolved_selector.strategies[0].type for s in selectors.values() if s.resolved_selector.strategies))
            }
        
        return stats
    
    async def rebuild_index_incremental(self, changed_files: List[str], configurations: Dict[str, SelectorConfiguration]) -> None:
        """Rebuild index incrementally for changed files."""
        correlation_id = self._generate_correlation_id()
        
        # Remove entries for changed files
        for file_path in changed_files:
            await self.remove_from_index(file_path)
        
        # Add updated entries
        for file_path in changed_files:
            if file_path in configurations:
                await self._add_configuration_to_index(file_path, configurations[file_path], correlation_id)
    
    def clear_index(self) -> None:
        """Clear the entire index."""
        self._index.clear()
        self._context_index.clear()
        self._file_index.clear()
    
    def export_index_data(self) -> Dict:
        """Export index data for debugging or analysis."""
        return {
            "index": {
                name: {
                    "context": entry.context,
                    "file_path": entry.file_path,
                    "last_modified": entry.last_modified
                }
                for name, entry in self._index.items()
            },
            "contexts": {
                context: list(selectors.keys())
                for context, selectors in self._context_index.items()
            },
            "files": {
                file_path: list(names)
                for file_path, names in self._file_index.items()
            },
            "stats": self.get_index_stats()
        }
