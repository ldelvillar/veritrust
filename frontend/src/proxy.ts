import { clerkMiddleware, createRouteMatcher } from '@clerk/nextjs/server';
import { SIGN_IN_URL, SIGN_UP_URL } from '@/config/auth';

const isProtectedRoute = createRouteMatcher(['/app(.*)']);

export default clerkMiddleware(
  async (auth, req) => {
    if (isProtectedRoute(req)) await auth.protect();
  },
  { signInUrl: SIGN_IN_URL, signUpUrl: SIGN_UP_URL }
);

export const config = {
  matcher: [
    // Skip Next.js internals and all static files, unless found in search params
    '/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)',
    // Always run for API routes
    '/(api|trpc)(.*)',
  ],
};
