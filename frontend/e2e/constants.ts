// Puertos propios para no chocar con el stack de desarrollo en 3000 y 8000.
export const WEB_PORT = 3100;
export const MOCK_API_PORT = 8100;
export const WEB_URL = `http://localhost:${WEB_PORT}`;
export const MOCK_API_URL = `http://localhost:${MOCK_API_PORT}`;

// Sesión de Clerk que auth.setup.ts guarda y reutilizan las pruebas autenticadas.
export const AUTH_FILE = 'e2e/.auth/user.json';

// Usuario de prueba de Clerk; el sufijo +clerk_test evita que Clerk envíe correos reales.
export const E2E_USER_EMAIL = 'e2e+clerk_test@example.com';
