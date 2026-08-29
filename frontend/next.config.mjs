/** @type {import('next').NextConfig} */
const backendOrigin = (process.env.BACKEND_ORIGIN ?? "http://127.0.0.1:8000").replace(/\/$/, "");

const nextConfig = {
  async rewrites() {
    return [
      // Temporary compatibility for sessions created by the original UI.
      {
        source: "/api/agents",
        destination: `${backendOrigin}/api/v1/agents`,
      },
      {
        source: "/api/agent/chat",
        destination: `${backendOrigin}/api/v1/chat`,
      },
      {
        source: "/api/:path*",
        destination: `${backendOrigin}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
