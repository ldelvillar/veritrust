import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import fc from 'fast-check';
import { afterEach } from 'vitest';

// CI replays the same examples every run, so a property fails there only on a change, never on a fresh draw.
if (process.env.CI) fc.configureGlobal({ seed: 0 });

afterEach(() => {
  cleanup();
});
