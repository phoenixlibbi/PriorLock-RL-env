import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "export",   // static export — works with Vercel too (Vercel auto-detects Next.js and ignores this)
};

export default nextConfig;
