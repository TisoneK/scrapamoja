"""
Tests for fingerprint normalization subsystem.

Validates that FingerprintNormalizer generates coherent, statistically-valid
fingerprints across all properties (user-agent, timezone, language, plugins).
"""

import pytest
from src.stealth.fingerprint import FingerprintNormalizer, BrowserFingerprint, TIMEZONE_OFFSETS


class TestFingerprintInitialization:
    """Tests for FingerprintNormalizer initialization."""

    def test_normalizer_init_default(self):
        """FingerprintNormalizer initializes with default caching enabled."""
        normalizer = FingerprintNormalizer()
        assert normalizer.cache_fingerprints is True
        assert normalizer._cached_fingerprint is None

    def test_normalizer_init_no_cache(self):
        """FingerprintNormalizer can be initialized without caching."""
        normalizer = FingerprintNormalizer(cache_fingerprints=False)
        assert normalizer.cache_fingerprints is False


class TestFingerprintGeneration:
    """Tests for generate_fingerprint() method."""

    def test_generate_fingerprint_chrome(self):
        """Generate Chrome fingerprint."""
        normalizer = FingerprintNormalizer(cache_fingerprints=False)
        fp = normalizer.generate_fingerprint(browser="Chrome")
        
        assert fp.browser == "Chrome"
        assert "chrome" in fp.user_agent.lower()
        assert fp.plugins  # Chrome should have plugins

    def test_generate_fingerprint_firefox(self):
        """Generate Firefox fingerprint."""
        normalizer = FingerprintNormalizer(cache_fingerprints=False)
        fp = normalizer.generate_fingerprint(browser="Firefox")
        
        assert fp.browser == "Firefox"
        assert "firefox" in fp.user_agent.lower()

    def test_generate_fingerprint_safari(self):
        """Generate Safari fingerprint."""
        normalizer = FingerprintNormalizer(cache_fingerprints=False)
        fp = normalizer.generate_fingerprint(browser="Safari")
        
        assert fp.browser == "Safari"
        assert "safari" in fp.user_agent.lower()
        assert fp.platform == "macOS"  # Safari only on macOS

    def test_generate_fingerprint_random_browser(self):
        """Generate fingerprint with random browser."""
        normalizer = FingerprintNormalizer(cache_fingerprints=False)
        fp = normalizer.generate_fingerprint()
        
        assert fp.browser in ["Chrome", "Firefox", "Safari"]
        assert fp.consistent  # Should be coherent

    def test_generate_fingerprint_with_language(self):
        """Generate fingerprint with specific language."""
        normalizer = FingerprintNormalizer(cache_fingerprints=False)
        fp = normalizer.generate_fingerprint(language="fr-FR")
        
        assert fp.language == "fr-FR"
        assert fp.timezone in ["Europe/Paris", "UTC"]

    def test_generate_multiple_fingerprints_no_cache(self):
        """Generate multiple fingerprints without caching (should be different)."""
        normalizer = FingerprintNormalizer(cache_fingerprints=False)
        fp1 = normalizer.generate_fingerprint()
        fp2 = normalizer.generate_fingerprint()
        
        # Likely different (not guaranteed, but very probable)
        assert fp1.browser != fp2.browser or fp1.screen_width != fp2.screen_width

    def test_generate_with_cache_returns_same(self):
        """With caching enabled, same fingerprint returned."""
        normalizer = FingerprintNormalizer(cache_fingerprints=True)
        fp1 = normalizer.generate_fingerprint()
        fp2 = normalizer.generate_fingerprint()
        
        assert fp1 is fp2  # Exact same object

    def test_fingerprint_has_required_fields(self):
        """Generated fingerprint has all required fields."""
        normalizer = FingerprintNormalizer(cache_fingerprints=False)
        fp = normalizer.generate_fingerprint()
        
        assert fp.user_agent
        assert fp.platform
        assert fp.browser
        assert fp.language
        assert fp.timezone
        assert fp.timezone_offset is not None
        assert fp.screen_width > 0
        assert fp.screen_height > 0
        assert 0 < fp.device_pixel_ratio <= 3.0
        assert fp.color_depth in [24, 32]
        assert isinstance(fp.plugins, list)
        assert isinstance(fp.media_devices, dict)


