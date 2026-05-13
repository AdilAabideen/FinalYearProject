// Exposes env configuration.
export const config = {
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000',
} as const;

export type Config = typeof config;

const resolvedBaseUrl = import.meta.env.VITE_API_BASE_URL
  ? config.apiBaseUrl
  : import.meta.env.DEV
    ? ''
    : config.apiBaseUrl;

export const API_BASE_URL = resolvedBaseUrl.replace(/\/+$/, '');

