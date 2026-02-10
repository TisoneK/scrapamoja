"""
Setup script for the shared components package.

This module provides packaging configuration and utilities for the shared components
package, making it easy to install and distribute components as a separate package.
"""

from setuptools import setup, find_packages
from pathlib import Path
import json

# Package metadata
PACKAGE_NAME = "scorewise-shared-components"
VERSION = "1.0.0"
DESCRIPTION = "Shared components for the Scorewise scraper framework"
AUTHOR = "Scorewise Team"
AUTHOR_EMAIL = "dev@scorewise.dev"
URL = "https://github.com/scorewise/scorewise-scraper"
LICENSE = "MIT"
PYTHON_REQUIRES = [
    "playwright>=1.40.0",
    "aiohttp>=3.8.0",
    "psutil>=5.8.0"
]

# Read package metadata from metadata file
metadata_file = Path(__file__).parent / 'metadata.json'
if metadata_file.exists():
    with open(metadata_file, 'r') as f:
        metadata = json.load(f)
        PACKAGE_NAME = metadata.get('name', PACKAGE_NAME)
        VERSION = metadata.get('version', VERSION)
        DESCRIPTION = metadata.get('description', DESCRIPTION)
        AUTHOR = metadata.get('author', AUTHOR)
        AUTHOR_EMAIL = metadata.get('author_email', AUTHOR_EMAIL)
        URL = metadata.get('url', URL)
        PYTHON_REQUIRES = metadata.get('requires', PYTHON_REQUIRES)

# Define package data
setup(
    name=PACKAGE_NAME,
    version=VERSION,
    description=DESCRIPTION,
    author=AUTHOR,
    author_email=AUTHOR_EMAIL,
    url=URL,
    license=LICENSE,
    python_requires=PYTHON_REQUIRES,
    packages=find_packages(where=['src']),
    include_package_data=True,
    package_data={
        'package': [
            {
                'shared_components': [
                    'src/sites/shared_components/__init__.py',
                    'src/sites/shared_components/authentication/__init__.py',
                    'src/sites/shared_components/pagination/__init__.py',
                    'src/sites/shared_components/data_processing/__init__.py',
                    'src/sites/shared_components/stealth/__init__.py'
                ]
            }
        ]
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Internet :: WWW/HTTP :: Indexing/Search",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
        "Topic :: Software Development :: Libraries :: WWW/HTTP :: Indexing/Search"
    ],
    keywords=[
        "scraping", "automation", "web", "extraction", "components", "shared", "reusable"
    ],
    project_urls={
        "Documentation": "https://github.com/scorewise/scorewise-scraper",
        "Source": "https://github.com/scorewise/scorewise-scraper/tree/main/src/sites/shared_components",
        "Issues": "https://github.com/scorewise/scorewise-scraper/issues"
    },
    entry_points={
        "console_scripts": [
            "shared_components.cli:main"
        ],
        "component_discovery": "shared_components.discovery:main",
        "dependency_resolver": "shared_components.dependency_resolver:main"
    },
    extras_require={
        'dev': [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "black>=22.0.0",
            "flake8>=5.0.0",
            "mypy>=1.0.0"
        ]
    }
)

# Component discovery entry point
console_scripts = {
    'main': 'shared_components.cli:main'
}

# Dependency resolver entry point
dependency_resolver = 'shared_components.dependency_resolver:main'

# CLI entry point
cli = 'shared_components.cli:main'