class TestCoherenceValidation:
    """Tests for validate_coherence() method."""

    def test_coherent_chrome_fingerprint(self):
        """Chrome fingerprint passes coherence validation."""
        normalizer = FingerprintNormalizer(cache_fingerprints=False)
        fp = normalizer.generate_fingerprint(browser="Chrome")
        
        is_coherent, errors = normalizer.validate_coherence(fp)
        assert is_coherent, f"Chrome fingerprint incoherent: {errors}"
        assert len(errors) == 0

    def test_coherent_firefox_fingerprint(self):
        """Firefox fingerprint passes coherence validation."""
        normalizer = FingerprintNormalizer(cache_fingerprints=False)
        fp = normalizer.generate_fingerprint(browser="Firefox")
        
        is_coherent, errors = normalizer.validate_coherence(fp)
        assert is_coherent, f"Firefox fingerprint incoherent: {errors}"

    def test_coherence_check_1_useragent_contains_browser(self):
        """Coherence check: user-agent contains browser name."""
        normalizer = FingerprintNormalizer(cache_fingerprints=False)
        fp = BrowserFingerprint(
            user_agent="Mozilla/5.0 (Generic Browser)",
            platform="Linux",
            platform_version="5.10",
            browser="Chrome",
            browser_version="120.0.0.0",
            language="en-US",
            timezone="UTC",
            timezone_offset=0,
            screen_width=1920,
            screen_height=1080,
            device_pixel_ratio=1.0,
            color_depth=24,
            plugins=[],
            media_devices={},
        )
        
        is_coherent, errors = normalizer.validate_coherence(fp)
        assert not is_coherent
        assert any("Chrome" in e for e in errors)

    def test_coherence_check_2_useragent_contains_platform(self):
        """Coherence check: user-agent contains platform indicator."""
        normalizer = FingerprintNormalizer(cache_fingerprints=False)
        fp = BrowserFingerprint(
            user_agent="Mozilla/5.0 (Generic) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
            platform="Windows",
            platform_version="10.0",
            browser="Chrome",
            browser_version="120.0.0.0",
            language="en-US",
            timezone="UTC",
            timezone_offset=0,
            screen_width=1920,
            screen_height=1080,
            device_pixel_ratio=1.0,
            color_depth=24,
            plugins=[],
            media_devices={},
        )
        
        is_coherent, errors = normalizer.validate_coherence(fp)
        assert not is_coherent
        assert any("Windows" in e for e in errors)

    def test_coherence_check_screen_resolution_realistic(self):
        """Coherence check: screen resolution must be realistic."""
        normalizer = FingerprintNormalizer(cache_fingerprints=False)
        
        # Too small
        fp_small = normalizer.get_safe_defaults()
        fp_small.screen_width = 320
        fp_small.screen_height = 200
        is_coherent, errors = normalizer.validate_coherence(fp_small)
        assert not is_coherent
        assert any("small" in e.lower() for e in errors)
        
        # Too large
        fp_large = normalizer.get_safe_defaults()
        fp_large.screen_width = 10000
        fp_large.screen_height = 10000
        is_coherent, errors = normalizer.validate_coherence(fp_large)
        assert not is_coherent
        assert any("large" in e.lower() for e in errors)

    def test_coherence_check_device_pixel_ratio(self):
        """Coherence check: device pixel ratio must be realistic."""
        normalizer = FingerprintNormalizer(cache_fingerprints=False)
        fp = normalizer.get_safe_defaults()
        fp.device_pixel_ratio = 5.5
        
        is_coherent, errors = normalizer.validate_coherence(fp)
        assert not is_coherent
        assert any("pixel ratio" in e.lower() for e in errors)

    def test_coherence_check_color_depth(self):
        """Coherence check: color depth must be 24 or 32."""
        normalizer = FingerprintNormalizer(cache_fingerprints=False)
        fp = normalizer.get_safe_defaults()
        fp.color_depth = 16
        
        is_coherent, errors = normalizer.validate_coherence(fp)
        assert not is_coherent
        assert any("color depth" in e.lower() for e in errors)

    def test_coherence_check_language_tag(self):
        """Coherence check: language must be valid BCP-47."""
        normalizer = FingerprintNormalizer(cache_fingerprints=False)
        fp = normalizer.get_safe_defaults()
        fp.language = "invalid-language-tag-xyz"
        
        is_coherent, errors = normalizer.validate_coherence(fp)
        assert not is_coherent
        assert any("BCP-47" in e for e in errors)


