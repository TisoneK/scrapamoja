#!/usr/bin/env python3
# /// script
# requires-python = ">=3.8"
# ///
"""
Document Verifier Script - BMAD Crew Advisor v0.2.0

Validates Builder outputs against locked decisions, project context, and quality standards.
Implements the "read-before-validate" principle for all document types.
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

class DocumentVerifier:
    def __init__(self, args):
        self.args = args
        self.issues = []
        self.warnings = []
        self.locked_decisions = {}
        self.project_context = {}
        
    def load_locked_decisions(self) -> bool:
        """Load locked decisions from file."""
        try:
            if not os.path.exists(self.args.locked_decisions):
                self.warnings.append(f"Locked decisions file not found: {self.args.locked_decisions}")
                return True  # Not critical, proceed with warnings
                
            with open(self.args.locked_decisions, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Parse locked decisions (simple key-value extraction)
            self.locked_decisions = self._parse_markdown_decisions(content)
            return True
            
        except Exception as e:
            self.issues.append(f"Failed to load locked decisions: {e}")
            return False
    
    def load_project_context(self) -> bool:
        """Load project context from file."""
        try:
            if not os.path.exists(self.args.project_context):
                self.warnings.append(f"Project context file not found: {self.args.project_context}")
                return True
                
            with open(self.args.project_context, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Parse project context
            self.project_context = self._parse_project_context(content)
            return True
            
        except Exception as e:
            self.issues.append(f"Failed to load project context: {e}")
            return False
    
    def verify_document(self) -> Tuple[bool, List[str], List[str]]:
        """Main verification function."""
        # Load reference documents
        if not self.load_locked_decisions():
            return False, self.issues, self.warnings
            
        if not self.load_project_context():
            return False, self.issues, self.warnings
        
        # Verify file exists and is readable
        if not os.path.exists(self.args.file_path):
            self.issues.append(f"Document not found: {self.args.file_path}")
            return False, self.issues, self.warnings
            
        try:
            with open(self.args.file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            self.issues.append(f"Failed to read document: {e}")
            return False, self.issues, self.warnings
            
        # Check if file is empty
        if not content.strip():
            self.issues.append("Document is empty")
            return False, self.issues, self.warnings
        
        # Route to specific verifier based on document type
        if self.args.document_type == "story":
            self._verify_story(content)
        elif self.args.document_type == "architecture":
            self._verify_architecture(content)
        elif self.args.document_type == "prd":
            self._verify_prd(content)
        elif self.args.document_type == "epics":
            self._verify_epics(content)
        elif self.args.document_type == "code-review":
            self._verify_code_review(content)
        elif self.args.document_type == "retrospective":
            self._verify_retrospective(content)
        else:
            self.warnings.append(f"Unknown document type: {self.args.document_type}")
            self._verify_generic(content)
        
        # Final validation against locked decisions
        self._validate_against_locked_decisions(content)
        
        return len(self.issues) == 0, self.issues, self.warnings
    
    def _verify_story(self, content: str):
        """Verify story document."""
        # Check for required sections
        required_sections = ["Acceptance Criteria", "Technical Requirements"]
        for section in required_sections:
            if not re.search(rf"##?\s*{re.escape(section)}", content, re.IGNORECASE):
                self.issues.append(f"Missing required section: {section}")
        
        # Check for story ID
        if not re.search(r"Story-\d+|STORY-\d+", content):
            self.issues.append("Missing or invalid story ID format")
        
        # Check acceptance criteria are testable
        ac_match = re.search(r"##?\s*Acceptance\s*Criteria\s*\n(.+?)(?=##|\n\n|$)", content, re.IGNORECASE | re.DOTALL)
        if ac_match:
            ac_content = ac_match.group(1)
            # Look for non-testable criteria
            if re.search(r"(understand|know|learn|familiar)", ac_content, re.IGNORECASE):
                self.warnings.append("Acceptance criteria may not be testable (contains 'understand/know/learn')")
        
        # Check for scope indicators
        if re.search(r"future|later|next\s+release|phase\s+2", content, re.IGNORECASE):
            self.warnings.append("Story may contain future scope items")
    
    def _verify_architecture(self, content: str):
        """Verify architecture document."""
        # Check for architectural decisions
        if not re.search(r"decision|architecture|component|system", content, re.IGNORECASE):
            self.issues.append("Architecture document lacks clear architectural decisions")
        
        # Check for rationale
        if not re.search(r"rationale|why|because|reason", content, re.IGNORECASE):
            self.warnings.append("Architecture decisions may lack rationale")
        
        # Check for technology specifications
        tech_patterns = [r"\.js$", r"\.py$", r"\.java$", r"database|db$", r"api|rest|graphql"]
        has_tech = any(re.search(pattern, content, re.IGNORECASE) for pattern in tech_patterns)
        if not has_tech:
            self.warnings.append("Architecture document may lack technology specifications")
    
    def _verify_prd(self, content: str):
        """Verify PRD document."""
        # Check for problem statement
        if not re.search(r"problem|challenge|issue|need", content, re.IGNORECASE):
            self.issues.append("PRD lacks clear problem statement")
        
        # Check for success metrics
        if not re.search(r"metric|kpi|measure|success|goal", content, re.IGNORECASE):
            self.issues.append("PRD lacks success metrics or KPIs")
        
        # Check for scope boundaries
        if not re.search(r"scope|boundary|exclude|out\s+of\s+scope", content, re.IGNORECASE):
            self.warnings.append("PRD may lack clear scope boundaries")
    
    def _verify_epics(self, content: str):
        """Verify epics and stories document."""
        # Check for epic structure
        if not re.search(r"epic|user\s+story", content, re.IGNORECASE):
            self.issues.append("Epics document lacks epic or story structure")
        
        # Check for story breakdown
        story_count = len(re.findall(r"story-\d+|user\s+story", content, re.IGNORECASE))
        if story_count == 0:
            self.issues.append("No stories found in epics document")
        elif story_count < 3:
            self.warnings.append("Very few stories found in epics document")
    
    def _verify_code_review(self, content: str):
        """Verify code review triage."""
        # Check for classifications
        classifications = ["patch", "defer", "intent_gap", "bad_spec"]
        found_classifications = []
        
        for classification in classifications:
            if re.search(rf"\b{re.escape(classification)}\b", content, re.IGNORECASE):
                found_classifications.append(classification)
        
        if not found_classifications:
            self.issues.append("Code review lacks finding classifications")
        
        # Check for remediation instructions
        if not re.search(r"fix|remediat|action|step", content, re.IGNORECASE):
            self.issues.append("Code review lacks remediation instructions")
        
        # Check for priority assessment
        if not re.search(r"priority|severity|impact|critical", content, re.IGNORECASE):
            self.warnings.append("Code review may lack priority assessment")
    
    def _verify_retrospective(self, content: str):
        """Verify retrospective document."""
        # Check for retrospective sections
        sections = ["what went well", "what didn't", "improvements", "action items"]
        found_sections = []
        
        for section in sections:
            if re.search(rf"##?\s*{re.escape(section)}", content, re.IGNORECASE):
                found_sections.append(section)
        
        if len(found_sections) < 2:
            self.warnings.append("Retrospective may be missing standard sections")
    
    def _verify_generic(self, content: str):
        """Generic document verification."""
        # Basic structure checks
        if len(content) < 100:
            self.warnings.append("Document is very short")
        
        # Check for markdown structure
        if not re.search(r"^#+", content, re.MULTILINE):
            self.warnings.append("Document lacks markdown heading structure")
    
    def _validate_against_locked_decisions(self, content: str):
        """Validate document against locked decisions."""
        if not self.locked_decisions:
            return
        
        # Check for common conflicts
        for decision_key, decision_value in self.locked_decisions.items():
            # Simple conflict detection - can be enhanced
            if isinstance(decision_value, str):
                # Look for contradictory statements
                if re.search(rf"\b{re.escape(decision_value)}\b", content, re.IGNORECASE):
                    # This is very basic - real implementation would be more sophisticated
                    pass
    
    def _parse_markdown_decisions(self, content: str) -> Dict:
        """Parse locked decisions from markdown."""
        decisions = {}
        # Simple parsing - can be enhanced with proper markdown parsing
        sections = re.split(r"^##+", content, flags=re.MULTILINE)
        
        for section in sections:
            if ":" in section:
                lines = section.strip().split('\n')
                if lines:
                    key = lines[0].split(':')[0].strip()
                    value = ':'.join(lines[0].split(':')[1:]).strip()
                    if key and value:
                        decisions[key] = value
        
        return decisions
    
    def _parse_project_context(self, content: str) -> Dict:
        """Parse project context from markdown."""
        context = {}
        # Simple parsing - can be enhanced
        lines = content.split('\n')
        for line in lines:
            if ':' in line and not line.startswith('#'):
                key, value = line.split(':', 1)
                context[key.strip()] = value.strip()
        
        return context
    
    def print_results(self, is_valid: bool, issues: List[str], warnings: List[str]):
        """Print verification results."""
        print(f"\n## Document Verification Results")
        print(f"**Document:** {self.args.file_path}")
        print(f"**Type:** {self.args.document_type}")
        print(f"**Status:** {'PASS' if is_valid else 'FAIL'}")
        print(f"**Timestamp:** {self._get_timestamp()}")
        
        if issues:
            print(f"\n**Critical Issues ({len(issues)}):**")
            for i, issue in enumerate(issues, 1):
                print(f"{i}. {issue}")
        
        if warnings:
            print(f"\n**Warnings ({len(warnings)}):**")
            for i, warning in enumerate(warnings, 1):
                print(f"{i}. {warning}")
        
        if not issues and not warnings:
            print(f"\n**Summary:** Document passes all verification checks")
        
        print(f"\n**Next Steps:**")
        if issues:
            print("- Fix critical issues before proceeding")
            print("- Re-run verification after fixes")
        else:
            print("- Document is ready for progression")
            print("- Commit to version control")
        
        return is_valid
    
    def _get_timestamp(self) -> str:
        """Get current timestamp."""
        from datetime import datetime
        return datetime.now().isoformat()

def main():
    parser = argparse.ArgumentParser(description="Verify BMAD documents against standards")
    parser.add_argument("--document-type", required=True, 
                       choices=["story", "architecture", "prd", "epics", "code-review", "retrospective"],
                       help="Type of document to verify")
    parser.add_argument("--file-path", required=True, help="Path to document file")
    parser.add_argument("--locked-decisions", 
                       default="_bmad/bmad-crew/locked-decisions.md",
                       help="Path to locked decisions file")
    parser.add_argument("--project-context", 
                       default="project-context.md",
                       help="Path to project context file")
    parser.add_argument("--output-format", default="markdown",
                       choices=["markdown", "json"],
                       help="Output format for results")
    
    args = parser.parse_args()
    
    verifier = DocumentVerifier(args)
    is_valid, issues, warnings = verifier.verify_document()
    
    if args.output_format == "json":
        result = {
            "valid": is_valid,
            "document": args.file_path,
            "type": args.document_type,
            "issues": issues,
            "warnings": warnings,
            "timestamp": verifier._get_timestamp()
        }
        print(json.dumps(result, indent=2))
    else:
        verifier.print_results(is_valid, issues, warnings)
    
    sys.exit(0 if is_valid else 1)

if __name__ == "__main__":
    main()
