/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{html,ts}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#FFD204',
          light: '#FCD34D',
          dark: '#CA8A04',
        },
        secondary: {
          DEFAULT: '#4B5563',
          light: '#9CA3AF',
          dark: '#374151',
        },
        green: {
          DEFAULT: '#00C587',
          light: '#2cffbd',
          dark: '#005f41',
        },
        orange: {
          DEFAULT: '#FF803A',
          light: '#ffc2a0',
          dark: '#d34b00',
        },
        blue: {
          DEFAULT: '#01CDEB',
          light: '#54e8fe',
          dark: '#017485',
        },
        black: {
          DEFAULT: '#2C2A29',
          light: '#2c2a29',
          dark: '#000000',
        },
        neutral: '#FFFFFF',
        dark: {
          bg: '#0d1117',
          surface: '#161b22',
          border: '#21262d',
          text: '#c9d1d9',
          muted: '#8b949e',
          accent: '#58a6ff',
        },
      },
    },
  },
  plugins: [],
}
