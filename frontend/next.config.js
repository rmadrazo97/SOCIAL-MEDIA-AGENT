/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  async rewrites() {
    const backendUrl = process.env.BACKEND_URL || 'http://backend:8000';
    return {
      // fallback rewrites only apply when no filesystem route (API route) matches
      fallback: [
        {
          source: '/api/:path*',
          destination: `${backendUrl}/api/:path*`,
        },
        {
          source: '/copilotkit',
          destination: `${backendUrl}/copilotkit/`,
        },
        {
          source: '/copilotkit/:path*',
          destination: `${backendUrl}/copilotkit/:path*`,
        },
      ],
    };
  },
}

module.exports = nextConfig
