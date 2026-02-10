"""
Environment detection logic for the scraper framework.

This module provides comprehensive environment detection capabilities, including
automatic detection from various sources and manual environment specification.
"""

import os
import sys
from typing import Dict, Any, Optional, List, Set
from datetime import datetime
from pathlib import Path
from enum import Enum


class Environment(Enum):
    """Environment enumeration."""
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"
    LOCAL = "local"
    CI = "ci"
    DOCKER = "docker"
    KUBERNETES = "kubernetes"


class EnvironmentDetector:
    """Environment detection system."""
    
    def __init__(self):
        """Initialize environment detector."""
        self._detection_methods = [
            self._detect_from_env_vars,
            self._detect_from_command_line,
            self._detect_from_file_system,
            self._detect_from_host_info,
            self._detect_from_python_path,
            self._detect_from_config_files,
            self._detect_from_docker,
            self._detect_from_kubernetes
        ]
        
        self._environment_overrides = {}
        self._detection_cache = {}
        self._detection_timestamp = None
    
    def detect_environment(self, force_redetect: bool = False) -> Environment:
        """
        Detect the current environment.
        
        Args:
            force_redetect: Force redetection even if cached
            
        Returns:
            Detected environment
        """
        # Check cache first
        if not force_redetect and self._detection_cache:
            return self._detection_cache['environment']
        
        # Check for manual overrides
        override_env = self._check_manual_overrides()
        if override_env:
            self._cache_detection(override_env, "manual_override")
            return override_env
        
        # Run detection methods in priority order
        for detection_method in self._detection_methods:
            try:
                detected_env = detection_method()
                if detected_env:
                    self._cache_detection(detected_env, detection_method.__name__)
                    return detected_env
            except Exception as e:
                print(f"Environment detection method {detection_method.__name__} failed: {str(e)}")
                continue
        
        # Default to development if no environment detected
        default_env = Environment.DEVELOPMENT
        self._cache_detection(default_env, "default")
        return default_env
    
    def _check_manual_overrides(self) -> Optional[Environment]:
        """Check for manual environment overrides."""
        # Check environment variable override
        env_override = os.getenv('SCRAPER_ENV')
        if env_override:
            try:
                return Environment(env_override.lower())
            except ValueError:
                print(f"Invalid environment override: {env_override}")
        
        # Check command line override
        if hasattr(sys, 'argv'):
            for arg in sys.argv:
                if arg.startswith('--env='):
                    env_value = arg.split('=', 1)[1]
                    try:
                        return Environment(env_value.lower())
                    except ValueError:
                        print(f"Invalid environment override: {env_value}")
        
        # Check manual override registry
        if 'manual' in self._environment_overrides:
            override = self._environment_overrides['manual']
            try:
                return Environment(override.lower())
            except ValueError:
                print(f"Invalid manual override: {override}")
        
        return None
    
    def _detect_from_env_vars(self) -> Optional[Environment]:
        """Detect environment from environment variables."""
        env_vars = os.environ
        
        # Check for specific environment indicators
        if env_vars.get('CI') == 'true' or env_vars.get('CONTINUOUS_INTEGRATION') == 'true':
            return Environment.CI
        
        if env_vars.get('DOCKER_CONTAINER'):
            return Environment.DOCKER
        
        if env_vars.get('KUBERNETES_SERVICE_HOST'):
            return Environment.KUBERNETES
        
        if env_vars.get('ENVIRONMENT'):
            env_value = env_vars['ENVIRONMENT'].lower()
            if env_value in ['dev', 'development']:
                return Environment.DEVELOPMENT
            elif env_value in ['test', 'testing']:
                return Environment.TESTING
            elif env_value in ['staging', 'stage']:
                return Environment.STAGING
            elif env_value in ['prod', 'production']:
                return Environment.PRODUCTION
            elif env_value in ['local']:
                return Environment.LOCAL
        
        # Check for common development environment variables
        if env_vars.get('FLASK_ENV') == 'development':
            return Environment.DEVELOPMENT
        if env_vars.get('FLASK_ENV') == 'production':
            return Environment.PRODUCTION
        if env_vars.get('NODE_ENV') == 'development':
            return Environment.DEVELOPMENT
        if env_vars.get('NODE_ENV') == 'production':
            return Environment.PRODUCTION
        
        return None
    
    def _detect_from_command_line(self) -> Optional[Environment]:
        """Detect environment from command line arguments."""
        if not hasattr(sys, 'argv'):
            return None
        
        argv = sys.argv
        
        # Check for environment flags
        if '--dev' in argv or '--development' in argv:
            return Environment.DEVELOPMENT
        if '--test' in argv or '--testing' in argv:
            return Environment.TESTING
        if '--staging' in argv or '--stage' in argv:
            return Environment.STAGING
        if '--prod' in argv or '--production' in argv:
            return Environment.PRODUCTION
        if '--local' in argv:
            return Environment.LOCAL
        
        # Check for script name patterns
        script_name = Path(argv[0]).name if argv else ''
        if 'test' in script_name.lower():
            return Environment.TESTING
        if 'dev' in script_name.lower():
            return Environment.DEVELOPMENT
        
        return None
    
    def _detect_from_file_system(self) -> Optional[Environment]:
        """Detect environment from file system indicators."""
        current_dir = Path.cwd()
        
        # Check for environment-specific files
        env_files = [
            '.env.development',
            '.env.dev',
            '.env.testing',
            '.env.test',
            '.env.staging',
            '.env.stage',
            '.env.production',
            '.env.prod',
            '.env.local'
        ]
        
        for env_file in env_files:
            if (current_dir / env_file).exists():
                env_name = env_file.replace('.env.', '').replace('.env', '')
                if env_name in ['dev', 'development']:
                    return Environment.DEVELOPMENT
                elif env_name in ['test', 'testing']:
                    return Environment.TESTING
                elif env_name in ['staging', 'stage']:
                    return Environment.STAGING
                elif env_name in ['prod', 'production']:
                    return Environment.PRODUCTION
                elif env_name == 'local':
                    return Environment.LOCAL
        
        # Check for directory structure patterns
        if (current_dir / 'tests').exists() and (current_dir / 'src').exists():
            return Environment.DEVELOPMENT
        
        if (current_dir / 'node_modules').exists() and (current_dir / 'package.json').exists():
            return Environment.DEVELOPMENT
        
        # Check for production indicators
        if (current_dir / 'Procfile').exists() or (current_dir / 'Dockerfile.prod').exists():
            return Environment.PRODUCTION
        
        return None
    
    def _detect_from_host_info(self) -> Optional[Environment]:
        """Detect environment from host information."""
        hostname = os.getenv('HOSTNAME', '')
        
        # Check hostname patterns
        hostname_lower = hostname.lower()
        
        if any(pattern in hostname_lower for pattern in ['prod', 'production', 'live']):
            return Environment.PRODUCTION
        if any(pattern in hostname_lower for pattern in ['staging', 'stage', 'stg']):
            return Environment.STAGING
        if any(pattern in hostname_lower for pattern in ['dev', 'development', 'dev-']):
            return Environment.DEVELOPMENT
        if any(pattern in hostname_lower for pattern in ['test', 'testing', 'test-']):
            return Environment.TESTING
        
        # Check for local development patterns
        if hostname.startswith(('localhost', '127.0.0.1', '::1')):
            return Environment.LOCAL
        
        # Check for CI/CD patterns
        if any(pattern in hostname_lower for pattern in ['jenkins', 'travis', 'circleci', 'github-actions']):
            return Environment.CI
        
        return None
    
    def _detect_from_python_path(self) -> Optional[Environment]:
        """Detect environment from Python path."""
        python_path = sys.path
        
        # Check for virtual environment indicators
        if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
            # We're in a virtual environment
            venv_path = Path(sys.prefix)
            
            if 'test' in venv_path.name.lower():
                return Environment.TESTING
            if 'dev' in venv_path.name.lower():
                return Environment.DEVELOPMENT
            if 'prod' in venv_path.name.lower():
                return Environment.PRODUCTION
        
        # Check for development patterns in path
        path_str = str(python_path)
        if 'site-packages' in path_str:
            return Environment.PRODUCTION
        
        return None
    
    def _detect_from_config_files(self) -> Optional[Environment]:
        """Detect environment from configuration files."""
        current_dir = Path.cwd()
        
        # Check for common config files
        config_files = [
            'config.json',
            'config.yaml',
            'config.yml',
            'settings.json',
            'settings.yaml',
            'settings.yml',
            'app.json',
            'app.yaml',
            'app.yml'
        ]
        
        for config_file in config_files:
            config_path = current_dir / config_file
            if config_path.exists():
                try:
                    import json
                    with open(config_path, 'r') as f:
                        if config_file.endswith('.json'):
                            config_data = json.load(f)
                        else:
                            import yaml
                            config_data = yaml.safe_load(f)
                    
                    # Look for environment in config
                    if 'environment' in config_data:
                        env_value = config_data['environment'].lower()
                        if env_value in ['dev', 'development']:
                            return Environment.DEVELOPMENT
                        elif env_value in ['test', 'testing']:
                            return Environment.TESTING
                        elif env_value in ['staging', 'stage']:
                            return Environment.STAGING
                        elif env_value in ['prod', 'production']:
                            return Environment.PRODUCTION
                        elif env_value == 'local':
                            return Environment.LOCAL
                    
                    # Look for environment-specific settings
                    if 'development' in config_data or 'dev' in config_data:
                        return Environment.DEVELOPMENT
                    if 'testing' in config_data or 'test' in config_data:
                        return Environment.TESTING
                    if 'staging' in config_data or 'stage' in config_data:
                        return Environment.STAGING
                    if 'production' in config_data or 'prod' in config_data:
                        return Environment.PRODUCTION
                
                except Exception:
                    # Skip files that can't be parsed
                    continue
        
        return None
    
    def _detect_from_docker(self) -> Optional[Environment]:
        """Detect Docker environment."""
        # Check for Docker-specific files
        current_dir = Path.cwd()
        
        if (current_dir / 'Dockerfile').exists() or (current_dir / 'docker-compose.yml').exists():
            # Check if we're inside a Docker container
            if os.path.exists('/.dockerenv'):
                return Environment.DOCKER
            
            # Check for Docker environment variables
            if os.getenv('DOCKER_CONTAINER') or os.getenv('DOCKER_HOST'):
                return Environment.DOCKER
        
        return None
    
    def _detect_from_kubernetes(self) -> Optional[Environment]:
        """Detect Kubernetes environment."""
        # Check for Kubernetes-specific files and environment variables
        current_dir = Path.cwd()
        
        if (current_dir / 'k8s').exists() or (current_dir / 'kubernetes').exists():
            # Check if we're inside a Kubernetes pod
            if os.getenv('KUBERNETES_SERVICE_HOST'):
                return Environment.KUBERNETES
            
            # Check for Kubernetes environment variables
            if os.getenv('KUBERNETES_POD_NAME') or os.getenv('KUBERNETES_NAMESPACE'):
                return Environment.KUBERNETES
        
        return None
    
    def _cache_detection(self, environment: Environment, method: str) -> None:
        """Cache detection result."""
        self._detection_cache = {
            'environment': environment,
            'method': method,
            'timestamp': datetime.utcnow()
        }
        self._detection_timestamp = datetime.utcnow()
    
    def get_detection_info(self) -> Dict[str, Any]:
        """Get information about the last detection."""
        if not self._detection_cache:
            return {}
        
        return {
            'environment': self._detection_cache['environment'].value,
            'method': self._detection_cache['method'],
            'timestamp': self._detection_cache['timestamp'].isoformat() if self._detection_cache['timestamp'] else None,
            'overrides': self._environment_overrides
        }
    
    def set_manual_override(self, environment: Environment) -> None:
        """Set a manual environment override."""
        self._environment_overrides['manual'] = environment.value
        # Clear cache to force redetection
        self._detection_cache = None
        self._detection_timestamp = None
    
    def clear_manual_override(self) -> None:
        """Clear manual environment override."""
        if 'manual' in self._environment_overrides:
            del self._environment_overrides['manual']
        # Clear cache to force redetection
        self._detection_cache = None
        self._detection_timestamp = None
    
    def is_production(self) -> bool:
        """Check if current environment is production."""
        env = self.detect_environment()
        return env == Environment.PRODUCTION
    
    def is_development(self) -> bool:
        """Check if current environment is development."""
        env = self.detect_environment()
        return env == Environment.DEVELOPMENT
    
    def is_testing(self) -> bool:
        """Check if current environment is testing."""
        env = self.detect_environment()
        return env == Environment.TESTING
    
    def is_staging(self) -> bool:
        """Check if current environment is staging."""
        env = self.detect_environment()
        return env == Environment.STAGING
    
    def is_ci(self) -> bool:
        """Check if current environment is CI/CD."""
        env = self.detect_environment()
        return env == Environment.CI
    
    def get_environment_config_path(self, environment: Environment = None) -> Optional[Path]:
        """Get configuration file path for environment."""
        if environment is None:
            environment = self.detect_environment()
        
        current_dir = Path.cwd()
        
        # Try different config file patterns
        config_patterns = [
            f'config.{environment.value}.json',
            f'config.{environment.value}.yaml',
            f'config.{environment.value}.yml',
            f'settings.{environment.value}.json',
            f'settings.{environment.value}.yaml',
            f'settings.{environment.value}.yml',
            f'.env.{environment.value}',
            f'.env.{environment.value[0:3]}'  # .env.dev, .env.prod, etc.
        ]
        
        for pattern in config_patterns:
            config_path = current_dir / pattern
            if config_path.exists():
                return config_path
        
        return None
    
    def get_all_possible_environments(self) -> List[Environment]:
        """Get all possible environments."""
        return list(Environment)
    
    def validate_environment(self, environment: str) -> bool:
        """Validate if environment string is valid."""
        try:
            Environment(environment.lower())
            return True
        except ValueError:
            return False


