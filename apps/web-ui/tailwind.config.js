import typography from '@tailwindcss/typography';
import containerQueries from '@tailwindcss/container-queries';

/** @type {import('tailwindcss').Config} */
export default {
	darkMode: 'class',
	content: ['./src/**/*.{html,js,svelte,ts}'],
	theme: {
		extend: {
			colors: {
				// 新能源集团 Brand Colors
				brand: {
					50: '#e6f3ff',
					100: '#b3d9ff',
					200: '#80bfff',
					300: '#4da6ff',
					400: '#1a8cff',
					500: '#0066CC', // Primary Blue
					600: '#0052a3',
					700: '#003d7a',
					800: '#002952',
					900: '#001429'
				},
				secondary: {
					50: '#e6fff7',
					100: '#b3ffeb',
					200: '#80ffdf',
					300: '#4affd2',
					400: '#17ffc6',
					500: '#00B388', // Secondary Green
					600: '#008f6d',
					700: '#006b52',
					800: '#004637',
					900: '#00231b'
				},
				gray: {
					50: 'var(--color-gray-50, #f9f9f9)',
					100: 'var(--color-gray-100, #ececec)',
					200: 'var(--color-gray-200, #e3e3e3)',
					300: 'var(--color-gray-300, #cdcdcd)',
					400: 'var(--color-gray-400, #b4b4b4)',
					500: 'var(--color-gray-500, #9b9b9b)',
					600: 'var(--color-gray-600, #676767)',
					700: 'var(--color-gray-700, #4e4e4e)',
					800: 'var(--color-gray-800, #333)',
					850: 'var(--color-gray-850, #262626)',
					900: 'var(--color-gray-900, #171717)',
					950: 'var(--color-gray-950, #0d0d0d)'
				}
			},
			backgroundImage: {
				'brand-gradient': 'linear-gradient(135deg, #0066CC 0%, #00B388 100%)',
				'brand-gradient-hover': 'linear-gradient(135deg, #0052a3 0%, #008f6d 100%)',
				'glass-light': 'linear-gradient(135deg, rgba(255, 255, 255, 0.1) 0%, rgba(255, 255, 255, 0.05) 100%)',
				'glass-dark': 'linear-gradient(135deg, rgba(0, 0, 0, 0.3) 0%, rgba(0, 0, 0, 0.1) 100%)'
			},
			backdropBlur: {
				xs: '2px'
			},
			boxShadow: {
				'glass-light': '0 8px 32px 0 rgba(31, 38, 135, 0.1)',
				'glass-dark': '0 8px 32px 0 rgba(0, 0, 0, 0.3)',
				'brand': '0 4px 14px 0 rgba(0, 102, 204, 0.3)',
				'brand-lg': '0 10px 40px 0 rgba(0, 102, 204, 0.4)'
			},
			fontFamily: {
				heading: ['Space Grotesk', 'sans-serif'],
				body: ['DM Sans', 'sans-serif']
			},
			typography: {
				DEFAULT: {
					css: {
						pre: false,
						code: false,
						'pre code': false,
						'code::before': false,
						'code::after': false
					}
				}
			},
			padding: {
				'safe-bottom': 'env(safe-area-inset-bottom)'
			},
			transitionProperty: {
				width: 'width'
			}
		}
	},
	plugins: [typography, containerQueries]
};
