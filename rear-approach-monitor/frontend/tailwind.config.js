/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // 다크 안전 모니터링 테마: 검정/짙은 남색 배경 + 청록 포인트
        base: {
          900: '#070b16', // 가장 어두운 배경
          800: '#0a0e1a',
          700: '#111a2e',
          600: '#1a2540',
          500: '#243356',
        },
        accent: {
          DEFAULT: '#22d3ee', // 청록 포인트
          soft: '#0891b2',
        },
        risk: {
          safe: '#22c55e',
          warning: '#eab308',
          danger: '#ef4444',
        },
      },
      fontFamily: {
        mono: ['ui-monospace', 'SFMono-Regular', 'Menlo', 'monospace'],
      },
      boxShadow: {
        'glow-accent': '0 0 0 1px rgba(34,211,238,0.3), 0 0 24px -4px rgba(34,211,238,0.5)',
        'glow-danger': '0 0 0 1px rgba(239,68,68,0.4), 0 0 32px -4px rgba(239,68,68,0.6)',
        'glow-safe': '0 0 0 1px rgba(34,197,94,0.3), 0 0 24px -6px rgba(34,197,94,0.45)',
        'glow-warning': '0 0 0 1px rgba(234,179,8,0.35), 0 0 24px -6px rgba(234,179,8,0.5)',
      },
      keyframes: {
        'pulse-danger': {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.55' },
        },
        'slide-up': {
          '0%': { transform: 'translateY(16px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        'slide-down': {
          '0%': { transform: 'translateY(-16px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        'ping-ring': {
          '0%': { transform: 'scale(1)', opacity: '0.6' },
          '100%': { transform: 'scale(2.4)', opacity: '0' },
        },
        'fade-in': {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        sweep: {
          '0%': { transform: 'rotate(0deg)' },
          '100%': { transform: 'rotate(360deg)' },
        },
      },
      animation: {
        'pulse-danger': 'pulse-danger 1.1s ease-in-out infinite',
        'slide-up': 'slide-up 0.3s ease-out',
        'slide-down': 'slide-down 0.35s ease-out',
        'ping-ring': 'ping-ring 1.6s ease-out infinite',
        'fade-in': 'fade-in 0.4s ease-out',
        sweep: 'sweep 4s linear infinite',
      },
    },
  },
  plugins: [],
};
