import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  ...(process.env.NETLIFY ? {} : { output: "standalone" }),
  typescript: {
    ignoreBuildErrors: true,
  },
  reactStrictMode: false,
  turbopack: {
    root: process.cwd(),
  },
};

export default nextConfig;
