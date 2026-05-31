'use client';

import Link from 'next/link';
import { useState } from 'react';

type Values = {
  nombre: string;
  email: string;
  org: string;
  cargo: string;
  perfil: string;
  volumen: string;
  equipo: string;
  mensaje: string;
  consent: boolean;
};

type RequiredKey = 'nombre' | 'email' | 'org' | 'perfil' | 'consent';
type FieldErrors = Partial<Record<RequiredKey, boolean>>;

const EMAIL_RE = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

const volumenOpts = [
  'Menos de 100 análisis / mes',
  '100 – 500 análisis / mes',
  '500 – 2.000 análisis / mes',
  'Más de 2.000 análisis / mes',
];
const equipoOpts = [
  '1 – 5 personas',
  '6 – 20 personas',
  '21 – 100 personas',
  'Más de 100 personas',
];

const inputBase =
  'w-full rounded-[11px] border px-3.5 py-3.25 text-[14.5px] text-[#33344c] transition placeholder:text-[#9698b1] focus:border-primary focus:bg-white focus:outline-none focus:ring-4 focus:ring-[#efedfc]';

function fieldClass(invalid: boolean) {
  return `${inputBase} ${
    invalid ? 'border-[#e0556b] bg-[#fbe4e8]' : 'border-[#dcd9ee] bg-[#faf9fe]'
  }`;
}

const labelClass =
  'flex items-center gap-1.5 text-[13px] font-bold text-[#33344c]';
const errClass = 'text-[12px] font-semibold text-[#c23552]';
const reqMark = <span className="text-primary">*</span>;
const optMark = (
  <span className="text-[11.5px] font-semibold text-[#9698b1]">(opcional)</span>
);

type IconProps = { className?: string };

function PressIcon({ className }: IconProps) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.9}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <path d="M4 4h12a2 2 0 0 1 2 2v13a1 1 0 0 1-1 1H6a2 2 0 0 1-2-2zM18 8h2a1 1 0 0 1 1 1v9a2 2 0 0 1-2 2M7 8h7M7 12h7M7 16h4" />
    </svg>
  );
}
function HealthIcon({ className }: IconProps) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.9}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <path d="M3 21h18M5 21V8l7-5 7 5v13M9 21v-6h6v6" />
    </svg>
  );
}
function InstitutionIcon({ className }: IconProps) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.9}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <path d="M3 9l9-6 9 6M5 10v9a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-9M9 21v-6h6v6" />
    </svg>
  );
}
function CheckIcon({ className }: IconProps) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2.2}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <path d="M20 6 9 17l-5-5" />
    </svg>
  );
}
function ShieldIcon({ className }: IconProps) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2.1}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
    >
      <path d="M12 3l7 3v5c0 4.5-3 8.5-7 10-4-1.5-7-5.5-7-10V6z" />
      <path d="M9 12l2 2 4-4" />
    </svg>
  );
}

const perfiles = [
  { value: 'periodismo', label: 'Periodismo / verificación', Icon: PressIcon },
  { value: 'salud-publica', label: 'Salud pública', Icon: HealthIcon },
  { value: 'institucion', label: 'Institución / otra', Icon: InstitutionIcon },
];

function ChevronSelect({
  id,
  value,
  onChange,
  children,
}: {
  id: string;
  value: string;
  onChange: (v: string) => void;
  children: React.ReactNode;
}) {
  return (
    <div className="relative">
      <select
        id={id}
        name={id}
        value={value}
        onChange={e => onChange(e.target.value)}
        className={`${fieldClass(false)} cursor-pointer appearance-none pr-10`}
      >
        {children}
      </select>
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth={2.4}
        strokeLinecap="round"
        strokeLinejoin="round"
        className="pointer-events-none absolute top-1/2 right-3.5 size-4 -translate-y-1/2 text-[#9698b1]"
      >
        <path d="M6 9l6 6 6-6" />
      </svg>
    </div>
  );
}

