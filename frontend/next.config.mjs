import { dirname } from "node:path";
import { fileURLToPath } from "node:url";

const root = dirname(fileURLToPath(import.meta.url));

/** @type {import('next').NextConfig} */
const nextConfig = {
  turbopack: {
    root
  },
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "server.arcgisonline.com"
      },
      {
        protocol: "https",
        hostname: "lh3.googleusercontent.com"
      }
    ]
  }
};

export default nextConfig;
