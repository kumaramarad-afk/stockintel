/** @type {import('next').NextConfig} */
const backendOrigin = (process.env.INTERNAL_API_URL || "http://localhost:8000")
  .replace(/\/+$/, "")
  .replace(/\/api$/i, "");

const nextConfig = {
  output: "standalone",
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${backendOrigin}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
