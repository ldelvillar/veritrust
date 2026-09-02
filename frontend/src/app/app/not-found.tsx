import Button from '@/components/Button';

export default function AppNotFound() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center px-6 py-24 text-center">
      <div className="animate-fade-in max-w-md space-y-6">
        <p className="bg-linear-to-b from-primary to-ink-deep bg-clip-text text-8xl font-black text-transparent">
          404
        </p>

        <div className="space-y-2">
          <h1 className="text-2xl font-bold text-ink md:text-3xl">
            No encontramos esta página
          </h1>
          <p className="text-muted">
            El recurso que buscas no existe o ya no está disponible.
          </p>
        </div>

        <div className="flex flex-col justify-center gap-3 sm:flex-row">
          <Button href="/app/analisis" size="lg">
            Nuevo análisis
          </Button>
          <Button href="/app/historial" variant="soft" size="lg">
            Ver mi historial
          </Button>
        </div>
      </div>
    </div>
  );
}
