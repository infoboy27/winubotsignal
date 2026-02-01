import { NextRequest, NextResponse } from 'next/server';

export async function GET(request: NextRequest) {
  try {
    // Get bot dashboard URL from environment or default (port 8000, not 8501!)
    const botDashboardUrl = process.env.BOT_DASHBOARD_URL || 'http://winu-bot-signal-bot-dashboard:8000';
    
    // Fetch trading performance from bot dashboard API
    const response = await fetch(`${botDashboardUrl}/api/public-status`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });
    
    if (!response.ok) {
      console.error('Bot API error:', response.status, response.statusText);
      return NextResponse.json(
        { error: 'Failed to fetch trading performance', win_rate: 0, total_pnl: 0 },
        { status: response.status }
      );
    }
    
    const data = await response.json();
    
    // Return the trading performance data
    return NextResponse.json({
      win_rate: data.win_rate || 0,
      total_pnl: data.total_pnl || 0,
      total_trades: data.total_trades || 0,
      latest_trade: data.latest_trade || null
    });
  } catch (error) {
    console.error('Trading performance proxy error:', error);
    return NextResponse.json(
      { error: 'Failed to connect to bot API', win_rate: 0, total_pnl: 0 },
      { status: 500 }
    );
  }
}

