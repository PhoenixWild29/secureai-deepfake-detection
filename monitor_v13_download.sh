#!/bin/bash
# Monitor V13 download progress

echo "Monitoring V13 download..."
echo "Press Ctrl+C to stop"
echo ""

# Check cache directories
CACHE_DIRS=(
    "/root/.cache/huggingface"
    "/home/app/.cache/huggingface"
    "$HOME/.cache/huggingface"
)

for dir in "${CACHE_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        echo "Checking: $dir"
        find "$dir" -name "*.safetensors" -exec ls -lh {} \; 2>/dev/null | while read line; do
            echo "  $line"
        done
    fi
done

echo ""
echo "Watching for new files (refresh every 5 seconds)..."
echo ""

while true; do
    for dir in "${CACHE_DIRS[@]}"; do
        if [ -d "$dir" ]; then
            find "$dir" -name "*model_*.safetensors" -exec ls -lh {} \; 2>/dev/null | while read line; do
                echo "$(date '+%H:%M:%S') - $line"
            done
        fi
    done
    echo "---"
    sleep 5
done