export default function DemoForm() {
  const [values, setValues] = useState<Values>({
    nombre: '',
    email: '',
    org: '',
    cargo: '',
    perfil: '',
    volumen: '',
    equipo: '',
    mensaje: '',
    consent: false,
  });
  const [errors, setErrors] = useState<FieldErrors>({});
  const [sent, setSent] = useState(false);
  const [firstName, setFirstName] = useState('');

  const update = <K extends keyof Values>(key: K, value: Values[K]) => {
    setValues(prev => ({ ...prev, [key]: value }));
    setErrors(prev => {
      if (!(key in prev)) return prev;
      const next = { ...prev };
      delete next[key as RequiredKey];
      return next;
    });
  };

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const next: FieldErrors = {};
    if (!values.nombre.trim()) next.nombre = true;
    if (!EMAIL_RE.test(values.email)) next.email = true;
    if (!values.org.trim()) next.org = true;
    if (!values.perfil) next.perfil = true;
    if (!values.consent) next.consent = true;

    setErrors(next);
    if (Object.keys(next).length > 0) return;

    setFirstName(values.nombre.trim().split(' ')[0]);
    setSent(true);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  if (sent) {
    return (
      <div className="px-6.5 py-8.5 md:px-11.5 md:py-11">
        <div className="flex flex-col items-center px-5 py-7.5 text-center">
          <div className="mb-5.5 grid size-18.5 place-items-center rounded-[20px] bg-[#def4ea] text-[#0e8e5b]">
            <CheckIcon className="size-9.5" />
          </div>
          <h2 className="mb-3 text-[27px] font-bold tracking-[-0.02em] text-[#15162c]">
            ¡Solicitud recibida!
          </h2>
          <p className="mb-6.5 max-w-107.5 text-[15.5px] leading-relaxed text-[#7e7f99]">
            {firstName ? `Gracias, ${firstName}` : 'Gracias'}. Un especialista
            de VeriTrust te escribirá en menos de 24&nbsp;h laborables para
            agendar tu demo.
          </p>
          <div className="flex flex-wrap justify-center gap-3">
            <Link
              href="/app/analisis"
              className="inline-flex items-center justify-center rounded-xl bg-primary px-5.5 py-3.25 text-[15px] font-semibold text-white shadow-[0_8px_22px_rgba(67,45,215,0.32)] transition hover:-translate-y-0.5 hover:bg-[#3722b8]"
            >
              Mientras tanto, analiza gratis →
            </Link>
            <Link
              href="/"
              className="inline-flex items-center justify-center rounded-xl border border-[#dcd9ee] bg-white px-5.5 py-3.25 text-[15px] font-semibold text-[#33344c] transition hover:border-primary hover:text-primary"
            >
              Volver al inicio
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="px-6.5 py-8.5 md:px-11.5 md:py-11">
      <span className="text-[12.5px] font-extrabold tracking-widest text-[#5446dc] uppercase">
        Cuéntanos sobre ti
      </span>
      <h2 className="mt-2.5 mb-2 text-[26px] font-bold tracking-[-0.02em] text-[#15162c]">
        Reserva tu demo
      </h2>
      <p className="mb-7.5 text-[15px] leading-snug text-[#7e7f99]">
        Un especialista te contactará en menos de 24&nbsp;h laborables para
        agendar una sesión.
      </p>

      <form noValidate onSubmit={handleSubmit}>
        <div className="grid gap-x-5 gap-y-4.5 md:grid-cols-2">
          <div className="flex flex-col gap-2">
            <label htmlFor="nombre" className={labelClass}>
              Nombre {reqMark}
            </label>
            <input
              id="nombre"
              type="text"
              placeholder="Tu nombre"
              value={values.nombre}
              onChange={e => update('nombre', e.target.value)}
              className={fieldClass(!!errors.nombre)}
            />
            {errors.nombre && (
              <span className={errClass}>Indica tu nombre.</span>
            )}
          </div>

          <div className="flex flex-col gap-2">
            <label htmlFor="email" className={labelClass}>
              Email profesional {reqMark}
            </label>
            <input
              id="email"
              type="email"
              placeholder="tu.email@medio.es"
              value={values.email}
              onChange={e => update('email', e.target.value)}
              className={fieldClass(!!errors.email)}
            />
            {errors.email && (
              <span className={errClass}>Introduce un email válido.</span>
            )}
          </div>

          <div className="flex flex-col gap-2">
            <label htmlFor="org" className={labelClass}>
              Organización {reqMark}
            </label>
            <input
              id="org"
              type="text"
              placeholder="Nombre de tu medio o institución"
              value={values.org}
              onChange={e => update('org', e.target.value)}
              className={fieldClass(!!errors.org)}
            />
            {errors.org && (
              <span className={errClass}>Indica tu organización.</span>
            )}
          </div>

          <div className="flex flex-col gap-2">
            <label htmlFor="cargo" className={labelClass}>
              Cargo {optMark}
            </label>
            <input
              id="cargo"
              type="text"
              placeholder="Editor/a, responsable de comunicación…"
              value={values.cargo}
              onChange={e => update('cargo', e.target.value)}
              className={fieldClass(false)}
            />
          </div>

          <div className="flex flex-col gap-2 md:col-span-2">
            <label className={labelClass}>
              ¿Cuál describe mejor tu equipo? {reqMark}
            </label>
            <div
              role="radiogroup"
              aria-label="Tipo de equipo"
              className="flex flex-wrap gap-2.5"
            >
              {perfiles.map(({ value, label, Icon }) => {
                const active = values.perfil === value;
                return (
                  <label key={value} className="cursor-pointer">
                    <input
                      type="radio"
                      name="perfil"
                      value={value}
                      checked={active}
                      onChange={() => update('perfil', value)}
                      className="sr-only"
                    />
                    <span
                      className={`inline-flex items-center gap-2 rounded-[11px] border px-3.75 py-2.75 text-[13.5px] font-bold transition ${
                        active
                          ? 'border-primary bg-[#efedfc] text-[#5446dc] ring-1 ring-primary'
                          : 'border-[#dcd9ee] bg-[#faf9fe] text-[#33344c] hover:border-primary hover:text-[#5446dc]'
                      }`}
                    >
                      <Icon
                        className={`size-4 ${active ? 'text-primary' : 'text-[#9698b1]'}`}
                      />
                      {label}
                    </span>
                  </label>
                );
              })}
            </div>
            {errors.perfil && (
              <span className={errClass}>Selecciona una opción.</span>
            )}
          </div>

          <div className="flex flex-col gap-2">
            <label htmlFor="volumen" className={labelClass}>
              Volumen estimado {optMark}
            </label>
            <ChevronSelect
              id="volumen"
              value={values.volumen}
              onChange={v => update('volumen', v)}
            >
              <option value="">Selecciona…</option>
              {volumenOpts.map(o => (
                <option key={o}>{o}</option>
              ))}
            </ChevronSelect>
          </div>

          <div className="flex flex-col gap-2">
            <label htmlFor="equipo" className={labelClass}>
              Tamaño del equipo {optMark}
            </label>
            <ChevronSelect
              id="equipo"
              value={values.equipo}
              onChange={v => update('equipo', v)}
            >
              <option value="">Selecciona…</option>
              {equipoOpts.map(o => (
                <option key={o}>{o}</option>
              ))}
            </ChevronSelect>
          </div>

          <div className="flex flex-col gap-2 md:col-span-2">
            <label htmlFor="mensaje" className={labelClass}>
              ¿Qué quieres resolver con VeriTrust? {optMark}
            </label>
            <textarea
              id="mensaje"
              placeholder="Cuéntanos tu caso: tipo de contenido, idiomas, integración por API…"
              value={values.mensaje}
              onChange={e => update('mensaje', e.target.value)}
              className={`${fieldClass(false)} min-h-29.5 resize-y leading-relaxed`}
            />
          </div>

          <div className="flex flex-col gap-2 md:col-span-2">
            <div className="mt-1 flex items-start gap-2.75">
              <input
                id="consent"
                type="checkbox"
                checked={values.consent}
                onChange={e => update('consent', e.target.checked)}
                className="mt-0.5 size-4.5 shrink-0 cursor-pointer accent-primary"
              />
              <label
                htmlFor="consent"
                className="text-[12.5px] leading-snug font-medium text-[#7e7f99]"
              >
                Acepto que VeriTrust trate mis datos para contactarme sobre la
                demo, de acuerdo con la{' '}
                <Link
                  href="/politica-de-privacidad"
                  className="font-bold text-[#5446dc] underline underline-offset-2"
                >
                  Política de privacidad
                </Link>
                .
              </label>
            </div>
            {errors.consent && (
              <span className={`mt-2 block ${errClass}`}>
                Debes aceptar para continuar.
              </span>
            )}
          </div>
        </div>

        <div className="mt-7 flex flex-wrap items-center gap-4">
          <button
            type="submit"
            className="inline-flex items-center justify-center rounded-xl bg-primary px-7 py-4 text-base font-semibold text-white shadow-[0_8px_22px_rgba(67,45,215,0.32)] transition hover:-translate-y-0.5 hover:bg-[#3722b8]"
          >
            Solicitar demo
          </button>
          <span className="flex items-center gap-1.75 text-[12.5px] text-[#7e7f99]">
            <ShieldIcon className="size-3.75 text-[#9698b1]" />
            Sin compromiso · respondemos en 24&nbsp;h
          </span>
        </div>
      </form>
    </div>
  );
}
