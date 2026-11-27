/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          50: "#f6f7f9",
          100: "#eceef2",
          200: "#d4d8e0",
          300: "#a9b0bf",
          400: "#6c7585",
          500: "#4a5362",
          600: "#343c49",
          700: "#232934",
          800: "#161b22",
          900: "#0d1117",
        },
      },
    },
  },
  plugins: [],
};
