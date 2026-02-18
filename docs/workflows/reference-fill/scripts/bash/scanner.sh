#!/bin/bash

# Scanner script for reference fill workflow - identifies incomplete reference files
#
# Usage: ./scanner.sh <input-path> [output-file] [reference-type]

set -euo pipefail

# Default values
INPUT_PATH="${1:-}"
OUTPUT_FILE="${2:-./scan.json}"
REFERENCE_TYPE="${3:-flashscore}"

# Validate input
if [ -z "$INPUT_PATH" ]; then
    echo "Error: Input path required"
    echo "Usage: $0 <input-path> [output-file] [reference-type]"
    exit 1
fi

if [ ! -d "$INPUT_PATH" ]; then
    echo "Error: Input path does not exist: $INPUT_PATH"
    exit 1
fi

echo "Scanning reference files in: $INPUT_PATH"

# Create temporary file for processing
TEMP_FILE=$(mktemp)
trap "rm -f $TEMP_FILE" EXIT

# Find reference files
find "$INPUT_PATH" -type f \( -name "*.md" -o -name "*.html" \) | while read -r file; do
    name=$(basename "$file")
    extension="${name##*.}"
    size=$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null || echo "0")
    modified=$(stat -f%Sm -t%Y-%m-%dT%H:%M:%SZ "$file" 2>/dev/null || stat -c%y "$file" 2>/dev/null | cut -d' ' -f1-2 | tr ' ' 'T' || echo "unknown")
    relative_path="${file#$INPUT_PATH}"
    relative_path="${relative_path#/}"
    
    # Initialize file info
    status="unknown"
    completeness=0
    issues=""
    
    # Analyze file content
    if [ "$extension" = "md" ]; then
        content=$(cat "$file")
        
        # Check for required sections
        required_sections=("title" "match_state" "primary_tab" "tab_level" "description")
        missing_sections=()
        
        # Check if file has frontmatter
        if echo "$content" | grep -q "^---"; then
            # Extract frontmatter
            frontmatter=$(echo "$content" | sed -n '/^---/,/^---/p' | sed '1d;$d')
            
            for section in "${required_sections[@]}"; do
                if ! echo "$frontmatter" | grep -q "^$section:"; then
                    missing_sections+=("$section")
                fi
            done
        else
            missing_sections=("${required_sections[@]}")
        fi
        
        if [ ${#missing_sections[@]} -gt 0 ]; then
            status="incomplete"
            issues="Missing metadata sections: $(IFS=', '; echo "${missing_sections[*]}")"
            completeness=50
        else
            status="complete"
            completeness=100
        fi
        
        # Check for HTML sample
        if ! echo "$content" | grep -q "```html" && ! echo "$content" | grep -q "## HTML Sample"; then
            status="incomplete"
            issues="$issues; Missing HTML sample section"
            completeness=$((completeness - 30))
            [ $completeness -lt 0 ] && completeness=0
        fi
        
        # Check for summary
        if ! echo "$content" | grep -q "## Summary" && ! echo "$content" | grep -q "## Usage"; then
            status="incomplete"
            issues="$issues; Missing summary or usage section"
            completeness=$((completeness - 20))
            [ $completeness -lt 0 ] && completeness=0
        fi
        
    elif [ "$extension" = "html" ]; then
        content=$(cat "$file")
        
        # Basic HTML validation
        if echo "$content" | grep -q "<html" && echo "$content" | grep -q "</html>"; then
            status="complete"
            completeness=100
        else
            status="invalid"
            issues="Invalid HTML structure"
            completeness=25
        fi
    fi
    
    # Convert issues array to JSON-friendly format
    issues_json=$(echo "$issues" | sed 's/; /", "/g' | sed 's/^"/["' | sed 's/$/"]/')
    
    # Output JSON for this file
    cat << EOF
{
  "path": "$file",
  "name": "$name",
  "extension": ".$extension",
  "size": $size,
  "last_modified": "$modified",
  "relative_path": "$relative_path",
  "status": "$status",
  "completeness": $completeness,
  "issues": $issues_json
},
EOF
done > "$TEMP_FILE"

# Build final JSON
total_files=$(wc -l < "$TEMP_FILE")
total_files=$((total_files))

# Calculate statistics
incomplete_count=$(grep -c '"status": "incomplete"' "$TEMP_FILE" 2>/dev/null || echo "0")
complete_count=$(grep -c '"status": "complete"' "$TEMP_FILE" 2>/dev/null || echo "0")

cat << EOF > "$OUTPUT_FILE"
{
  "metadata": {
    "scan_time": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "input_path": "$INPUT_PATH",
    "reference_type": "$REFERENCE_TYPE",
    "total_files": $total_files,
    "incomplete_count": $incomplete_count,
    "complete_count": $complete_count
  },
  "files": [
$(sed '$ s/,$//' "$TEMP_FILE")
  ]
}
EOF

echo "Scan complete!"
echo "Total files: $total_files"
echo "Complete: $complete_count"
echo "Incomplete: $incomplete_count"
echo "Results saved to: $OUTPUT_FILE"

# Return success
exit 0