# Global environment detector instance
_environment_detector = EnvironmentDetector()


# Convenience functions
def detect_environment(force_redetect: bool = False) -> Environment:
    """Detect the current environment."""
    return _environment_detector.detect_environment(force_redetect)


def get_environment() -> str:
    """Get the current environment as string."""
    return _environment_detector.detect_environment().value


def is_production() -> bool:
    """Check if current environment is production."""
    return _environment_detector.is_production()


def is_development() -> bool:
    """Check if current environment is development."""
    return _environment_detector.is_development()


def is_testing() -> bool:
    """Check if current environment is testing."""
    return _environment_detector.is_testing()


def is_staging() -> bool:
    """Check if current environment is staging."""
    return _environment_detector.is_staging()


def is_ci() -> bool:
    """Check if current environment is CI/CD."""
    return _environment_detector.is_ci()


def set_manual_override(environment: str) -> None:
    """Set a manual environment override."""
    try:
        env = Environment(environment.lower())
        _environment_detector.set_manual_override(env)
    except ValueError as e:
        raise ValueError(f"Invalid environment: {environment}")


def clear_manual_override() -> None:
    """Clear manual environment override."""
    _environment_detector.clear_manual_override()


def get_detection_info() -> Dict[str, Any]:
    """Get information about the last detection."""
    return _environment_detector.get_detection_info()


