/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    // 开发模式：把 /api/v1/* 转到本地 FastAPI :8000
    // 生产模式（如 Vercel）：不 rewrite — lib/api.ts 的 try/catch 会回退到 fallback 数据
    if (process.env.NODE_ENV !== "production") {
      return [
        {
          source: "/api/v1/:path*",
          destination: "http://localhost:8000/api/v1/:path*",
        },
      ];
    }
    return [];
  },
};
export default nextConfig;
