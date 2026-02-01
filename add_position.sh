#!/bin/bash
# Quick script to add a position to the dashboard
# Usage: ./add_position.sh SYMBOL SIDE ENTRY_PRICE QUANTITY

SYMBOL=$1
SIDE=$2
ENTRY_PRICE=$3
QUANTITY=$4

if [ -z "$SYMBOL" ] || [ -z "$SIDE" ] || [ -z "$ENTRY_PRICE" ] || [ -z "$QUANTITY" ]; then
    echo "Usage: ./add_position.sh SYMBOL SIDE ENTRY_PRICE QUANTITY"
    echo "Example: ./add_position.sh BTC/USDT LONG 43000 0.1"
    exit 1
fi

docker compose exec postgres psql -U winu -d winudb << SQL
INSERT INTO paper_positions (
    symbol, side, entry_price, quantity, current_price,
    unrealized_pnl, stop_loss, take_profit, market_type,
    is_open, created_at, updated_at
) VALUES (
    '$SYMBOL', '$SIDE', $ENTRY_PRICE, $QUANTITY, $ENTRY_PRICE,
    0, NULL, NULL, 'futures',
    true, NOW(), NOW()
);

SELECT id, symbol, side, entry_price, quantity 
FROM paper_positions 
WHERE symbol = '$SYMBOL' AND is_open = true;
SQL

echo ""
echo "✅ Position added! Check bot.winu.app dashboard"
