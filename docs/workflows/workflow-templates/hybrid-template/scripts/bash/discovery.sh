#!/bin/bash

# Discovery script for hybrid workflows - identifies targets for processing
#
# Usage: ./discovery.sh <input-path> [output-file] [pattern]

set -euo pipefail

# Default values
INPUT_PATH="${1:-}"
OUTPUT_FILE="${2:-./discovery.json}"
PATTERN="${3:-*}"

# Validate input
if [ -z "$INPUT_PATH" ]; then
    echo "Error: Input path required"
    echo "Usage: $0 <input-path> [output-file] [pattern]"
    exit 1
fi

if [ ! -d "$INPUT_PATH" ]; then
    echo "Error: Input path does not exist: $INPUT_PATH"
    exit 1
fi

echo "Starting discovery in: $INPUT_PATH"

# Create temporary file for processing
TEMP_FILE=$(mktemp)
trap "rm -f $TEMP_FILE" EXIT

# Find files matching pattern
find "$INPUT_PATH" -type f -name "$PATTERN" | while read -r file; do
    # Get file info
    name=$(basename "$file")
    extension="${name##*.}"
    size=$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null || echo "0")
    modified=$(stat -f%Sm -t%Y-%m-%dT%H:%M:%SZ "$file" 2>/dev/null || stat -c%y "$file" 2>/dev/null | cut -d' ' -f1-2 | tr ' ' 'T' || echo "unknown")
    relative_path="${file#$INPUT_PATH}"
    relative_path="${relative_path#/}"  # Remove leading slash
    
    # Determine file type and processability
    case "$extension" in
        "js")
            type="javascript"
            processable="true"
            ;;
        "md")
            type="markdown"
            processable="true"
            ;;
        *)
            type="other"
            processable="false"
            ;;
    esac
    
    # Output JSON for this file
    cat << EOF
{
  "path": "$file",
  "name": "$name",
  "extension": ".$extension",
  "size": $size,
  "last_modified": "$modified",
  "relative_path": "$relative_path",
  "type": "$type",
  "processable": $processable
},
EOF
done > "$TEMP_FILE"

# Build final JSON
total_files=$(wc -l < "$TEMP_FILE")
total_files=$((total_files))  # Convert to number

cat << EOF > "$OUTPUT_FILE"
{
  "metadata": {
    "scan_time": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "input_path": "$INPUT_PATH",
    "pattern": "$PATTERN",
    "total_files": $total_files
  },
  "targets": [
$(sed '$ s/,$//' "$TEMP_FILE")
  ]
}
EOF

echo "Discovery complete!"
echo "Found $total_files files"
echo "Results saved to: $OUTPUT_FILE"

# Return success
exit 0
