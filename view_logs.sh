#!/bin/bash
# Quick Log Viewer Script for Winu Bot

echo "=================================================="
echo "  WINU BOT - LOG VIEWER"
echo "=================================================="
echo ""
echo "Available log commands:"
echo ""
echo "1. REAL-TIME LOGS (follow live activity):"
echo "   docker logs winu-bot-signal-trading-bot -f"
echo ""
echo "2. LAST 50 LINES:"
echo "   docker logs winu-bot-signal-trading-bot --tail 50"
echo ""
echo "3. LAST 100 LINES:"
echo "   docker logs winu-bot-signal-trading-bot --tail 100"
echo ""
echo "4. LAST 1 HOUR:"
echo "   docker logs winu-bot-signal-trading-bot --since 1h"
echo ""
echo "5. SEARCH FOR SPECIFIC TERMS:"
echo "   docker logs winu-bot-signal-trading-bot 2>&1 | grep 'search_term'"
echo ""
echo "=================================================="
echo ""
echo "Choose an option (1-5) or press Ctrl+C to exit:"
read -p "Enter choice: " choice

case $choice in
    1)
        echo "Showing live logs (press Ctrl+C to stop)..."
        docker logs winu-bot-signal-trading-bot -f
        ;;
    2)
        echo "Last 50 lines:"
        docker logs winu-bot-signal-trading-bot --tail 50
        ;;
    3)
        echo "Last 100 lines:"
        docker logs winu-bot-signal-trading-bot --tail 100
        ;;
    4)
        echo "Last hour:"
        docker logs winu-bot-signal-trading-bot --since 1h
        ;;
    5)
        read -p "Enter search term: " term
        echo "Searching for '$term'..."
        docker logs winu-bot-signal-trading-bot 2>&1 | grep "$term"
        ;;
    *)
        echo "Invalid choice"
        ;;
esac




