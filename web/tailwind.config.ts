import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Paleta base provisional de PowerAI.
        brand: {
          DEFAULT: "#1f4e79",
          dark: "#163a5a",
        },
      },
    },
  },
  plugins: [],
};

export default config;
