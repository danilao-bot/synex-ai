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
        background: '#0B0F17',
        surface: '#151C2C',
        surfaceBorder: '#232D42',
        accent: '#3B82F6',
        accentGlow: 'rgba(59, 130, 246, 0.15)',
        success: '#10B981',
        warning: '#F59E0B',
        danger: '#EF4444'
      }
    },
  },
  plugins: [],
}
