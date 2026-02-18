#!/bin/bash

# Validator script for reference fill workflow - validates completed files
# Usage: ./validator.sh <input_path> <output_path> [reference_type]

set -e

# Default values
INPUT_PATH="$1"
OUTPUT_PATH="${2:-./outputs/validation/validation_results.json}"
REFERENCE_TYPE="${3:-flashscore}"

# Validate input parameters
if [[ -z "$INPUT_PATH" ]]; then
    echo "Error: Input path is required"
    echo "Usage: $0 <input_path> [output_path] [reference_type]"
    exit 1
fi

echo "Validating reference files in: $INPUT_PATH"

# Create output directory if it doesn't exist
mkdir -p "$(dirname "$OUTPUT_PATH")"

# Generate validation ID
VALIDATION_ID="validation_$(date +%Y%m%d_%H%M%S)"

# Get reference files
FILES=$(find "$INPUT_PATH" -type f \( -name "*.md" -o -name "*.html" \))

# Initialize JSON structure
cat > "$OUTPUT_PATH" << EOF
{
    "validation_metadata": {
        "validation_id": "$VALIDATION_ID",
        "validation_date": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
        "script_version": "1.0.0",
        "validator_settings": {
            "input_path": "$INPUT_PATH",
            "reference_type": "$REFERENCE_TYPE",
            "output_path": "$OUTPUT_PATH"
        }
    },
    "summary": {
        "total_files_validated": 0,
        "files_by_status": {
            "passed": 0,
            "failed": 0,
            "warning": 0
        },
        "files_by_category": {
            "scheduled": {"total": 0, "passed": 0, "failed": 0},
            "live": {"total": 0, "passed": 0, "failed": 0},
            "finished": {"total": 0, "passed": 0, "failed": 0}
        }
    },
    "quality_metrics": {
        "template_compliance": 0,
        "html_quality": 0,
        "metadata_completeness": 0,
        "selector_documentation": 0
    },
    "files": [
EOF

# Process each file
file_count=0
passed_count=0
failed_count=0
warning_count=0

while IFS= read -r file; do
    if [[ -z "$file" ]]; then continue; fi
    
    file_count=$((file_count + 1))
    filename=$(basename "$file")
    extension="${filename##*.}"
    relative_path="${file#$INPUT_PATH/}"
    relative_path="${relative_path#/}"
    
    # Initialize file validation
    validation_status="unknown"
    completeness_score=0
    issues=()
    warnings=()
    
    if [[ "$extension" == "md" ]]; then
        # Validate markdown file
        content=$(cat "$file")
        
        # Check required sections
        if [[ ! "$content" =~ "## Summary" ]]; then
            issues+=("Missing required section: ## Summary")
        fi
        
        if [[ ! "$content" =~ "## HTML" ]]; then
            issues+=("Missing required section: ## HTML")
        fi
        
        if [[ ! "$content" =~ "## Notes" ]]; then
            issues+=("Missing required section: ## Notes")
        fi
        
        # Check for HTML block
        if [[ ! "$content" =~ "```html" ]]; then
            issues+=("Missing HTML code block")
        fi
        
        # Check metadata
        if [[ "$content" =~ "\*\*Source URL:\*\*" ]]; then
            completeness_score=$((completeness_score + 20))
        else
            warnings+=("Missing source URL metadata")
        fi
        
        if [[ "$content" =~ "\*\*Date Collected:\*\*" ]]; then
            completeness_score=$((completeness_score + 20))
        else
            warnings+=("Missing date collected metadata")
        fi
        
        # Check selector documentation
        if [[ "$content" =~ "### Selector Patterns" ]]; then
            completeness_score=$((completeness_score + 20))
        else
            warnings+=("Missing selector patterns documentation")
        fi
        
        # Check active state indicators
        if [[ "$content" =~ "### Active State Indicators" ]]; then
            completeness_score=$((completeness_score + 20))
        else
            warnings+=("Missing active state indicators")
        fi
        
        # Check match state differences
        if [[ "$content" =~ "### Match State Differences" ]]; then
            completeness_score=$((completeness_score + 20))
        else
            warnings+=("Missing match state differences")
        fi
        
        # Determine validation status
        if [[ ${#issues[@]} -gt 0 ]]; then
            validation_status="failed"
            failed_count=$((failed_count + 1))
        elif [[ ${#warnings[@]} -gt 0 ]]; then
            validation_status="warning"
            warning_count=$((warning_count + 1))
        else
            validation_status="passed"
            passed_count=$((passed_count + 1))
        fi
        
    elif [[ "$extension" == "html" ]]; then
        # Basic HTML validation
        content=$(cat "$file")
        
        if [[ "$content" =~ "<html" && "$content" =~ "</html>" ]]; then
            validation_status="passed"
            completeness_score=100
            passed_count=$((passed_count + 1))
        else
            validation_status="failed"
            issues+=("Invalid HTML structure")
            failed_count=$((failed_count + 1))
        fi
    fi
    
    # Add comma if not first file
    if [[ $file_count -gt 1 ]]; then
        echo "," >> "$OUTPUT_PATH"
    fi
    
    # Add file validation to JSON
    cat >> "$OUTPUT_PATH" << EOF
        {
            "path": "$file",
            "name": "$filename",
            "extension": ".$extension",
            "size": $(stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null || echo 0),
            "last_modified": "$(date -r "$file" -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u +%Y-%m-%dT%H:%M:%SZ)",
            "relative_path": "$relative_path",
            "validation_status": "$validation_status",
            "completeness_score": $completeness_score,
            "issues": [$(printf '"%s",' "${issues[@]}" | sed 's/,$//')],
            "warnings": [$(printf '"%s",' "${warnings[@]}" | sed 's/,$//')]
        }
EOF
    
done <<< "$FILES"

# Close JSON structure
cat >> "$OUTPUT_PATH" << EOF
    ]
}
EOF

# Update summary counts
sed -i.tmp "s/\"total_files_validated\": 0/\"total_files_validated\": $file_count/" "$OUTPUT_PATH"
sed -i.tmp "s/\"passed\": 0/\"passed\": $passed_count/" "$OUTPUT_PATH"
sed -i.tmp "s/\"failed\": 0/\"failed\": $failed_count/" "$OUTPUT_PATH"
sed -i.tmp "s/\"warning\": 0/\"warning\": $warning_count/" "$OUTPUT_PATH"
rm -f "$OUTPUT_PATH.tmp"

# Calculate quality metrics
if [[ $file_count -gt 0 ]]; then
    template_compliance=$(echo "scale=2; $passed_count * 100 / $file_count" | bc -l)
    sed -i.tmp "s/\"template_compliance\": 0/\"template_compliance\": $template_compliance/" "$OUTPUT_PATH"
    rm -f "$OUTPUT_PATH.tmp"
fi

echo "Validation complete!"
echo "Validation ID: $VALIDATION_ID"
echo "Total files: $file_count"
echo "Passed: $passed_count"
echo "Failed: $failed_count"
echo "Warnings: $warning_count"
echo "Results saved to: $OUTPUT_PATH"

# Return success
echo "{\"success\": true, \"validation_id\": \"$VALIDATION_ID\", \"total_files\": $file_count, \"passed\": $passed_count, \"failed\": $failed_count, \"warnings\": $warning_count, \"output_file\": \"$OUTPUT_PATH\"}"
