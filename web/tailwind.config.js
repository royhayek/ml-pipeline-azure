/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', 'system-ui', 'sans-serif'],
        mono: ['"Fira Code"', 'monospace'],
      },
      colors: {
        surface: {
          DEFAULT: '#111115',
          raised: '#18181e',
          overlay: '#1e1e26',
        },
        border: {
          DEFAULT: 'rgba(255,255,255,0.07)',
          strong: 'rgba(255,255,255,0.12)',
        },
        brand: {
          DEFAULT: '#a78bfa',
          dim:     'rgba(167,139,250,0.12)',
        },
        teal: {
          glow: '#2dd4bf',
          dim:  'rgba(45,212,191,0.12)',
        },
      },
      animation: {
        'fade-up':  'fadeUp 0.4s cubic-bezier(0.22,1,0.36,1) both',
        'pulse-dot':'pulseDot 2s ease-in-out infinite',
      },
      keyframes: {
        fadeUp: {
          from: { opacity: 0, transform: 'translateY(10px)' },
          to:   { opacity: 1, transform: 'translateY(0)' },
        },
        pulseDot: {
          '0%,100%': { opacity: 1 },
          '50%':     { opacity: 0.3 },
        },
      },
    },
  },
  plugins: [],
}
