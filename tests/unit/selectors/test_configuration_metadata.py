"""
Unit tests for ConfigurationMetadata recipe metadata fields.

Tests the new recipe versioning and stability tracking fields
that were added to support the adaptive selector system.
"""

import pytest
import yaml
from dataclasses import asdict

from src.selectors.models.selector_config import ConfigurationMetadata


class TestConfigurationMetadataValidation:
    """Test cases for ConfigurationMetadata validation."""
    
    def test_create_metadata_with_all_new_fields(self):
        """Test creating metadata with all new recipe fields populated."""
        metadata = ConfigurationMetadata(
            version="1.0.0",
            last_updated="2026-03-02T12:00:00Z",
            description="Test configuration with recipe metadata",
            recipe_id="recipe-001",
            stability_score=0.85,
            generation=1,
            parent_recipe_id=None
        )
        
        assert metadata.recipe_id == "recipe-001"
        assert metadata.stability_score == 0.85
        assert metadata.generation == 1
        assert metadata.parent_recipe_id is None
    
    def test_create_metadata_without_new_fields_backward_compatible(self):
        """Test that existing configs without new fields still work."""
        metadata = ConfigurationMetadata(
            version="1.0.0",
            last_updated="2026-03-02T12:00:00Z",
            description="Legacy configuration"
        )
        
        # New fields should default to None
        assert metadata.recipe_id is None
        assert metadata.stability_score is None
        assert metadata.generation is None
        assert metadata.parent_recipe_id is None


class TestConfigurationMetadataYAMLRoundTrip:
    """Integration tests for YAML load/serialize round-trip."""

    def test_load_yaml_with_new_metadata_fields(self):
        """Test loading a YAML configuration with new recipe metadata fields."""
        yaml_content = """
metadata:
  version: "1.0.0"
  last_updated: "2026-03-02T12:00:00Z"
  description: "Test configuration with recipe metadata"
  recipe_id: "recipe-001"
  stability_score: 0.85
  generation: 1
  parent_recipe_id: null
"""
        # Load YAML
        data = yaml.safe_load(yaml_content)
        metadata_dict = data['metadata']
        
        # Create ConfigurationMetadata from loaded data
        metadata = ConfigurationMetadata(**metadata_dict)
        
        assert metadata.version == "1.0.0"
        assert metadata.recipe_id == "recipe-001"
        assert metadata.stability_score == 0.85
        assert metadata.generation == 1
        assert metadata.parent_recipe_id is None

    def test_serialize_metadata_with_new_fields(self):
        """Test that new metadata fields are included in serialization."""
        metadata = ConfigurationMetadata(
            version="1.0.0",
            last_updated="2026-03-02T12:00:00Z",
            description="Test configuration with recipe metadata",
            recipe_id="recipe-001",
            stability_score=0.85,
            generation=1,
            parent_recipe_id="parent-recipe-001"
        )
        
        # Serialize to dict using dataclass
        metadata_dict = asdict(metadata)
        
        assert metadata_dict['version'] == "1.0.0"
        assert metadata_dict['recipe_id'] == "recipe-001"
        assert metadata_dict['stability_score'] == 0.85
        assert metadata_dict['generation'] == 1
        assert metadata_dict['parent_recipe_id'] == "parent-recipe-001"

    def test_round_trip_load_serialize_load(self):
        """Test round-trip: load YAML → serialize → load again produces same values."""
        original_yaml = """
metadata:
  version: "1.0.0"
  last_updated: "2026-03-02T12:00:00Z"
  description: "Test round-trip with recipe metadata"
  recipe_id: "recipe-002"
  stability_score: 0.92
  generation: 3
  parent_recipe_id: "recipe-001"
"""
        # First load
        data1 = yaml.safe_load(original_yaml)
        metadata1 = ConfigurationMetadata(**data1['metadata'])
        
        # Serialize to dict
        serialized = asdict(metadata1)
        
        # Reconstruct YAML-like dict for second load
        round_trip_data = {'metadata': serialized}
        
        # Second load
        metadata2 = ConfigurationMetadata(**round_trip_data['metadata'])
        
        # Verify values are preserved
        assert metadata2.version == metadata1.version
        assert metadata2.last_updated == metadata1.last_updated
        assert metadata2.description == metadata1.description
        assert metadata2.recipe_id == metadata1.recipe_id
        assert metadata2.stability_score == metadata1.stability_score
        assert metadata2.generation == metadata1.generation
        assert metadata2.parent_recipe_id == metadata1.parent_recipe_id

    def test_backward_compatible_yaml_loads(self):
        """Test that legacy YAML configs without new fields still work."""
        legacy_yaml = """
metadata:
  version: "1.0.0"
  last_updated: "2025-01-27T17:00:00Z"
  description: "Legacy configuration without new fields"
"""
        # Load legacy YAML
        data = yaml.safe_load(legacy_yaml)
        metadata = ConfigurationMetadata(**data['metadata'])
        
        # Verify backward compatibility
        assert metadata.version == "1.0.0"
        assert metadata.recipe_id is None
        assert metadata.stability_score is None
        assert metadata.generation is None
        assert metadata.parent_recipe_id is None

    def test_legacy_yaml_round_trip_preserves_none_values(self):
        """Test that legacy configs serialize None values correctly."""
        metadata = ConfigurationMetadata(
            version="1.0.0",
            last_updated="2025-01-27T17:00:00Z",
            description="Legacy configuration"
        )
        
        # Serialize
        serialized = asdict(metadata)
        
        # Verify new fields are None
        assert serialized['recipe_id'] is None
        assert serialized['stability_score'] is None
        assert serialized['generation'] is None
        assert serialized['parent_recipe_id'] is None


