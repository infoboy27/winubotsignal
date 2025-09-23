/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {
    serverActions: {
      allowedOrigins: ['localhost:3003', 'localhost:3000']
    }
  },
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  },
  async rewrites() {
    // For server-side rewrites, use the internal Docker service name
    const apiUrl = process.env.API_URL_INTERNAL || 'http://api:8001'
    console.log('API URL for rewrites:', apiUrl)
    return [
      {
        source: '/api/:path*',
        destination: `${apiUrl}/:path*`,
      },
    ]
  },
}

module.exports = nextConfig



