import { NextRequest, NextResponse } from 'next/server';

const MCP_SERVER_URL = process.env.MCP_SERVER_URL || 
  (process.env.NEXT_PUBLIC_MCP_API_URL || 'http://mcp-server:8003').replace('https://mcp-api.winu.app', 'http://mcp-server:8003').replace('http://localhost:8003', 'http://mcp-server:8003');

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    
    const response = await fetch(`${MCP_SERVER_URL}/api/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      const errorText = await response.text();
      return NextResponse.json(
        { error: `MCP Server error: ${response.status} - ${errorText}` },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error: any) {
    return NextResponse.json(
      { error: error.message },
      { status: 500 }
    );
  }
}

