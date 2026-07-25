import type { NextConfig } from "next";
import path from "path";

const nextConfig: NextConfig = {
  // Parent dirs have other lockfiles; pin tracing root to this app.
  outputFileTracingRoot: path.join(__dirname),
};

export default nextConfig;
