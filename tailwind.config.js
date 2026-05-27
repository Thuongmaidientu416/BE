export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "Poppins", "ui-sans-serif", "system-ui", "sans-serif"],
      },
      colors: {
        ink: "#fdf8f3",
        panel: "rgba(45,90,61,0.07)",
        cyan: "#2d5a3d",
        violet: "#2d5a3d",
        ember: "#c96420",
      },
      boxShadow: {
        glow: "0 0 45px rgba(45, 90, 61, 0.22)",
        violet: "0 0 60px rgba(45, 90, 61, 0.22)",
      },
    },
  },
  plugins: [],
};
