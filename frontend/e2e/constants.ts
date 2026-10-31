// Own ports so as not to clash with the development stack on 3000 and 8000.
export const WEB_PORT = 3100;
export const MOCK_API_PORT = 8100;
export const WEB_URL = `http://localhost:${WEB_PORT}`;
export const MOCK_API_URL = `http://localhost:${MOCK_API_PORT}`;

// Clerk session that auth.setup.ts saves and the authenticated tests reuse.
export const AUTH_FILE = 'e2e/.auth/user.json';

// Clerk test user, where the +clerk_test suffix stops Clerk from sending real emails.
export const E2E_USER_EMAIL = 'e2e+clerk_test@example.com';
