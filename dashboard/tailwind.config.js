/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        terminal: {
          bg: '#0a0f1a',
          panel: '#111827',
          border: '#1e293b',
          muted: '#64748b',
        },
        emerald: {
          glow: '#10b981',
        },
        crimson: {
          glow: '#ef4444',
        },
      },
      boxShadow: {
        'glow-emerald': '0 0 40px rgba(16, 185, 129, 0.35)',
        'glow-crimson': '0 0 40px rgba(239, 68, 68, 0.35)',
        'glow-amber': '0 0 40px rgba(245, 158, 11, 0.25)',
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
    },
  },
  plugins: [],
};
