import { notFound } from 'next/navigation';

// Rutas inexistentes bajo /app/* caen aquí para renderizar el 404 con la barra lateral.
export default function AppCatchAll() {
  notFound();
}
