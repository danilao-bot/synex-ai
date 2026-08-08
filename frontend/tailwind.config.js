/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        background: '#060913',
        surface: '#0D1527',
        surfaceBorder: '#1E293B',
        primary: '#6366F1', // Indigo primary action
        primaryHover: '#4F46E5', // Darker indigo for hover
        accent: '#00E5FF', // Cyan informational accent
        accentGlow: 'rgba(0, 229, 255, 0.15)',
        success: '#05F29B',
        warning: '#FF9F00',
        danger: '#EF4444'
      },
      fontFamily: {
        sans: ['var(--font-inter)', 'sans-serif'],
        display: ['var(--font-outfit)', 'sans-serif'],
        mono: ['var(--font-mono)', 'monospace'],
      },
      keyframes: {
        'fade-in-up': {
          '0%': { opacity: 0, transform: 'translateY(15px)' },
          '100%': { opacity: 1, transform: 'translateY(0)' },
        }
      },
      animation: {
        'fade-in-up': 'fade-in-up 0.5s ease-out forwards',
      }
    },
  },
  plugins: [],
}
