/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        bone: '#EBE3D2',
        dun: '#CCBFA3',
        sage: '#A4AC86',
        reseda: '#737A5D',
        ebony: '#414833',
      },
    },
  },
  plugins: [
    require('@tailwindcss/typography'),
  ],
}
