function prodRequired(name: string, devFallback: string): string {
  const value = process.env[name];
  if (value) return value;
  if (process.env.NODE_ENV !== 'production') return devFallback;
  throw new Error(
    `${name} must be set for production builds. See frontend/.env.example.`
  );
}

export const clientEnv = {
  apiUrl: prodRequired('NEXT_PUBLIC_API_URL', 'http://127.0.0.1:8000'),
  clerkPublishableKey: prodRequired('NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY', ''),
};
