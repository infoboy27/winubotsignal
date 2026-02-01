#!/bin/bash

# Payment Activation Monitor Wrapper Script
# This script loads environment variables and runs the monitor

cd "$(dirname "$0")"

# Load environment variables from production.env
if [ -f production.env ]; then
    export $(grep -v '^#' production.env | xargs)
fi

# Show usage if needed
if [ "$1" == "--help" ] || [ "$1" == "-h" ]; then
    python3 monitor_payment_activation.py check
    exit 0
fi

# Run the monitor with provided arguments or default to continuous monitoring
if [ -z "$1" ]; then
    echo "🔍 Starting continuous payment activation monitor..."
    echo "Press Ctrl+C to stop"
    echo ""
    python3 monitor_payment_activation.py watch
else
    python3 monitor_payment_activation.py "$@"
fi



