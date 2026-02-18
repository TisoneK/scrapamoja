#!/bin/bash

# Generator script for reference fill workflow - creates content for reference files
#
# Usage: ./generator.sh <input-file> [template-path] [output-path] [--dry-run]

set -euo pipefail

# Default values
INPUT_FILE="${1:-}"
TEMPLATE_PATH="${2:-./templates}"
OUTPUT_PATH="${3:-./output}"
DRY_RUN=""

# Parse arguments
shift 3
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN="--dry-run"
            shift
            ;;
        *)
            echo "Unknown argument: $1"
            exit 1
            ;;
    esac
done

# Validate input
if [ -z "$INPUT_FILE" ]; then
    echo "Error: Input file required"
    echo "Usage: $0 <input-file> [template-path] [output-path] [--dry-run]"
    exit 1
fi

if [ ! -f "$INPUT_FILE" ]; then
    echo "Error: Input file not found: $INPUT_FILE"
    exit 1
fi

# Check if jq is available
if ! command -v jq &> /dev/null; then
    echo "Error: jq is required for JSON processing"
    exit 1
fi

echo "Starting content generator..."

# Load generated content
file_count=$(jq '.files | length' "$INPUT_FILE")
echo "Loaded $file_count files to generate"

# Create output directory
if [ -z "$DRY_RUN" ]; then
    mkdir -p "$OUTPUT_PATH"
fi

# Create results JSON
RESULTS_FILE="${INPUT_FILE%.json}_results.json"
START_TIME=$(date -u +%Y-%m-%dT%H:%M:%SZ)

# Initialize results
cat << EOF > "$RESULTS_FILE"
{
  "metadata": {
    "start_time": "$START_TIME",
    "input_file": "$INPUT_FILE",
    "template_path": "$TEMPLATE_PATH",
    "dry_run": $([ -n "$DRY_RUN" ] && echo "true" || echo "false")
  },
  "generated": [],
  "errors": [],
  "skipped": []
}
EOF

# Process each file
for ((i=0; i<file_count; i++)); do
    filename=$(jq -r ".files[$i].filename" "$INPUT_FILE")
    target_path="$OUTPUT_PATH/$filename"
    
    echo "Generating: $filename"
    
    # Build file content
    content_parts=()
    
    # Add frontmatter
    if jq -e ".files[$i].metadata" "$INPUT_FILE" > /dev/null; then
        content_parts+=("---")
        # Add each metadata field
        jq -r ".files[$i].metadata | to_entries[] | \"\(.key): \"\(.value)\"\"" "$INPUT_FILE" | while read -r line; do
            content_parts+=("$line")
        done
        content_parts+=("---")
        content_parts+=("")
    fi
    
    # Add sections
    if jq -e ".files[$i].sections" "$INPUT_FILE" > /dev/null; then
        section_count=$(jq ".files[$i].sections | length" "$INPUT_FILE")
        for ((j=0; j<section_count; j++)); do
            title=$(jq -r ".files[$i].sections[$j].title" "$INPUT_FILE")
            section_content=$(jq -r ".files[$i].sections[$j].content" "$INPUT_FILE")
            
            content_parts+=("## $title")
            content_parts+=("")
            content_parts+=("$section_content")
            content_parts+=("")
        done
    fi
    
    # Add HTML sample if provided
    if jq -e ".files[$i].html_sample" "$INPUT_FILE" > /dev/null; then
        html_sample=$(jq -r ".files[$i].html_sample" "$INPUT_FILE")
        content_parts+=("## HTML Sample")
        content_parts+=("")
        content_parts+=("```html")
        content_parts+=("$html_sample")
        content_parts+=("```")
        content_parts+=("")
    fi
    
    # Add summary if provided
    if jq -e ".files[$i].summary" "$INPUT_FILE" > /dev/null; then
        summary=$(jq -r ".files[$i].summary" "$INPUT_FILE")
        content_parts+=("## Summary")
        content_parts+=("")
        content_parts+=("$summary")
        content_parts+=("")
    fi
    
    # Add usage if provided
    if jq -e ".files[$i].usage" "$INPUT_FILE" > /dev/null; then
        usage=$(jq -r ".files[$i].usage" "$INPUT_FILE")
        content_parts+=("## Usage")
        content_parts+=("")
        content_parts+=("$usage")
        content_parts+=("")
    fi
    
    # Add notes if provided
    if jq -e ".files[$i].notes" "$INPUT_FILE" > /dev/null; then
        notes=$(jq -r ".files[$i].notes" "$INPUT_FILE")
        content_parts+=("## Notes")
        content_parts+=("")
        content_parts+=("$notes")
        content_parts+=("")
    fi
    
    # Join content parts
    final_content=$(IFS=$'\n'; echo "${content_parts[*]}")
    content_length=${#final_content}
    
    if [ -n "$DRY_RUN" ]; then
        echo "  [DRY RUN] Would create: $target_path"
        echo "  Content length: $content_length characters"
    else
        # Create directory if needed
        dir=$(dirname "$target_path")
        mkdir -p "$dir"
        
        # Write file
        echo "$final_content" > "$target_path"
        
        echo "  ✓ Generated successfully"
    fi
    
    # Record successful generation
    jq --arg filename "$filename" --arg path "$target_path" --arg size "$content_length" --arg time "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
       '.generated += [{"filename": $filename, "path": $path, "status": "success", "size": ($size | tonumber), "timestamp": $time}]' \
       "$RESULTS_FILE" > "${RESULTS_FILE}.tmp" && mv "${RESULTS_FILE}.tmp" "$RESULTS_FILE"
done

# Finalize results
END_TIME=$(date -u +%Y-%m-%dT%H:%M:%SZ)
generated_count=$(jq '.generated | length' "$RESULTS_FILE")
error_count=$(jq '.errors | length' "$RESULTS_FILE")

jq --arg end_time "$END_TIME" --arg generated "$generated_count" --arg errors "$error_count" \
   '.metadata.end_time = $end_time | .metadata.total_generated = ($generated | tonumber) | .metadata.total_errors = ($errors | tonumber)' \
   "$RESULTS_FILE" > "${RESULTS_FILE}.tmp" && mv "${RESULTS_FILE}.tmp" "$RESULTS_FILE"

echo "Generation complete!"
echo "Generated: $generated_count files"
echo "Errors: $error_count"
echo "Results saved to: $RESULTS_FILE"

# Return success
exit 0
