/** @type {import('next').NextConfig} */
const nextConfig = {
  // Produce a standalone server bundle for a slim Docker image.
  output: "standalone",
};

export default nextConfig;
