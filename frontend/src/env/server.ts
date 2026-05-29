import 'server-only';

function prodRequired(name: string, devFallback: string): string {
  const value = process.env[name];
  if (value) return value;
  if (process.env.NODE_ENV !== 'production') return devFallback;
  throw new Error(
    `${name} must be set for production builds. See frontend/.env.example.`
  );
}

const apiUrl =
  process.env.INTERNAL_API_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  (process.env.NODE_ENV !== 'production' ? 'http://127.0.0.1:8000' : '');

if (!apiUrl) {
  throw new Error(
    'INTERNAL_API_URL or NEXT_PUBLIC_API_URL must be set for production server-side fetches. ' +
      'A missing value would cause the Next.js server to call its own localhost.'
  );
}

export const serverEnv = {
  apiUrl,
  get clerkSecretKey() {
    return prodRequired('CLERK_SECRET_KEY', '');
  },
};
