/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/**/*.{js,jsx}", "./components/**/*.{js,jsx}", "./lib/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#0F2E33",
        pine: { DEFAULT: "#0D4F59", light: "#146573" },
        leaf: "#2A8585",
        mist: "#E5EFEE",
        paper: "#F5F8F7",
        slip: "#FFFCF3",
        marigold: "#F0A81C",
        alert: "#B3261E",
      },
      fontFamily: {
        display: ['"Bricolage Grotesque Variable"', "system-ui", "sans-serif"],
        sans: ['"Figtree Variable"', "system-ui", "-apple-system", '"Segoe UI"', "Roboto", "sans-serif"],
      },
    },
  },
  plugins: [],
};