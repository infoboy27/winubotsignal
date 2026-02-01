import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

export function middleware(request: NextRequest) {
  const hostname = request.headers.get('host') || ''
  
  // Check if it's the main domain (www.winu.app or winu.app)
  const isMainDomain = hostname === 'www.winu.app' || hostname === 'winu.app'
  
  // Check if it's the dashboard subdomain
  const isDashboardDomain = hostname === 'dashboard.winu.app'
  
  // Create response
  const response = NextResponse.next()
  
  // If it's the main domain, serve the landing page
  if (isMainDomain) {
    // Allow all paths on main domain - let client-side routing handle it
    return response
  }
  
  // If it's the dashboard domain, serve the dashboard
  if (isDashboardDomain) {
    // Allow all paths on dashboard domain - let client-side routing handle it
    return response
  }
  
  return response
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - api (API routes)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     */
    '/((?!api|_next/static|_next/image|favicon.ico).*)',
  ],
}
