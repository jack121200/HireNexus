/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        /* ── Midnight Prism: Vercel + Linear inspired ── */
        ink: "#0a0a0a",
        panel: "#141414",
        panelMuted: "#1a1a1a",
        panelHover: "#1f1f1f",
        border: "#262626",
        borderHover: "#404040",
        borderFocus: "#525252",
        accent: "#0070f3",       /* Vercel blue */
        accentSoft: "#3291ff",
        accentWarm: "#f472b6",   /* Pink accent */
        accentCool: "#22d3ee",   /* Cyan accent */
        accentLime: "#4ade80",   /* Green accent */
        accentPurple: "#7c5cff", /* Purple accent */
        text: "#ededed",
        textMuted: "#888888",
        textDim: "#666666",
        success: "#00d68f",
        danger: "#ef4444",
        warning: "#f59e0b",
        info: "#3b82f6",
      },
      boxShadow: {
        glow: "0 0 20px rgba(0,112,243,0.15)",
        glowLg: "0 8px 40px rgba(0,112,243,0.2)",
        card: "0 1px 3px rgba(0,0,0,0.3), 0 1px 2px rgba(0,0,0,0.4)",
        cardHover: "0 4px 20px rgba(0,0,0,0.4), 0 0 0 1px rgba(64,64,64,0.5)",
        ring: "0 0 0 2px rgba(0,112,243,0.4)",
      },
      fontFamily: {
        display: ["Inter", "Space Grotesk", "system-ui", "sans-serif"],
        body: ["Inter", "Plus Jakarta Sans", "system-ui", "sans-serif"],
      },
      backgroundImage: {
        /* Subtle gradients for hero sections */
        aurora: "radial-gradient(ellipse 80% 50% at 50% -20%, rgba(0,112,243,0.15), transparent), linear-gradient(180deg, #0a0a0a 0%, #0a0a0a 100%)",
        mesh: "radial-gradient(circle at 20% 30%, rgba(0,112,243,0.08), transparent 40%), radial-gradient(circle at 80% 20%, rgba(124,92,255,0.06), transparent 40%)",
        /* Glass panel gradient */
        glass: "linear-gradient(135deg, rgba(20,20,20,0.8), rgba(26,26,26,0.6))",
      },
      borderRadius: {
        "2xl": "1rem",
        "3xl": "1.25rem",
      },
      keyframes: {
        float: {
          "0%, 100%": { transform: "translateY(0px)" },
          "50%": { transform: "translateY(-4px)" },
        },
        fadeIn: {
          "0%": { opacity: "0", transform: "translateY(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        fadeInUp: {
          "0%": { opacity: "0", transform: "translateY(16px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        slideIn: {
          "0%": { opacity: "0", transform: "translateX(-8px)" },
          "100%": { opacity: "1", transform: "translateX(0)" },
        },
        scaleIn: {
          "0%": { opacity: "0", transform: "scale(0.95)" },
          "100%": { opacity: "1", transform: "scale(1)" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
        pulseSoft: {
          "0%, 100%": { opacity: "0.6" },
          "50%": { opacity: "1" },
        },
        gradientShift: {
          "0%, 100%": { backgroundPosition: "0% 50%" },
          "50%": { backgroundPosition: "100% 50%" },
        },
      },
      animation: {
        float: "float 5s ease-in-out infinite",
        fadeIn: "fadeIn 0.4s ease-out",
        fadeInUp: "fadeInUp 0.5s ease-out",
        slideIn: "slideIn 0.3s ease-out",
        scaleIn: "scaleIn 0.3s ease-out",
        shimmer: "shimmer 2s linear infinite",
        pulseSoft: "pulseSoft 4s ease-in-out infinite",
        gradientShift: "gradientShift 8s ease-in-out infinite",
      },
      transitionDuration: {
        DEFAULT: "150ms",
      },
    },
  },
  plugins: [],
};
