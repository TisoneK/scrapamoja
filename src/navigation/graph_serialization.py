"""
Route graph serialization and deserialization

Provides efficient serialization and deserialization of route graphs with compression,
versioning, and integrity checking for storage and transmission.
"""

import json
import pickle
import zlib
import hashlib
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Union
from pathlib import Path
from dataclasses import dataclass, asdict
import base64

from .models import RouteGraph, NavigationRoute, RouteType, TraversalMethod
from .logging_config import get_navigation_logger


@dataclass
class SerializationMetadata:
    """Metadata for serialized route graphs"""
    version: str = "1.0"
    created_at: datetime = None
    created_by: str = "navigation_system"
    compression_algorithm: str = "zlib"
    integrity_checksum: str = ""
    total_routes: int = 0
    total_nodes: int = 0
    total_edges: int = 0
    serialization_format: str = "json"
    compressed_size: int = 0
    uncompressed_size: int = 0


class RouteGraphSerializer:
    """Serializer for route graphs with compression and integrity checking"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize serializer"""
        self.logger = get_navigation_logger("route_graph_serializer")
        self.config = config or {}
        
        # Serialization configuration
        self.default_format = self.config.get("default_format", "json")
        self.enable_compression = self.config.get("enable_compression", True)
        self.compression_level = self.config.get("compression_level", 6)
        self.enable_integrity_check = self.config.get("enable_integrity_check", True)
        
        self.logger.info(
            "Route graph serializer initialized",
            default_format=self.default_format,
            enable_compression=self.enable_compression,
            compression_level=self.compression_level
        )
    
    def serialize(
        self,
        graph: RouteGraph,
        file_path: Optional[str] = None,
        format: Optional[str] = None
    ) -> Union[bytes, str]:
        """Serialize route graph to bytes or file"""
        try:
            serialization_format = format or self.default_format
            
            self.logger.info(
                "Serializing route graph",
                graph_id=graph.graph_id,
                format=serialization_format,
                routes_count=len(graph.routes)
            )
            
            # Convert graph to serializable format
            graph_data = self._graph_to_dict(graph)
            
            # Create metadata
            metadata = SerializationMetadata(
                created_at=datetime.utcnow(),
                total_routes=len(graph.routes),
                total_nodes=len(graph.nodes),
                total_edges=len(graph.edges),
                serialization_format=serialization_format
            )
            
            # Serialize data
            if serialization_format == "json":
                serialized_data = self._serialize_to_json(graph_data, metadata)
            elif serialization_format == "pickle":
                serialized_data = self._serialize_to_pickle(graph_data, metadata)
            else:
                raise ValueError(f"Unsupported serialization format: {serialization_format}")
            
            # Apply compression if enabled
            if self.enable_compression:
                serialized_data = self._compress_data(serialized_data)
                metadata.compression_algorithm = "zlib"
            
            # Calculate integrity checksum
            if self.enable_integrity_check:
                metadata.integrity_checksum = self._calculate_checksum(serialized_data)
            
            # Add metadata to serialized data
            final_data = self._add_metadata(serialized_data, metadata)
            
            # Save to file if path provided
            if file_path:
                self._save_to_file(final_data, file_path, metadata)
                return file_path
            
            return final_data
            
        except Exception as e:
            self.logger.error(
                f"Failed to serialize route graph: {str(e)}",
                graph_id=graph.graph_id
            )
            raise
    
    def deserialize(
        self,
        data: Union[bytes, str, Path],
        format: Optional[str] = None
    ) -> RouteGraph:
        """Deserialize route graph from data or file"""
        try:
            # Handle file path input
            if isinstance(data, (str, Path)):
                data, metadata = self._load_from_file(str(data))
            else:
                data, metadata = self._extract_metadata(data)
            
            serialization_format = format or metadata.serialization_format
            
            self.logger.info(
                "Deserializing route graph",
                format=serialization_format,
                version=metadata.version,
                routes_count=metadata.total_routes
            )
            
            # Verify integrity
            if self.enable_integrity_check and metadata.integrity_checksum:
                calculated_checksum = self._calculate_checksum(data)
                if calculated_checksum != metadata.integrity_checksum:
                    raise ValueError("Integrity checksum mismatch - data may be corrupted")
            
            # Decompress if needed
            if metadata.compression_algorithm == "zlib":
                data = self._decompress_data(data)
            
            # Deserialize data
            if serialization_format == "json":
                graph_data = self._deserialize_from_json(data)
            elif serialization_format == "pickle":
                graph_data = self._deserialize_from_pickle(data)
            else:
                raise ValueError(f"Unsupported serialization format: {serialization_format}")
            
            # Convert back to RouteGraph
            graph = self._dict_to_graph(graph_data)
            
            self.logger.info(
                "Route graph deserialized successfully",
                graph_id=graph.graph_id,
                routes_count=len(graph.routes)
            )
            
            return graph
            
        except Exception as e:
            self.logger.error(
                f"Failed to deserialize route graph: {str(e)}"
            )
            raise
    
    def _graph_to_dict(self, graph: RouteGraph) -> Dict[str, Any]:
        """Convert route graph to dictionary"""
        return {
            "graph_id": graph.graph_id,
            "nodes": list(graph.nodes),
            "edges": [list(edge) for edge in graph.edges],
            "routes": [self._route_to_dict(route) for route in graph.routes.values()],
            "graph_metadata": asdict(graph.graph_metadata) if graph.graph_metadata else {}
        }
    
    def _route_to_dict(self, route: NavigationRoute) -> Dict[str, Any]:
        """Convert navigation route to dictionary"""
        return {
            "route_id": route.route_id,
            "source_url": route.source_url,
            "target_url": route.target_url,
            "route_type": route.route_type.value,
            "traversal_method": route.traversal_method.value,
            "selector": route.selector,
            "confidence_score": route.confidence_score,
            "risk_score": route.risk_score,
            "estimated_duration": route.estimated_duration,
            "metadata": route.metadata or {}
        }
    
    def _dict_to_graph(self, graph_data: Dict[str, Any]) -> RouteGraph:
        """Convert dictionary back to route graph"""
        # Create routes
        routes = {}
        for route_dict in graph_data["routes"]:
            route = NavigationRoute(
                route_id=route_dict["route_id"],
                source_url=route_dict["source_url"],
                target_url=route_dict["target_url"],
                route_type=RouteType(route_dict["route_type"]),
                traversal_method=TraversalMethod(route_dict["traversal_method"]),
                selector=route_dict["selector"],
                confidence_score=route_dict["confidence_score"],
                risk_score=route_dict["risk_score"],
                estimated_duration=route_dict.get("estimated_duration", 0.0),
                metadata=route_dict.get("metadata")
            )
            routes[route.route_id] = route
        
        # Create graph
        graph = RouteGraph(
            graph_id=graph_data["graph_id"],
            routes=routes,
            graph_metadata=graph_data.get("graph_metadata", {})
        )
        
        return graph
    
    def _serialize_to_json(self, data: Dict[str, Any], metadata: SerializationMetadata) -> bytes:
        """Serialize to JSON format"""
        json_data = {
            "metadata": asdict(metadata),
            "data": data
        }
        return json.dumps(json_data, default=str, separators=(',', ':')).encode('utf-8')
    
    def _serialize_to_pickle(self, data: Dict[str, Any], metadata: SerializationMetadata) -> bytes:
        """Serialize to pickle format"""
        pickle_data = {
            "metadata": metadata,
            "data": data
        }
        return pickle.dumps(pickle_data)
    
    def _deserialize_from_json(self, data: bytes) -> Dict[str, Any]:
        """Deserialize from JSON format"""
        json_data = json.loads(data.decode('utf-8'))
        return json_data["data"]
    
    def _deserialize_from_pickle(self, data: bytes) -> Dict[str, Any]:
        """Deserialize from pickle format"""
        pickle_data = pickle.loads(data)
        return pickle_data["data"]
    
    def _compress_data(self, data: bytes) -> bytes:
        """Compress data using zlib"""
        return zlib.compress(data, level=self.compression_level)
    
    def _decompress_data(self, data: bytes) -> bytes:
        """Decompress zlib data"""
        return zlib.decompress(data)
    
    def _calculate_checksum(self, data: bytes) -> str:
        """Calculate SHA-256 checksum"""
        return hashlib.sha256(data).hexdigest()
    
    def _add_metadata(self, data: bytes, metadata: SerializationMetadata) -> bytes:
        """Add metadata to serialized data"""
        # Update metadata with size information
        metadata.uncompressed_size = len(data)
        
        if self.enable_compression:
            metadata.compressed_size = len(self._compress_data(data))
        
        # Serialize metadata
        metadata_json = json.dumps(asdict(metadata), default=str).encode('utf-8')
        
        # Combine metadata and data with separator
        separator = b"__METADATA__"
        return metadata_json + separator + data
    
    def _extract_metadata(self, data: bytes) -> Tuple[bytes, SerializationMetadata]:
        """Extract metadata from serialized data"""
        separator = b"__METADATA__"
        
        if separator not in data:
            # Legacy format without metadata
            metadata = SerializationMetadata()
            return data, metadata
        
        # Split metadata and data
        metadata_json, serialized_data = data.split(separator, 1)
        
        # Parse metadata
        metadata_dict = json.loads(metadata_json.decode('utf-8'))
        metadata_dict["created_at"] = datetime.fromisoformat(metadata_dict["created_at"])
        metadata = SerializationMetadata(**metadata_dict)
        
        return serialized_data, metadata
    
    def _save_to_file(self, data: bytes, file_path: str, metadata: SerializationMetadata) -> None:
        """Save serialized data to file"""
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'wb') as f:
            f.write(data)
        
        self.logger.info(
            "Route graph saved to file",
            file_path=file_path,
            size_bytes=len(data),
            compressed_size=metadata.compressed_size
        )
    
    def _load_from_file(self, file_path: str) -> Tuple[bytes, SerializationMetadata]:
        """Load serialized data from file"""
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        with open(path, 'rb') as f:
            data = f.read()
        
        return self._extract_metadata(data)


