import type { Config } from "tailwindcss";

// Tokens de la familia AI.Q (design system PowerAI v2). Ver docs/design-system.md.
// El morado es marca e interacción; los semánticos (verde/ámbar/rojo) son solo
// estado y nunca decoran.
const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          900: "#352C78",
          800: "#453A96",
          600: "#5B51C8",
          200: "#C9C5EC",
          100: "#EFEDFB",
          50: "#F6F5FD",
          DEFAULT: "#5B51C8",
        },
        cream: {
          100: "#FBF2E7",
        },
        surface: {
          200: "#ECEDF4",
          100: "#F4F5FA",
        },
        neutral: {
          900: "#2A2A3C",
          700: "#3A3A50",
          500: "#6B6B80",
          400: "#8A8AA0",
          200: "#DDDFE9",
          100: "#E2E4EE",
        },
        success: {
          700: "#27500A",
          600: "#3B6D11",
        },
        warning: {
          700: "#633806",
          600: "#854F0B",
        },
        danger: {
          700: "#791F1F",
          600: "#A32D2D",
        },
      },
      borderRadius: {
        pill: "99px",
      },
    },
  },
  plugins: [],
};

export default config;
