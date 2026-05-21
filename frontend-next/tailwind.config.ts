import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    container: { center: true, padding: "1.5rem", screens: { "2xl": "1320px" } },
    extend: {
      colors: {
        // ShadowBlade 调色（深蓝 / 石墨 / 灰白 / 青绿）
        navy: {
          50: "#eef3fb",
          100: "#d6e0f3",
          200: "#a8bee1",
          300: "#7799cd",
          400: "#4c79b6",
          500: "#2c528f",
          600: "#1f3a72",
          700: "#142a55",
          800: "#0f1d3a",
          900: "#0a1428",
          950: "#060c1a",
        },
        graphite: {
          50: "#eef0f4",
          100: "#d8dde5",
          200: "#b6bdcc",
          300: "#8590a8",
          400: "#5a667f",
          500: "#3a455c",
          600: "#2a3447",
          700: "#1d2535",
          800: "#161c28",
          900: "#11161f",
          950: "#0c1118",
        },
        accent: {
          50: "#e6fbf6",
          100: "#c5f4e8",
          300: "#6ee2c5",
          400: "#2ee2c4",
          500: "#22d3b7",
          600: "#14b59a",
          700: "#0d8f7a",
          900: "#064f44",
        },
        // 语义颜色（shadcn/ui 习惯用法，绑到 CSS 变量）
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        card: { DEFAULT: "hsl(var(--card))", foreground: "hsl(var(--card-foreground))" },
        popover: { DEFAULT: "hsl(var(--popover))", foreground: "hsl(var(--popover-foreground))" },
        primary: { DEFAULT: "hsl(var(--primary))", foreground: "hsl(var(--primary-foreground))" },
        secondary: { DEFAULT: "hsl(var(--secondary))", foreground: "hsl(var(--secondary-foreground))" },
        muted: { DEFAULT: "hsl(var(--muted))", foreground: "hsl(var(--muted-foreground))" },
        accent2: { DEFAULT: "hsl(var(--accent))", foreground: "hsl(var(--accent-foreground))" },
        destructive: { DEFAULT: "hsl(var(--destructive))", foreground: "hsl(var(--destructive-foreground))" },
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      fontFamily: {
        display: ["var(--font-display)", "system-ui", "sans-serif"],
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
      },
      keyframes: {
        "accordion-down": { from: { height: "0" }, to: { height: "var(--radix-accordion-content-height)" } },
        "accordion-up": { from: { height: "var(--radix-accordion-content-height)" }, to: { height: "0" } },
        shimmer: { "100%": { transform: "translateX(100%)" } },
      },
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",
        shimmer: "shimmer 2s infinite",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};

export default config;