def get_environment_config_path(environment: str = None) -> Optional[Path]:
    """Get configuration file path for environment."""
    if environment:
        try:
            env = Environment(environment.lower())
            return _environment_detector.get_environment_config_path(env)
        except ValueError:
            return None
    else:
        return _environment_detector.get_environment_config_path()


# Environment-specific utilities
def get_environment_specific_config(base_config: Dict[str, Any], environment: str = None) -> Dict[str, Any]:
    """Get environment-specific configuration."""
    if environment is None:
        environment = get_environment()
    
    # Start with base config
    config = base_config.copy()
    
    # Add environment-specific overrides
    env_overrides = {
        'development': {
            'debug': True,
            'headless': False,
            'timeout': 60000,
            'retry_count': 5,
            'log_level': 'DEBUG'
        },
        'testing': {
            'debug': True,
            'headless': True,
            'timeout': 30000,
            'retry_count': 1,
            'log_level': 'INFO'
        },
        'staging': {
            'debug': False,
            'headless': True,
            'timeout': 45000,
            'retry_count': 3,
            'log_level': 'INFO'
        },
        'production': {
            'debug': False,
            'headless': True,
            'timeout': 30000,
            'retry_count': 3,
            'log_level': 'WARNING'
        }
    }
    
    if environment in env_overrides:
        config.update(env_overrides[environment])
    
    return config
