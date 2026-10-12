import { writeFile } from 'node:fs/promises';

const apiBaseUrl = (process.env.API_BASE_URL ?? '').trim().replace(/\/+$/, '');
if (apiBaseUrl && !/^https?:\/\//i.test(apiBaseUrl)) {
  throw new Error('API_BASE_URL debe comenzar con https:// o http://');
}

const config = `window.TURNERO_CONFIG = ${JSON.stringify({ apiBaseUrl })};\n`;
await writeFile(new URL('./public/runtime-config.js', import.meta.url), config, 'utf8');
