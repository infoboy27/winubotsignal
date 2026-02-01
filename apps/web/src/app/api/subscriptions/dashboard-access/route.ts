import { NextRequest, NextResponse } from 'next/server';

export async function GET(request: NextRequest) {
  try {
    // Get the authorization header
    const authHeader = request.headers.get('authorization');
    
    if (!authHeader) {
      return NextResponse.json(
        { error: 'Not authenticated' },
        { status: 401 }
      );
    }
    
    // Get backend API URL from environment or default
    const apiUrl = process.env.API_URL_INTERNAL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';
    
    // Forward the request to the backend API with authentication
    const response = await fetch(`${apiUrl}/api/subscriptions/dashboard-access`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': authHeader,
      },
    });
    
    // Handle response
    let data;
    const responseText = await response.text();
    
    try {
      data = responseText ? JSON.parse(responseText) : { error: 'Empty response' };
    } catch (e) {
      console.error('Failed to parse backend response:', responseText);
      return NextResponse.json(
        { error: 'Invalid response from backend', details: responseText },
        { status: 500 }
      );
    }
    
    // Return the response from backend
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error('Dashboard access proxy error:', error);
    return NextResponse.json(
      { error: 'Failed to connect to backend API', details: String(error) },
      { status: 500 }
    );
  }
}











