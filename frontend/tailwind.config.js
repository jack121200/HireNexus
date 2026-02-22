/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#07090f",
        panel: "#0d111b",
        panelMuted: "#121827",
        border: "#1f2636",
        accent: "#7c5cff",
        accentSoft: "#9b7bff",
        accentWarm: "#ff7aa8",
        accentCool: "#2fe1ff",
        accentLime: "#7dffb3",
        text: "#e6e9f2",
        textMuted: "#9aa4b5",
        success: "#3be97d",
        danger: "#ff5c7c",
        warning: "#ffc44d",
        info: "#5bb8ff",
      },
      boxShadow: {
        glow: "0 20px 60px rgba(124, 92, 255, 0.25)",
        glowSoft: "0 10px 40px rgba(47, 225, 255, 0.18)",
        neon: "0 0 30px rgba(255, 122, 168, 0.3)",
      },
      fontFamily: {
        display: ["Space Grotesk", "system-ui", "sans-serif"],
        body: ["Plus Jakarta Sans", "system-ui", "sans-serif"],
      },
      backgroundImage: {
        aurora:
          "radial-gradient(1200px 600px at 10% -10%, rgba(124,92,255,0.35), transparent 60%), radial-gradient(1000px 500px at 90% 0%, rgba(47,225,255,0.25), transparent 60%), radial-gradient(900px 500px at 50% 100%, rgba(255,122,168,0.2), transparent 70%), linear-gradient(180deg, #06080f 0%, #070a14 35%, #05070d 100%)",
        mesh:
          "radial-gradient(circle at 20% 20%, rgba(124,92,255,0.2), transparent 40%), radial-gradient(circle at 80% 0%, rgba(47,225,255,0.18), transparent 42%), radial-gradient(circle at 50% 80%, rgba(255,122,168,0.16), transparent 45%)",
      },
      keyframes: {
        float: {
          "0%, 100%": { transform: "translateY(0px)" },
          "50%": { transform: "translateY(-6px)" },
        },
        pulseSoft: {
          "0%, 100%": { opacity: 0.6 },
          "50%": { opacity: 1 },
        },
        gradientShift: {
          "0%, 100%": { backgroundPosition: "0% 50%" },
          "50%": { backgroundPosition: "100% 50%" },
        },
      },
      animation: {
        float: "float 6s ease-in-out infinite",
        pulseSoft: "pulseSoft 5s ease-in-out infinite",
        gradientShift: "gradientShift 10s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};
