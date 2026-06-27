import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  /* config options here */
  typescript: {
    ignoreBuildErrors: true,
  },
  reactStrictMode: false,
  // Dashboard served on 3001 via `npx next dev -p 3001` / PORT env.
  // (serverRuntimeConfig removed in Next 16 — that key triggered an
  //  "Unrecognized key" warning on boot.)
};

export default nextConfig;
