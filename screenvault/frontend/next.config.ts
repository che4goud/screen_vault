import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  outputFileTracingRoot: "/Users/prathvi/Documents/ss_desc/screenvault",
  images: {
    remotePatterns: [
      {
        protocol: "http",
        hostname: "localhost",
        port: "8000",
        pathname: "/thumbnails/**",
      },
    ],
  },
};

export default nextConfig;
