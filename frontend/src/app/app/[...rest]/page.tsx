import { notFound } from 'next/navigation';

// Unknown routes under /app/* land here to render the 404 with the sidebar.
export default function AppCatchAll() {
  notFound();
}
