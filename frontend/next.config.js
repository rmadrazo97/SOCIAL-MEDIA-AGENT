/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  async rewrites() {
    const backendUrl = process.env.BACKEND_URL || 'http://backend:8000';
    return [
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
    ];
  },
}

module.exports = nextConfig
