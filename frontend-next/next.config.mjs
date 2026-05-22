/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    // BACKEND_URL is the FastAPI base — set this on Vercel to your Railway/
    // Render/Fly URL (e.g. https://shadowblade-backend.up.railway.app).
    // Server-side env, not exposed to the client. Falls back to localhost
    // for `next dev`.
    const backend =
      process.env.BACKEND_URL ||
      process.env.NEXT_PUBLIC_API_BASE?.replace(/\/api\/v1\/?$/, "") ||
      (process.env.NODE_ENV === "production" ? null : "http://localhost:8000");

    if (!backend) {
      // No backend wired in production → /api/v1/* falls to lib/api.ts's
      // try/catch fallback (fixture data). Studio's "立即生成" will fail
      // gracefully with an error message.
      return [];
    }

    return [
      { source: "/api/v1/:path*", destination: `${backend}/api/v1/:path*` },
      // Backend StaticFiles mount — serves generated MP4 + cover.
      { source: "/static/:path*", destination: `${backend}/static/:path*` },
    ];
  },
};
export default nextConfig;
