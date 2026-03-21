#!/usr/bin/env python3
"""
Decision Manager Script for BMAD Crew Locked Decisions

Manages living document of locked decisions and handles decision challenges.
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path


def load_decisions(decisions_file: str) -> dict:
    """Load existing decisions from file."""
    try:
        if Path(decisions_file).exists():
            with open(decisions_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse YAML-like content (simplified parser)
            decisions = {
                "metadata": {},
                "decisions": [],
                "last_updated": None
            }
            
            lines = content.split('\n')
            current_section = None
            current_decision = None
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                if line.startswith('# '):
                    current_section = line[2:].lower()
                    if current_section == 'metadata':
                        continue
                elif line.startswith('## '):
                    if current_decision:
                        decisions["decisions"].append(current_decision)
                    current_decision = {
                        "id": line[3:].strip(),
                        "created": None,
                        "category": None,
                        "scope": None,
                        "description": "",
                        "rationale": "",
                        "challenges": []
                    }
                elif current_decision and line.startswith('- **'):
                    # Parse decision fields
                    if 'created:' in line.lower():
                        current_decision["created"] = line.split('created:')[1].strip()
                    elif 'category:' in line.lower():
                        current_decision["category"] = line.split('category:')[1].strip()
                    elif 'scope:' in line.lower():
                        current_decision["scope"] = line.split('scope:')[1].strip()
                elif current_decision and line.startswith('**Description:**'):
                    current_decision["description"] = line.replace('**Description:**', '').strip()
                elif current_decision and line.startswith('**Rationale:**'):
                    current_decision["rationale"] = line.replace('**Rationale:**', '').strip()
                elif current_decision and line.startswith('**Challenge Process:**'):
                    current_decision["challenge_process"] = line.replace('**Challenge Process:**', '').strip()
            
            if current_decision:
                decisions["decisions"].append(current_decision)
            
            return decisions
        else:
            return {
                "metadata": {"created": datetime.now().isoformat()},
                "decisions": [],
                "last_updated": None
            }
    except Exception as e:
        return {
            "metadata": {"error": str(e)},
            "decisions": [],
            "last_updated": None
        }


def save_decisions(decisions_file: str, decisions: dict) -> bool:
    """Save decisions to file in markdown format."""
    try:
        content = []
        content.append("# Locked Decisions")
        content.append("")
        content.append("This document contains all locked decisions for BMAD sessions.")
        content.append("")
        
        # Metadata
        content.append("## Metadata")
        content.append(f"- **Created:** {decisions.get('metadata', {}).get('created', datetime.now().isoformat())}")
        content.append(f"- **Last Updated:** {datetime.now().isoformat()}")
        content.append("")
        
        # Decisions
        for decision in decisions.get("decisions", []):
            content.append(f"## {decision['id']}")
            content.append("")
            content.append(f"- **Created:** {decision.get('created', 'Unknown')}")
            content.append(f"- **Category:** {decision.get('category', 'General')}")
            content.append(f"- **Scope:** {decision.get('scope', 'Session')}")
            content.append("")
            content.append(f"**Description:** {decision.get('description', 'No description')}")
            content.append("")
            content.append(f"**Rationale:** {decision.get('rationale', 'No rationale')}")
            content.append("")
            
            if 'challenge_process' in decision:
                content.append(f"**Challenge Process:** {decision['challenge_process']}")
                content.append("")
            
            if decision.get('challenges'):
                content.append("**Challenges:**")
                for challenge in decision['challenges']:
                    content.append(f"- {challenge}")
                content.append("")
        
        with open(decisions_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(content))
        
        return True
    except Exception as e:
        return False


def find_relevant_decisions(decisions: dict, context: dict) -> list:
    """Find decisions relevant to current context."""
    relevant = []
    
    category = context.get('category', '').lower()
    scope = context.get('scope', '').lower()
    agent = context.get('agent', '').lower()
    
    for decision in decisions.get('decisions', []):
        decision_category = decision.get('category', '').lower()
        decision_scope = decision.get('scope', '').lower()
        description = decision.get('description', '').lower()
        
        # Check relevance
        is_relevant = False
        
        if category and category in decision_category:
            is_relevant = True
        elif scope and scope in decision_scope:
            is_relevant = True
        elif agent and agent in description:
            is_relevant = True
        
        if is_relevant:
            relevant.append(decision)
    
    return relevant


def add_decision(decisions: dict, decision_data: dict) -> dict:
    """Add a new locked decision."""
    new_decision = {
        "id": decision_data.get('id', f"decision-{len(decisions['decisions']) + 1}"),
        "created": datetime.now().isoformat(),
        "category": decision_data.get('category', 'General'),
        "scope": decision_data.get('scope', 'Session'),
        "description": decision_data.get('description', ''),
        "rationale": decision_data.get('rationale', ''),
        "challenge_process": decision_data.get('challenge_process', 'Standard challenge process applies'),
        "challenges": []
    }
    
    decisions['decisions'].append(new_decision)
    return decisions


def challenge_decision(decisions: dict, decision_id: str, challenge_data: dict) -> dict:
    """Record a challenge to an existing decision."""
    for decision in decisions['decisions']:
        if decision['id'] == decision_id:
            challenge = {
                "timestamp": datetime.now().isoformat(),
                "challenger": challenge_data.get('challenger', 'Unknown'),
                "reason": challenge_data.get('reason', ''),
                "proposed_change": challenge_data.get('proposed_change', ''),
                "status": "pending"
            }
            decision['challenges'].append(challenge)
            break
    
    return decisions


def main():
    parser = argparse.ArgumentParser(description="Manage locked decisions")
    parser.add_argument("--decisions-file", default="locked-decisions.md", help="Path to decisions file")
    parser.add_argument("--load", action="store_true", help="Load existing decisions")
    parser.add_argument("--add", action="store_true", help="Add new decision")
    parser.add_argument("--challenge", help="Challenge existing decision by ID")
    parser.add_argument("--find", action="store_true", help="Find relevant decisions")
    parser.add_argument("--context", help="JSON file with context for finding relevant decisions")
    parser.add_argument("--decision-data", help="JSON file with new decision data")
    parser.add_argument("--challenge-data", help="JSON file with challenge data")
    parser.add_argument("--output", "-o", help="Output JSON file")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    results = {
        "script": "decision-manager.py",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat(),
        "status": "pass",
        "findings": [],
        "decisions": {},
        "relevant_decisions": []
    }
    
    # Load existing decisions
    decisions = load_decisions(args.decisions_file)
    results["decisions"] = decisions
    
    # Process commands
    if args.load:
        results["action"] = "load"
        results["message"] = f"Loaded {len(decisions['decisions'])} decisions from {args.decisions_file}"
    
    elif args.add:
        if args.decision_data:
            try:
                with open(args.decision_data, 'r') as f:
                    decision_data = json.load(f)
                
                decisions = add_decision(decisions, decision_data)
                
                if save_decisions(args.decisions_file, decisions):
                    results["action"] = "add"
                    results["message"] = f"Added decision {decision_data.get('id', 'unknown')} to {args.decisions_file}"
                else:
                    results["status"] = "fail"
                    results["message"] = f"Failed to save decisions to {args.decisions_file}"
            except Exception as e:
                results["status"] = "fail"
                results["message"] = f"Error loading decision data: {e}"
        else:
            results["status"] = "fail"
            results["message"] = "Decision data file required when adding new decision"
    
    elif args.challenge:
        if args.challenge_data:
            try:
                with open(args.challenge_data, 'r') as f:
                    challenge_data = json.load(f)
                
                decisions = challenge_decision(decisions, args.challenge, challenge_data)
                
                if save_decisions(args.decisions_file, decisions):
                    results["action"] = "challenge"
                    results["message"] = f"Recorded challenge to decision {args.challenge}"
                else:
                    results["status"] = "fail"
                    results["message"] = f"Failed to save challenge to {args.decisions_file}"
            except Exception as e:
                results["status"] = "fail"
                results["message"] = f"Error loading challenge data: {e}"
        else:
            results["status"] = "fail"
            results["message"] = "Challenge data file required when challenging decision"
    
    elif args.find:
        if args.context:
            try:
                with open(args.context, 'r') as f:
                    context = json.load(f)
                
                relevant = find_relevant_decisions(decisions, context)
                results["action"] = "find"
                results["relevant_decisions"] = relevant
                results["message"] = f"Found {len(relevant)} relevant decisions"
            except Exception as e:
                results["status"] = "fail"
                results["message"] = f"Error loading context: {e}"
        else:
            results["action"] = "find"
            results["relevant_decisions"] = decisions['decisions']
            results["message"] = f"Returning all {len(decisions['decisions'])} decisions"
    
    else:
        results["status"] = "fail"
        results["message"] = "No action specified. Use --load, --add, --challenge, or --find"
    
    # Output results
    json_output = json.dumps(results, indent=2)
    
    if args.output:
        with open(args.output, 'w') as f:
            f.write(json_output)
        if args.verbose:
            print(f"Results written to {args.output}")
    else:
        print(json_output)
    
    # Set exit code
    sys.exit(0 if results["status"] == "pass" else 1)


if __name__ == "__main__":
    main()
