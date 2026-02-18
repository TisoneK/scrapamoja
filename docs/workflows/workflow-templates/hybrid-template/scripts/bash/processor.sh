#!/bin/bash

# Processor script for hybrid workflows - executes LLM decisions
#
# Usage: ./processor.sh <decisions-file> [backup-path] [--dry-run]

set -euo pipefail

# Default values
DECISIONS_FILE="${1:-}"
BACKUP_PATH="${2:-./backup}"
DRY_RUN=""

# Parse arguments
shift 2
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
if [ -z "$DECISIONS_FILE" ]; then
    echo "Error: Decisions file required"
    echo "Usage: $0 <decisions-file> [backup-path] [--dry-run]"
    exit 1
fi

if [ ! -f "$DECISIONS_FILE" ]; then
    echo "Error: Decisions file not found: $DECISIONS_FILE"
    exit 1
fi

echo "Starting processor..."

# Check if jq is available
if ! command -v jq &> /dev/null; then
    echo "Error: jq is required for JSON processing"
    exit 1
fi

# Load decisions
decision_count=$(jq '.decisions | length' "$DECISIONS_FILE")
echo "Loaded $decision_count decisions"

# Create backup directory
if [ -z "$DRY_RUN" ]; then
    mkdir -p "$BACKUP_PATH"
fi

# Create results JSON
RESULTS_FILE="${DECISIONS_FILE%.json}_results.json"
START_TIME=$(date -u +%Y-%m-%dT%H:%M:%SZ)

# Initialize results
cat << EOF > "$RESULTS_FILE"
{
  "metadata": {
    "start_time": "$START_TIME",
    "decisions_file": "$DECISIONS_FILE",
    "dry_run": $([ -n "$DRY_RUN" ] && echo "true" || echo "false"),
    "backup_path": "$BACKUP_PATH"
  },
  "processed": [],
  "errors": [],
  "skipped": []
}
EOF

# Process each decision
for ((i=0; i<decision_count; i++)); do
    decision=$(jq -r ".decisions[$i]" "$DECISIONS_FILE")
    target_file=$(echo "$decision" | jq -r '.target_file')
    action=$(echo "$decision" | jq -r '.action')
    
    echo "Processing: $target_file"
    
    # Check if file exists
    if [ ! -f "$target_file" ]; then
        error_msg="File not found: $target_file"
        echo "  ✗ Error: $error_msg"
        
        # Add to errors
        jq --arg file "$target_file" --arg action "$action" --arg error "$error_msg" --arg time "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
           '.errors += [{"file": $file, "action": $action, "error": $error, "timestamp": $time}]' \
           "$RESULTS_FILE" > "${RESULTS_FILE}.tmp" && mv "${RESULTS_FILE}.tmp" "$RESULTS_FILE"
        continue
    fi
    
    # Backup original file
    if [ -z "$DRY_RUN" ]; then
        backup_file="$BACKUP_PATH/$(basename "$target_file")"
        cp "$target_file" "$backup_file"
    fi
    
    # Apply decision based on action type
    case "$action" in
        "modify")
            if [ -n "$DRY_RUN" ]; then
                echo "  [DRY RUN] Would modify: $target_file"
            else
                # Apply modifications
                content=$(cat "$target_file")
                changes=$(echo "$decision" | jq -c '.changes[]')
                echo "$changes" | while IFS= read -r change; do
                    pattern=$(echo "$change" | jq -r '.pattern')
                    replacement=$(echo "$change" | jq -r '.replacement')
                    content=$(echo "$content" | sed "s|$pattern|$replacement|g")
                done
                echo "$content" > "$target_file"
            fi
            ;;
            
        "create")
            new_file=$(echo "$decision" | jq -r '.new_file')
            if [ -n "$DRY_RUN" ]; then
                echo "  [DRY RUN] Would create: $new_file"
            else
                # Create new file
                new_dir=$(dirname "$new_file")
                mkdir -p "$new_dir"
                echo "$decision" | jq -r '.content' > "$new_file"
            fi
            ;;
            
        "delete")
            if [ -n "$DRY_RUN" ]; then
                echo "  [DRY RUN] Would delete: $target_file"
            else
                rm "$target_file"
            fi
            ;;
            
        *)
            error_msg="Unknown action: $action"
            echo "  ✗ Error: $error_msg"
            
            # Add to errors
            jq --arg file "$target_file" --arg action "$action" --arg error "$error_msg" --arg time "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
               '.errors += [{"file": $file, "action": $action, "error": $error, "timestamp": $time}]' \
               "$RESULTS_FILE" > "${RESULTS_FILE}.tmp" && mv "${RESULTS_FILE}.tmp" "$RESULTS_FILE"
            continue
            ;;
    esac
    
    # Record successful processing
    jq --arg file "$target_file" --arg action "$action" --arg time "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
       '.processed += [{"file": $file, "action": $action, "status": "success", "timestamp": $time}]' \
       "$RESULTS_FILE" > "${RESULTS_FILE}.tmp" && mv "${RESULTS_FILE}.tmp" "$RESULTS_FILE"
    
    echo "  ✓ Processed successfully"
done

# Finalize results
END_TIME=$(date -u +%Y-%m-%dT%H:%M:%SZ)
processed_count=$(jq '.processed | length' "$RESULTS_FILE")
error_count=$(jq '.errors | length' "$RESULTS_FILE")

jq --arg end_time "$END_TIME" --arg processed "$processed_count" --arg errors "$error_count" \
   '.metadata.end_time = $end_time | .metadata.total_processed = ($processed | tonumber) | .metadata.total_errors = ($errors | tonumber)' \
   "$RESULTS_FILE" > "${RESULTS_FILE}.tmp" && mv "${RESULTS_FILE}.tmp" "$RESULTS_FILE"

echo "Processing complete!"
echo "Processed: $processed_count files"
echo "Errors: $error_count"
echo "Results saved to: $RESULTS_FILE"

# Return success
exit 0
