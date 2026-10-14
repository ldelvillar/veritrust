import { container } from './container';

const databases = ['PubMed', 'Europe PMC', 'openFDA', 'AEMPS'];

export default function Sources() {
  return (
    <section
      aria-label="Fuentes médicas"
      className="border-b border-line bg-white py-9.5"
    >
      <div className={container}>
        <p className="mb-5 text-center text-sm font-bold tracking-[0.08em] text-faint uppercase">
          Buscamos la evidencia de cada afirmación en
        </p>
        <ul className="flex flex-wrap items-center justify-center gap-x-12 gap-y-3 text-xl font-semibold text-muted">
          {databases.map(name => (
            <li key={name}>{name}</li>
          ))}
        </ul>
      </div>
    </section>
  );
}
