import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  try {
    // Get the authorization header
    const authHeader = request.headers.get('authorization');
    
    if (!authHeader) {
      return NextResponse.json(
        { error: 'Not authenticated' },
        { status: 401 }
      );
    }
    
    // Get request body - handle empty body or invalid JSON
    let body = {};
    try {
      // Clone the request to avoid consumption issues
      const clonedRequest = request.clone();
      const text = await clonedRequest.text();
      
      // Only parse if there's actual content
      if (text && text.trim().length > 0) {
        body = JSON.parse(text);
      }
    } catch (e) {
      // Empty body is OK for trial start
      console.log('Trial start with empty or invalid body, using empty object');
      body = {};
    }
    
    // Get backend API URL from environment or default
    const apiUrl = process.env.API_URL_INTERNAL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';
    
    // Forward the request to the backend API with authentication
    const response = await fetch(`${apiUrl}/api/subscriptions/trial/start`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': authHeader,
      },
      body: JSON.stringify(body),
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
    console.error('Start trial proxy error:', error);
    return NextResponse.json(
      { error: 'Failed to connect to backend API', details: String(error) },
      { status: 500 }
    );
  }
}
