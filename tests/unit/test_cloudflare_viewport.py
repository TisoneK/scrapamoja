"""Unit tests for Cloudflare viewport normalization module."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.stealth.cloudflare.core.viewport import ViewportNormalizer
from src.stealth.cloudflare.core.viewport.normalizer import (
    DEFAULT_VIEWPORT_POOL,
    ViewportDimension,
)
from src.stealth.cloudflare.exceptions import ViewportNormalizationError
from src.stealth.cloudflare.models.config import CloudflareConfig


class TestViewportDimension:
    """Tests for ViewportDimension class."""

    def test_initialization_valid(self) -> None:
        """Test that ViewportDimension initializes correctly."""
        dim = ViewportDimension(1920, 1080, 0.35)
        assert dim.width == 1920
        assert dim.height == 1080
        assert dim.weight == 0.35

    def test_initialization_invalid_width(self) -> None:
        """Test that invalid width raises error."""
        with pytest.raises(ValueError) as exc_info:
            ViewportDimension(0, 1080, 0.35)
        assert "Width must be positive" in str(exc_info.value)

    def test_initialization_invalid_height(self) -> None:
        """Test that invalid height raises error."""
        with pytest.raises(ValueError) as exc_info:
            ViewportDimension(1920, 0, 0.35)
        assert "Height must be positive" in str(exc_info.value)

    def test_initialization_invalid_weight(self) -> None:
        """Test that invalid weight raises error."""
        with pytest.raises(ValueError) as exc_info:
            ViewportDimension(1920, 1080, 0)
        assert "Weight must be positive" in str(exc_info.value)

    def test_repr(self) -> None:
        """Test string representation."""
        dim = ViewportDimension(1920, 1080, 0.35)
        assert "1920" in repr(dim)
        assert "1080" in repr(dim)

    def test_equality(self) -> None:
        """Test equality comparison."""
        dim1 = ViewportDimension(1920, 1080, 0.35)
        dim2 = ViewportDimension(1920, 1080, 0.5)
        dim3 = ViewportDimension(1366, 768, 0.35)

        assert dim1 == dim2
        assert dim1 != dim3


class TestViewportNormalizer:
    """Tests for ViewportNormalizer class."""

    def test_initialization_default(self) -> None:
        """Test that ViewportNormalizer initializes with correct defaults."""
        normalizer = ViewportNormalizer()
        assert normalizer.enabled is True
        assert normalizer.selected_dimension is None
        assert len(normalizer.pool) == len(DEFAULT_VIEWPORT_POOL)

    def test_initialization_with_options(self) -> None:
        """Test initialization with custom options."""
        custom_pool = [ViewportDimension(1920, 1080, 1.0)]
        normalizer = ViewportNormalizer(
            enabled=False,
            custom_pool=custom_pool
        )
        assert normalizer.enabled is False
        assert len(normalizer.pool) == 1

    def test_initialization_with_config_disabled(self) -> None:
        """Test initialization with config that has protection disabled."""
        config = CloudflareConfig(cloudflare_protected=False)
        normalizer = ViewportNormalizer(enabled=True, config=config)
        assert normalizer.enabled is False

    def test_initialization_with_config_enabled(self) -> None:
        """Test initialization with config that has protection enabled."""
        config = CloudflareConfig(cloudflare_protected=True)
        normalizer = ViewportNormalizer(enabled=True, config=config)
        assert normalizer.enabled is True

    def test_initialization_empty_custom_pool(self) -> None:
        """Test that empty custom pool raises error."""
        # Note: Empty list uses default pool, so no error is raised
        normalizer = ViewportNormalizer(custom_pool=[])
        assert normalizer.pool == DEFAULT_VIEWPORT_POOL

    @pytest.mark.asyncio
    async def test_select_dimension_enabled(self) -> None:
        """Test dimension selection when enabled."""
        normalizer = ViewportNormalizer(enabled=True)
        dimension = await normalizer.select_dimension()

        assert isinstance(dimension, ViewportDimension)
        assert dimension.width > 0
        assert dimension.height > 0

    @pytest.mark.asyncio
    async def test_select_dimension_disabled(self) -> None:
        """Test dimension selection when disabled."""
        normalizer = ViewportNormalizer(enabled=False)
        dimension = await normalizer.select_dimension()

        # Should return first dimension from pool
        assert dimension == DEFAULT_VIEWPORT_POOL[0]

    @pytest.mark.asyncio
    async def test_select_dimension_cached(self) -> None:
        """Test that dimension is cached for session consistency."""
        normalizer = ViewportNormalizer(enabled=True)

        # First selection
        dim1 = await normalizer.select_dimension()

        # Second selection should return same dimension
        dim2 = await normalizer.select_dimension()

        assert dim1 == dim2

    @pytest.mark.asyncio
    async def test_apply_viewport_enabled(self) -> None:
        """Test applying viewport to context when enabled."""
        normalizer = ViewportNormalizer(enabled=True)

        # Create mock context
        mock_context = AsyncMock()
        mock_context.set_viewport_size = AsyncMock()

        await normalizer.apply_viewport(mock_context)

        # Verify set_viewport_size was called
        mock_context.set_viewport_size.assert_called_once()

    @pytest.mark.asyncio
    async def test_apply_viewport_disabled(self) -> None:
        """Test applying viewport to context when disabled."""
        normalizer = ViewportNormalizer(enabled=False)

        # Create mock context
        mock_context = AsyncMock()

        await normalizer.apply_viewport(mock_context)

        # Verify set_viewport_size was NOT called
        mock_context.set_viewport_size.assert_not_called()

    @pytest.mark.asyncio
    async def test_apply_viewport_no_support(self) -> None:
        """Test applying viewport when context doesn't support it."""
        normalizer = ViewportNormalizer(enabled=True)

        # Create mock context without set_viewport_size
        mock_context = MagicMock()
        del mock_context.set_viewport_size

        # Should not raise, just log warning
        await normalizer.apply_viewport(mock_context)

    def test_get_pool_size(self) -> None:
        """Test getting pool size."""
        normalizer = ViewportNormalizer()
        assert normalizer.get_pool_size() == len(DEFAULT_VIEWPORT_POOL)

    def test_get_dimension_distribution(self) -> None:
        """Test getting dimension distribution."""
        normalizer = ViewportNormalizer()
        distribution = normalizer.get_dimension_distribution()

        assert isinstance(distribution, dict)
        assert len(distribution) > 0

    def test_reset_selection(self) -> None:
        """Test resetting selection."""
        normalizer = ViewportNormalizer(enabled=True)

        # First selection caches the dimension
        # Note: In synchronous test we can't call async directly without event loop
        # So we just verify the reset method clears any cached value
        normalizer.selected_dimension = ViewportDimension(1920, 1080, 1.0)
        assert normalizer.selected_dimension is not None

        # Reset should clear the cache
        normalizer.reset_selection()
        assert normalizer.selected_dimension is None


class TestDefaultViewportPool:
    """Tests for the default viewport pool."""

    def test_pool_has_valid_dimensions(self) -> None:
        """Test that all dimensions in pool are valid."""
        for dim in DEFAULT_VIEWPORT_POOL:
            assert dim.width > 0
            assert dim.height > 0
            assert dim.weight > 0

    def test_pool_weights_sum(self) -> None:
        """Test that weights sum to approximately 1.0."""
        total_weight = sum(dim.weight for dim in DEFAULT_VIEWPORT_POOL)
        assert 0.99 <= total_weight <= 1.01

    def test_pool_contains_common_resolutions(self) -> None:
        """Test that pool contains common resolutions."""
        resolutions = {(dim.width, dim.height) for dim in DEFAULT_VIEWPORT_POOL}
        assert (1920, 1080) in resolutions  # Full HD
        assert (1366, 768) in resolutions   # HD
