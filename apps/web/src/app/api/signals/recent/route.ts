import { NextRequest, NextResponse } from 'next/server';

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const limit = searchParams.get('limit') || '20';
    const symbol = searchParams.get('symbol');
    const timeframe = searchParams.get('timeframe');
    const direction = searchParams.get('direction');
    const min_score = searchParams.get('min_score');
    const offset = searchParams.get('offset') || '0';

    const apiUrl = process.env.API_URL_INTERNAL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';
    
    // Build query parameters
    const queryParams = new URLSearchParams({
      limit,
      offset
    });
    
    if (symbol) queryParams.append('symbol', symbol);
    if (timeframe) queryParams.append('timeframe', timeframe);
    if (direction) queryParams.append('direction', direction);
    if (min_score) queryParams.append('min_score', min_score);

    const response = await fetch(`${apiUrl}/signals/recent?${queryParams.toString()}`);
    const data = await response.json();
    
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error('Signals recent proxy error:', error);
    return NextResponse.json(
      { error: 'Failed to connect to backend API' },
      { status: 500 }
    );
  }
}