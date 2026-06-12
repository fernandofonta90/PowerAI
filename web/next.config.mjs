/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // La URL de la API se inyecta por entorno (ver .env.example).
  env: {
    POWERAI_API_URL: process.env.POWERAI_API_URL ?? "http://localhost:8000",
  },
};

export default nextConfig;
