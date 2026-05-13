/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        PrimaryBlue: 'rgb(var(--PrimaryBlue) / <alpha-value>)',
      },
      fontFamily: {
        hind: ['Hind', 'sans-serif'],
      },
    },
  },
  plugins: [],
};
