"""
Runtime contract validation for site scrapers.

Provides runtime validation and monitoring of contract compliance
during scraper instantiation and operation.
"""

import time
from typing import Dict, Any, Optional, List
from .site_scraper import BaseSiteScraper


class ContractValidator:
    """Runtime validator for scraper contract compliance."""
    
    def __init__(self):
        self._logger = None  # Simplified for demo
        self._validation_stats = {
            "total_validations": 0,
            "validation_failures": 0,
            "contract_violations": {}
        }
    
    def validate_scraper_instantiation(self, scraper_class: type, page, selector_engine) -> BaseSiteScraper:
        """Validate scraper during instantiation and return validated instance."""
        start_time = time.time()
        
        try:
            # Pre-instantiation validation
            self._validate_scraper_class(scraper_class)
            
            # Instantiate the scraper
            scraper = scraper_class(page, selector_engine)
            
            # Post-instantiation validation
            self._validate_scraper_instance(scraper)
            
            # Record successful validation
            validation_time = time.time() - start_time
            self._record_validation_success(scraper_class.__name__, validation_time)
            
            print(f"✅ Scraper contract validation passed - {scraper_class.__name__} ({validation_time:.3f}s)")
            
            return scraper
            
        except Exception as e:
            # Record validation failure
            self._record_validation_failure(scraper_class.__name__, str(e))
            
            print(f"❌ Scraper contract validation failed - {scraper_class.__name__}: {str(e)}")
            
            raise Exception(f"Contract validation failed for {scraper_class.__name__}: {str(e)}")
    
    def _validate_scraper_class(self, scraper_class: type) -> None:
        """Validate scraper class before instantiation."""
        # Check inheritance
        if not issubclass(scraper_class, BaseSiteScraper):
            raise Exception(f"Scraper class {scraper_class.__name__} must inherit from BaseSiteScraper")
        
        # Check abstract methods are implemented
        abstract_methods = BaseSiteScraper.__abstractmethods__
        for method_name in abstract_methods:
            if not hasattr(scraper_class, method_name):
                raise Exception(f"Missing abstract method: {method_name}")
        
        # Check class attributes
        required_attrs = ['site_id', 'site_name', 'base_url']
        for attr in required_attrs:
            if not hasattr(scraper_class, attr):
                raise Exception(f"Missing class attribute: {attr}")
            
            value = getattr(scraper_class, attr)
            if not isinstance(value, str):
                raise Exception(f"Class attribute {attr} must be a string")
            
            if not value.strip():
                raise Exception(f"Class attribute {attr} cannot be empty")
    
    def _validate_scraper_instance(self, scraper: BaseSiteScraper) -> None:
        """Validate scraper instance after instantiation."""
        # Validate state
        state = scraper.validate_state()
        
        if not state.get("initialized"):
            raise Exception("Scraper not properly initialized")
        
        if not state.get("has_page"):
            raise Exception("Scraper missing page instance")
        
        if not state.get("has_selector_engine"):
            raise Exception("Scraper missing selector engine instance")
        
        # Validate site info consistency
        site_info = scraper.get_site_info()
        class_attrs = {
            'site_id': scraper.site_id,
            'site_name': scraper.site_name,
            'base_url': scraper.base_url
        }
        
        for attr, expected_value in class_attrs.items():
            if site_info[attr] != expected_value:
                raise Exception(f"Site info inconsistency: {attr} mismatch")
    
    def validate_method_call(self, scraper: BaseSiteScraper, method_name: str, *args, **kwargs) -> None:
        """Validate method call parameters against contract."""
        if method_name == 'navigate':
            if args or kwargs:
                raise Exception(f"navigate() method takes no parameters, got: args={args}, kwargs={kwargs}")
        
        elif method_name == 'scrape':
            if args:
                raise Exception(f"scrape() method only accepts **kwargs, got positional args: {args}")
        
        elif method_name == 'normalize':
            # normalize() should take self and raw_data (1 parameter total)
            if len(params) != 2:
                raise Exception(f"normalize() method must take exactly one parameter (raw_data), got: {params}")
            
            if 'raw_data' not in params:
                raise Exception(f"normalize() method must have 'raw_data' parameter")
        
        elif method_name == 'get_site_info':
            if args or kwargs:
                raise Exception(f"get_site_info() method takes no parameters, got: args={args}, kwargs={kwargs}")
        
        elif method_name == 'validate_state':
            if args or kwargs:
                raise Exception(f"validate_state() method takes no parameters, got: args={args}, kwargs={kwargs}")
    
    def monitor_contract_compliance(self, scraper: BaseSiteScraper) -> Dict[str, Any]:
        """Monitor contract compliance during operation."""
        try:
            state = scraper.validate_state()
            
            compliance_report = {
                "site_id": scraper.site_id,
                "timestamp": time.time(),
                "compliant": True,
                "issues": [],
                "warnings": []
            }
            
            # Check for common runtime issues
            if not state.get("has_page"):
                compliance_report["compliant"] = False
                compliance_report["issues"].append("Missing page instance")
            
            if not state.get("has_selector_engine"):
                compliance_report["compliant"] = False
                compliance_report["issues"].append("Missing selector engine instance")
            
            # Check site info consistency
            site_info = scraper.get_site_info()
            if site_info["site_id"] != scraper.site_id:
                compliance_report["compliant"] = False
                compliance_report["issues"].append("Site ID inconsistency")
            
            # Log compliance status
            if compliance_report["compliant"]:
                print(f"✅ Contract compliance check passed - {scraper.site_id}")
            else:
                print(f"⚠️ Contract compliance issues detected - {scraper.site_id}: {compliance_report['issues']}")
            
            return compliance_report
            
        except Exception as e:
            print(f"❌ Contract compliance monitoring failed - {getattr(scraper, 'site_id', 'unknown')}: {str(e)}")
            
            return {
                "site_id": getattr(scraper, 'site_id', 'unknown'),
                "timestamp": time.time(),
                "compliant": False,
                "issues": [f"Monitoring error: {str(e)}"],
                "warnings": []
            }
    
    def get_validation_stats(self) -> Dict[str, Any]:
        """Get validation statistics."""
        return self._validation_stats.copy()
    
    def reset_stats(self) -> None:
        """Reset validation statistics."""
        self._validation_stats = {
            "total_validations": 0,
            "validation_failures": 0,
            "contract_violations": {}
        }
    
    def _record_validation_success(self, scraper_class_name: str, validation_time: float) -> None:
        """Record successful validation."""
        self._validation_stats["total_validations"] += 1
        
        # Track performance
        if scraper_class_name not in self._validation_stats["contract_violations"]:
            self._validation_stats["contract_violations"][scraper_class_name] = {
                "success_count": 0,
                "failure_count": 0,
                "total_time": 0.0,
                "avg_time": 0.0
            }
        
        stats = self._validation_stats["contract_violations"][scraper_class_name]
        stats["success_count"] += 1
        stats["total_time"] += validation_time
        stats["avg_time"] = stats["total_time"] / stats["success_count"]
    
    def _record_validation_failure(self, scraper_class_name: str, error_message: str) -> None:
        """Record validation failure."""
        self._validation_stats["total_validations"] += 1
        self._validation_stats["validation_failures"] += 1
        
        if scraper_class_name not in self._validation_stats["contract_violations"]:
            self._validation_stats["contract_violations"][scraper_class_name] = {
                "success_count": 0,
                "failure_count": 0,
                "total_time": 0.0,
                "avg_time": 0.0
            }
        
        stats = self._validation_stats["contract_violations"][scraper_class_name]
        stats["failure_count"] += 1


# Global validator instance
_contract_validator = ContractValidator()


def validate_and_create_scraper(scraper_class: type, page, selector_engine) -> BaseSiteScraper:
    """
    Convenience function to validate and create a scraper instance.
    
    This function provides a simple way to create scrapers with automatic
    contract validation during instantiation.
    """
    return _contract_validator.validate_scraper_instantiation(scraper_class, page, selector_engine)


def monitor_compliance(scraper: BaseSiteScraper) -> Dict[str, Any]:
    """
    Convenience function to monitor scraper contract compliance.
    """
    return _contract_validator.monitor_contract_compliance(scraper)
