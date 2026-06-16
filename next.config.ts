import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  /* config options here */
  typescript: {
    ignoreBuildErrors: true,
  },
  reactStrictMode: false,
  // Use port 3001 to avoid conflict with WSL relay on port 3000
  // WSL relay (wslrelay.exe) occupies port 3000 for WSL2 networking
  serverRuntimeConfig: {
    port: 3001,
  },
};

export default nextConfig;
