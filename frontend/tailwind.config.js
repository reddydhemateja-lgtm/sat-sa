/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // SAT-SA professional palette
        navy: {
          50: '#f4f6fa',
          100: '#e6ecf5',
          200: '#c8d5e9',
          300: '#94a9c9',
          400: '#5e78a1',
          500: '#3d5680',
          600: '#2b4164',
          700: '#1f3150',
          800: '#162440',
          900: '#0e1a30',
          950: '#060e1d',
        },
        slate: {
          // overriding default for a slightly cooler gray
          50: '#f8fafc',
          100: '#f1f5f9',
          200: '#e2e8f0',
          300: '#cbd5e1',
          400: '#94a3b8',
          500: '#64748b',
          600: '#475569',
          700: '#334155',
          800: '#1e293b',
          900: '#0f172a',
          950: '#020617',
        },
        accent: {
          DEFAULT: '#2563eb',
          soft: '#3b82f6',
          deep: '#1d4ed8',
          muted: '#64748b',
        },
        status: {
          critical: '#dc2626',
          high: '#ea580c',
          warning: '#d97706',
          medium: '#ca8a04',
          info: '#0ea5e9',
          success: '#16a34a',
          muted: '#64748b',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['JetBrains Mono', 'Consolas', 'Monaco', 'monospace'],
      },
      boxShadow: {
        card: '0 1px 2px 0 rgba(15, 23, 42, 0.04), 0 1px 3px 0 rgba(15, 23, 42, 0.06)',
        panel: '0 4px 12px -2px rgba(15, 23, 42, 0.08)',
      },
      transitionDuration: {
        DEFAULT: '180ms',
      },
    },
  },
  plugins: [],
};