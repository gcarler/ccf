import type { Config } from "tailwindcss";

const config: Config = {
    darkMode: "class",
    content: [
        "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
        "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
        "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
    ],
    theme: {
        extend: {
            colors: {
                "primary": "#1973f0",
                "navy-dark": "#0A192F",
                "sky-blue": "#00B4DB",
                "background-light": "#f6f7f8",
                "background-dark": "#050A10",
                glass: "rgba(255, 255, 255, 0.1)",
                "glass-border": "rgba(255, 255, 255, 0.2)",
            },
            fontFamily: {
                "display": ["Manrope", "sans-serif"],
                "sans": ["Manrope", "sans-serif"]
            },
            borderRadius: {
                "DEFAULT": "0.25rem",
                "lg": "0.5rem",
                "xl": "1rem",
                "2xl": "1.5rem",
                "3xl": "2rem",
                "4xl": "2.5rem",
                "full": "9999px"
            },
            backdropBlur: {
                xs: "2px",
            },
        },
    },
    plugins: [],
};
export default config;
