import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    
    // Get backend API URL from environment or default
    const apiUrl = process.env.API_URL_INTERNAL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';
    
    // Build query parameters from the request body
    const queryParams = new URLSearchParams({
      plan_id: body.plan_id,
      payment_method: body.payment_method || 'nowpayments',
      pay_currency: body.pay_currency || 'usdc'
    });
    
    // Forward the request to the backend API with query parameters
    const response = await fetch(`${apiUrl}/api/crypto-subscriptions/create-payment?${queryParams}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        // Forward authorization header if present
        ...(request.headers.get('authorization') && {
          'Authorization': request.headers.get('authorization')!
        })
      }
    });
    
    const data = await response.json();
    
    // Return the response from backend
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error('Create payment proxy error:', error);
    return NextResponse.json(
      { error: 'Failed to connect to backend API' },
      { status: 500 }
    );
  }
}
