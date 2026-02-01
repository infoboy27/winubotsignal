import { NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'
export const revalidate = 0

export async function GET() {
  return NextResponse.json({ 
    message: 'Test API route working!', 
    timestamp: new Date().toISOString() 
  })
}

