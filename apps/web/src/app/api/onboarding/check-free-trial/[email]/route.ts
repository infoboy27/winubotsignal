import { NextRequest, NextResponse } from 'next/server';

export async function GET(
  request: NextRequest,
  { params }: { params: { email: string } }
) {
  try {
    const { email } = params;
    
    // Get backend API URL from environment or default
    const apiUrl = process.env.API_URL_INTERNAL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';
    
    // Forward the request to the backend API
    const response = await fetch(`${apiUrl}/onboarding/check-free-trial/${encodeURIComponent(email)}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });
    
    const data = await response.json();
    
    // Return the response from backend
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error('Check free trial proxy error:', error);
    return NextResponse.json(
      { error: 'Failed to connect to backend API' },
      { status: 500 }
    );
  }
}