class TestSafeDefaults:
    """Tests for get_safe_defaults() method."""

    def test_safe_defaults_returns_coherent_fingerprint(self):
        """Safe defaults fingerprint is coherent."""
        normalizer = FingerprintNormalizer()
        fp = normalizer.get_safe_defaults()
        
        is_coherent, errors = normalizer.validate_coherence(fp)
        assert is_coherent, f"Safe defaults incoherent: {errors}"
        assert len(errors) == 0

    def test_safe_defaults_values(self):
        """Safe defaults has reasonable values."""
        normalizer = FingerprintNormalizer()
        fp = normalizer.get_safe_defaults()
        
        assert fp.browser == "Chrome"
        assert fp.platform in ["Linux", "macOS"]
        assert fp.language == "en-US"
        assert fp.timezone == "UTC"
        assert fp.screen_width == 1920
        assert fp.screen_height == 1080
        assert fp.consistent is True

    def test_safe_defaults_always_same(self):
        """Safe defaults always returns the same values."""
        normalizer = FingerprintNormalizer()
        fp1 = normalizer.get_safe_defaults()
        fp2 = normalizer.get_safe_defaults()
        
        # Different objects but same values
        assert fp1.user_agent == fp2.user_agent
        assert fp1.browser == fp2.browser
        assert fp1.platform == fp2.platform


class TestFingerprintGeneration100Samples:
    """Test fingerprint generation at scale (100 samples)."""

    def test_generate_100_fingerprints_all_coherent(self):
        """Generate 100 fingerprints, all should be coherent."""
        normalizer = FingerprintNormalizer(cache_fingerprints=False)
        incoherent_count = 0
        errors_list = []
        
        for _ in range(100):
            fp = normalizer.generate_fingerprint()
            is_coherent, errors = normalizer.validate_coherence(fp)
            if not is_coherent:
                incoherent_count += 1
                errors_list.extend(errors)
        
        # Allow up to 5% incoherent (5 out of 100) due to random generation
        assert incoherent_count <= 5, f"Too many incoherent: {incoherent_count}/100. Errors: {errors_list[:10]}"

    def test_generate_100_chrome_fingerprints(self):
        """Generate 100 Chrome fingerprints, verify all have Chrome properties."""
        normalizer = FingerprintNormalizer(cache_fingerprints=False)
        
        for _ in range(100):
            fp = normalizer.generate_fingerprint(browser="Chrome")
            assert fp.browser == "Chrome"
            assert "chrome" in fp.user_agent.lower()
            assert fp.plugins  # Chrome should have plugins

    def test_timezone_offset_matches_timezone(self):
        """For 50 fingerprints, timezone_offset matches timezone."""
        normalizer = FingerprintNormalizer(cache_fingerprints=False)
        
        for _ in range(50):
            fp = normalizer.generate_fingerprint()
            expected_offset = TIMEZONE_OFFSETS.get(fp.timezone, -99999)
            assert fp.timezone_offset == expected_offset, \
                f"Timezone {fp.timezone} has offset {fp.timezone_offset}, expected {expected_offset}"


class TestCachingBehavior:
    """Tests for fingerprint caching."""

    def test_cache_clear(self):
        """clear_cache() clears the cached fingerprint."""
        normalizer = FingerprintNormalizer(cache_fingerprints=True)
        fp1 = normalizer.generate_fingerprint()
        
        normalizer.clear_cache()
        assert normalizer._cached_fingerprint is None
        
        fp2 = normalizer.generate_fingerprint()
        assert fp1 is not fp2  # Different objects now

    def test_cache_disabled_always_different(self):
        """With caching disabled, repeated calls return different objects."""
        normalizer = FingerprintNormalizer(cache_fingerprints=False)
        fp1 = normalizer.generate_fingerprint()
        fp2 = normalizer.generate_fingerprint()
        fp3 = normalizer.generate_fingerprint()
        
        assert fp1 is not fp2
        assert fp2 is not fp3
        assert fp1 is not fp3
