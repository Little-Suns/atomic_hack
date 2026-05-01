/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'rosatom-blue': '#005BAA',
        'rosatom-dark-blue': '#003C6E',
        'rosatom-light-blue': '#E6F2FF',
        'rosatom-gray': '#F5F5F5',
        'rosatom-text': '#333333',
      },
      fontFamily: {
        'sans': ['Inter', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