class TestConfigurationMetadataValidationErrors:
    """Test cases for ConfigurationMetadata validation error cases."""
    
    def test_invalid_stability_score_above_range(self):
        """Test that stability_score > 1.0 raises ValueError."""
        with pytest.raises(ValueError, match="stability_score must be between 0.0 and 1.0"):
            ConfigurationMetadata(
                version="1.0.0",
                last_updated="2026-03-02T12:00:00Z",
                description="Test",
                stability_score=1.5
            )
    
    def test_invalid_stability_score_below_range(self):
        """Test that stability_score < 0.0 raises ValueError."""
        with pytest.raises(ValueError, match="stability_score must be between 0.0 and 1.0"):
            ConfigurationMetadata(
                version="1.0.0",
                last_updated="2026-03-02T12:00:00Z",
                description="Test",
                stability_score=-0.5
            )
    
    def test_invalid_stability_score_wrong_type(self):
        """Test that non-numeric stability_score raises ValueError."""
        with pytest.raises(ValueError, match="stability_score must be a number"):
            ConfigurationMetadata(
                version="1.0.0",
                last_updated="2026-03-02T12:00:00Z",
                description="Test",
                stability_score="high"
            )
    
    def test_invalid_generation_zero(self):
        """Test that generation=0 raises ValueError."""
        with pytest.raises(ValueError, match="generation must be >= 1"):
            ConfigurationMetadata(
                version="1.0.0",
                last_updated="2026-03-02T12:00:00Z",
                description="Test",
                generation=0
            )
    
    def test_invalid_generation_negative(self):
        """Test that negative generation raises ValueError."""
        with pytest.raises(ValueError, match="generation must be >= 1"):
            ConfigurationMetadata(
                version="1.0.0",
                last_updated="2026-03-02T12:00:00Z",
                description="Test",
                generation=-3
            )
    
    def test_invalid_generation_wrong_type(self):
        """Test that non-integer generation raises ValueError."""
        with pytest.raises(ValueError, match="generation must be an integer"):
            ConfigurationMetadata(
                version="1.0.0",
                last_updated="2026-03-02T12:00:00Z",
                description="Test",
                generation=1.5
            )
    
    def test_invalid_recipe_id_empty_string(self):
        """Test that empty recipe_id raises ValueError."""
        with pytest.raises(ValueError, match="recipe_id must be non-empty if provided"):
            ConfigurationMetadata(
                version="1.0.0",
                last_updated="2026-03-02T12:00:00Z",
                description="Test",
                recipe_id=""
            )
    
    def test_invalid_recipe_id_whitespace_only(self):
        """Test that whitespace-only recipe_id raises ValueError."""
        with pytest.raises(ValueError, match="recipe_id must be non-empty if provided"):
            ConfigurationMetadata(
                version="1.0.0",
                last_updated="2026-03-02T12:00:00Z",
                description="Test",
                recipe_id="   "
            )
    
    def test_invalid_recipe_id_wrong_type(self):
        """Test that non-string recipe_id raises ValueError."""
        with pytest.raises(ValueError, match="recipe_id must be a string"):
            ConfigurationMetadata(
                version="1.0.0",
                last_updated="2026-03-02T12:00:00Z",
                description="Test",
                recipe_id=123
            )
    
    def test_invalid_parent_recipe_id_empty_string(self):
        """Test that empty parent_recipe_id raises ValueError."""
        with pytest.raises(ValueError, match="parent_recipe_id must be non-empty if provided"):
            ConfigurationMetadata(
                version="1.0.0",
                last_updated="2026-03-02T12:00:00Z",
                description="Test",
                parent_recipe_id=""
            )
    
    def test_invalid_parent_recipe_id_wrong_type(self):
        """Test that non-string parent_recipe_id raises ValueError."""
        with pytest.raises(ValueError, match="parent_recipe_id must be a string"):
            ConfigurationMetadata(
                version="1.0.0",
                last_updated="2026-03-02T12:00:00Z",
                description="Test",
                parent_recipe_id=456
            )


class TestConfigurationMetadataYAMLSerialization:
    """Test actual YAML file serialization and deserialization."""
    
    def test_yaml_dump_and_load_round_trip(self):
        """Test actual YAML file write/read cycle preserves all fields."""
        import tempfile
        import os
        
        # Create metadata with all new fields
        original = ConfigurationMetadata(
            version="2.0.0",
            last_updated="2026-03-03T10:00:00Z",
            description="Test configuration for YAML serialization",
            recipe_id="recipe-test-001",
            stability_score=0.95,
            generation=5,
            parent_recipe_id="recipe-parent-001"
        )
        
        # Write to actual YAML file
        test_data = {
            'version': original.version,
            'last_updated': original.last_updated,
            'description': original.description,
            'recipe_id': original.recipe_id,
            'stability_score': original.stability_score,
            'generation': original.generation,
            'parent_recipe_id': original.parent_recipe_id
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(test_data, f)
            temp_path = f.name
        
        try:
            # Read back from YAML file
            with open(temp_path, 'r') as f:
                loaded_data = yaml.safe_load(f)
            
            # Create new metadata from loaded data
            reconstructed = ConfigurationMetadata(**loaded_data)
            
            # Verify all fields preserved
            assert reconstructed.version == original.version
            assert reconstructed.last_updated == original.last_updated
            assert reconstructed.description == original.description
            assert reconstructed.recipe_id == original.recipe_id
            assert reconstructed.stability_score == original.stability_score
            assert reconstructed.generation == original.generation
            assert reconstructed.parent_recipe_id == original.parent_recipe_id
        finally:
            os.unlink(temp_path)
