/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Provide sane defaults so the client bundle always bakes in reachable endpoints
  // even if build-time env vars are missing in CI.
  env: {
    NEXT_PUBLIC_PIPELINE_URL:
      process.env.NEXT_PUBLIC_PIPELINE_URL || 'http://34.173.90.220:8001',
    NEXT_PUBLIC_CALENDAR_AGENT_URL:
      process.env.NEXT_PUBLIC_CALENDAR_AGENT_URL || 'http://34.170.150.39:8004',
    NEXT_PUBLIC_RAG_URL: process.env.NEXT_PUBLIC_RAG_URL || 'http://34.63.130.184:8002',
  },
}

module.exports = nextConfig