class RouteGraphCache:
    """Cache for serialized route graphs"""
    
    def __init__(self, cache_dir: str = "data/navigation/cache", max_size_mb: int = 100):
        """Initialize cache"""
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.logger = get_navigation_logger("route_graph_cache")
        
        self.logger.info(
            "Route graph cache initialized",
            cache_dir=str(self.cache_dir),
            max_size_mb=max_size_mb
        )
    
    def get(self, graph_id: str) -> Optional[RouteGraph]:
        """Get cached route graph"""
        try:
            cache_file = self.cache_dir / f"{graph_id}.graph"
            
            if not cache_file.exists():
                return None
            
            # Check if cache is stale (older than 1 hour)
            if self._is_cache_stale(cache_file):
                cache_file.unlink()
                return None
            
            serializer = RouteGraphSerializer()
            return serializer.deserialize(cache_file)
            
        except Exception as e:
            self.logger.error(
                f"Failed to load cached graph: {str(e)}",
                graph_id=graph_id
            )
            return None
    
    def put(self, graph: RouteGraph, ttl_hours: int = 1) -> None:
        """Cache route graph"""
        try:
            cache_file = self.cache_dir / f"{graph.graph_id}.graph"
            
            serializer = RouteGraphSerializer()
            serializer.serialize(graph, str(cache_file))
            
            # Set expiration time
            expiration_time = datetime.utcnow().timestamp() + (ttl_hours * 3600)
            expiration_file = self.cache_dir / f"{graph.graph_id}.exp"
            expiration_file.write_text(str(expiration_time))
            
            # Clean up if cache is too large
            self._cleanup_cache()
            
            self.logger.debug(
                "Route graph cached",
                graph_id=graph.graph_id,
                ttl_hours=ttl_hours
            )
            
        except Exception as e:
            self.logger.error(
                f"Failed to cache graph: {str(e)}",
                graph_id=graph.graph_id
            )
    
    def invalidate(self, graph_id: str) -> None:
        """Invalidate cached route graph"""
        try:
            cache_file = self.cache_dir / f"{graph_id}.graph"
            expiration_file = self.cache_dir / f"{graph_id}.exp"
            
            if cache_file.exists():
                cache_file.unlink()
            
            if expiration_file.exists():
                expiration_file.unlink()
            
            self.logger.debug(
                "Route graph cache invalidated",
                graph_id=graph_id
            )
            
        except Exception as e:
            self.logger.error(
                f"Failed to invalidate cache: {str(e)}",
                graph_id=graph_id
            )
    
    def clear(self) -> None:
        """Clear all cached graphs"""
        try:
            for file in self.cache_dir.glob("*.graph"):
                file.unlink()
            
            for file in self.cache_dir.glob("*.exp"):
                file.unlink()
            
            self.logger.info("Route graph cache cleared")
            
        except Exception as e:
            self.logger.error(f"Failed to clear cache: {str(e)}")
    
    def _is_cache_stale(self, cache_file: Path) -> bool:
        """Check if cache file is stale"""
        expiration_file = self.cache_dir / f"{cache_file.stem}.exp"
        
        if not expiration_file.exists():
            # No expiration file, assume stale
            return True
        
        try:
            expiration_time = float(expiration_file.read_text())
            return datetime.utcnow().timestamp() > expiration_time
        except:
            return True
    
    def _cleanup_cache(self) -> None:
        """Clean up cache if it exceeds size limit"""
        try:
            total_size = sum(f.stat().st_size for f in self.cache_dir.glob("*.graph"))
            
            if total_size > self.max_size_bytes:
                # Sort files by modification time and remove oldest
                cache_files = sorted(
                    self.cache_dir.glob("*.graph"),
                    key=lambda f: f.stat().st_mtime
                )
                
                for cache_file in cache_files:
                    cache_file.unlink()
                    expiration_file = self.cache_dir / f"{cache_file.stem}.exp"
                    if expiration_file.exists():
                        expiration_file.unlink()
                    
                    total_size -= cache_file.stat().st_size
                    if total_size <= self.max_size_bytes * 0.8:  # Leave 20% headroom
                        break
                
                self.logger.info(
                    "Cache cleanup completed",
                    files_removed=len(cache_files)
                )
                
        except Exception as e:
            self.logger.error(f"Failed to cleanup cache: {str(e)}")


def create_route_graph_serializer(config: Optional[Dict[str, Any]] = None) -> RouteGraphSerializer:
    """Create route graph serializer"""
    return RouteGraphSerializer(config)


def create_route_graph_cache(cache_dir: str = "data/navigation/cache", max_size_mb: int = 100) -> RouteGraphCache:
    """Create route graph cache"""
    return RouteGraphCache(cache_dir, max_size_mb)
