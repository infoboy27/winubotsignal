import { NextRequest, NextResponse } from 'next/server';

export async function GET(request: NextRequest) {
  try {
    // Get backend API URL from environment or default
    const apiUrl = process.env.API_URL_INTERNAL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001';
    
    // Forward the request to the backend API - use onboarding/plans endpoint
    const response = await fetch(`${apiUrl}/onboarding/plans`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });
    
    const data = await response.json();
    
    // Transform the plans to match frontend expectations
    const transformedPlans = (data.plans || []).map((plan: any) => ({
      id: plan.id,
      name: plan.name,
      price_usd: plan.price || 0,
      price_usdt: plan.price || 0,
      interval: plan.duration || plan.interval || 'monthly',
      duration_days: plan.id === 'free_trial' ? 7 : 30,
      dashboard_access_limit: plan.id === 'free_trial' ? 1 : -1,
      features: plan.features || [],
      telegram_access: plan.id !== 'free_trial',
      support_level: plan.id === 'free_trial' ? 'none' : plan.id === 'professional' ? 'priority' : '24/7',
      binance_pay_id: plan.id === 'professional' ? '287402909' : plan.id === 'vip_elite' ? '287402910' : undefined
    }));
    
    // Return the transformed plans array
    return NextResponse.json(transformedPlans, { status: response.status });
  } catch (error) {
    console.error('Subscription plans proxy error:', error);
    return NextResponse.json(
      { error: 'Failed to connect to backend API' },
      { status: 500 }
    );
  }
}

