import type { NextConfig } from "next";

/** Admin must stay a dynamic server app — never `output: "export"`. */
const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/images/:path*",
        destination: "/api/media/images/:path*",
      },
    ];
  },
};

export default nextConfig;
