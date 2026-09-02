'use client';

import Link from 'next/link';
import { useState } from 'react';
import CheckIcon from '@/assets/Check';
import ShieldIcon from '@/assets/Shield';
import Spinner from '@/assets/Spinner';
import WarningIcon from '@/assets/Warning';
import Button from '@/components/Button';
import { useContactSubmission } from '@/hooks/useContactSubmission';

type Values = {
  nombre: string;
  email: string;
  asunto: string;
  mensaje: string;
  consent: boolean;
};

type FieldErrors = Partial<Record<keyof Values, boolean>>;

const motivos = [
  'Consulta general',
  'Soporte técnico',
  'Ventas / planes',
  'Prensa',
  'Alianza / colaboración',
];

const EMAIL_RE = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

const inputBase =
  'w-full rounded-[11px] border px-3.5 py-3.25 text-[14.5px] text-body transition placeholder:text-faint focus:border-primary focus:bg-white focus:outline-none focus:ring-4 focus:ring-primary-soft';

function fieldClass(invalid: boolean) {
  return `${inputBase} ${
    invalid
      ? 'border-danger bg-danger-soft'
      : 'border-line-strong bg-surface-subtle'
  }`;
}

const labelClass = 'flex items-center gap-1.5 text-[13px] font-bold text-body';
const errClass = 'text-[12px] font-semibold text-danger-ink';
const reqMark = <span className="text-primary">*</span>;

export default function ContactForm() {
  const [values, setValues] = useState<Values>({
    nombre: '',
    email: '',
    asunto: '',
    mensaje: '',
    consent: false,
  });
  const [errors, setErrors] = useState<FieldErrors>({});
  const [sent, setSent] = useState(false);
  const [firstName, setFirstName] = useState('');
  const { submit, isLoading, error } = useContactSubmission();

  const update = <K extends keyof Values>(key: K, value: Values[K]) => {
    setValues(prev => ({ ...prev, [key]: value }));
    setErrors(prev => {
      if (!prev[key]) return prev;
      const next = { ...prev };
      delete next[key];
      return next;
    });
  };

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const next: FieldErrors = {};
    if (!values.nombre.trim()) next.nombre = true;
    if (!EMAIL_RE.test(values.email)) next.email = true;
    if (!values.asunto) next.asunto = true;
    if (!values.mensaje.trim()) next.mensaje = true;
    if (!values.consent) next.consent = true;

    setErrors(next);
    if (Object.keys(next).length > 0) return;

    const ok = await submit({
      type: 'contact',
      name: values.nombre.trim(),
      email: values.email.trim(),
      subject: values.asunto,
      message: values.mensaje.trim(),
    });
    if (!ok) return;

    setFirstName(values.nombre.trim().split(' ')[0]);
    setSent(true);
  };

  return (
    <div
      id="formulario"
      className="rounded-[20px] border border-line bg-white px-8 py-8.5 shadow-[0_1px_2px_rgba(18,33,31,0.05),0_10px_30px_rgba(18,33,31,0.06)]"
    >
      {sent ? (
        <div className="flex flex-col items-center px-5 py-7.5 text-center">
          <div className="mb-5.5 grid size-18.5 place-items-center rounded-[20px] bg-success-soft text-success-ink">
            <CheckIcon className="size-9.5" strokeWidth={2.2} />
          </div>
          <h2 className="mb-3 text-[27px] font-bold tracking-[-0.02em] text-ink">
            Mensaje enviado
          </h2>
          <p className="mb-6.5 max-w-107.5 text-[15.5px] leading-relaxed text-muted">
            {firstName ? `Gracias, ${firstName}` : 'Gracias por escribirnos'}.
            Nuestro equipo te responderá en menos de 24&nbsp;h laborables.
          </p>
          <Button href="/" size="lg">
            Volver al inicio
          </Button>
        </div>
      ) : (
        <>
          <h3 className="text-[19px] font-bold text-ink">
            Envíanos un mensaje
          </h3>
          <p className="mt-1.5 mb-6 text-[14px] leading-snug text-muted">
            Rellena el formulario y te responderemos en menos de 24&nbsp;h
            laborables.
          </p>

          <form noValidate onSubmit={handleSubmit}>
            <div className="grid gap-x-5 gap-y-4.5 md:grid-cols-2">
              <div className="flex flex-col gap-2">
                <label htmlFor="nombre" className={labelClass}>
                  Nombre {reqMark}
                </label>
                <input
                  id="nombre"
                  name="nombre"
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
                  Email {reqMark}
                </label>
                <input
                  id="email"
                  name="email"
                  type="email"
                  placeholder="tu@email.com"
                  value={values.email}
                  onChange={e => update('email', e.target.value)}
                  className={fieldClass(!!errors.email)}
                />
                {errors.email && (
                  <span className={errClass}>Introduce un email válido.</span>
                )}
              </div>

              <div className="flex flex-col gap-2 md:col-span-2">
                <label htmlFor="asunto" className={labelClass}>
                  Motivo {reqMark}
                </label>
                <div className="relative">
                  <select
                    id="asunto"
                    name="asunto"
                    value={values.asunto}
                    onChange={e => update('asunto', e.target.value)}
                    className={`${fieldClass(!!errors.asunto)} cursor-pointer appearance-none pr-10`}
                  >
                    <option value="">Selecciona un motivo…</option>
                    {motivos.map(m => (
                      <option key={m}>{m}</option>
                    ))}
                  </select>
                  <svg
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth={2.4}
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    className="pointer-events-none absolute top-1/2 right-3.5 size-4 -translate-y-1/2 text-faint"
                  >
                    <path d="M6 9l6 6 6-6" />
                  </svg>
                </div>
                {errors.asunto && (
                  <span className={errClass}>Selecciona un motivo.</span>
                )}
              </div>

              <div className="flex flex-col gap-2 md:col-span-2">
                <label htmlFor="mensaje" className={labelClass}>
                  Mensaje {reqMark}
                </label>
                <textarea
                  id="mensaje"
                  name="mensaje"
                  placeholder="¿En qué podemos ayudarte?"
                  value={values.mensaje}
                  onChange={e => update('mensaje', e.target.value)}
                  className={`${fieldClass(!!errors.mensaje)} min-h-29.5 resize-y leading-relaxed`}
                />
                {errors.mensaje && (
                  <span className={errClass}>Escribe tu mensaje.</span>
                )}
              </div>

              <div className="flex flex-col gap-2 md:col-span-2">
                <div className="mt-1 flex items-start gap-2.75">
                  <input
                    id="consent"
                    name="consent"
                    type="checkbox"
                    checked={values.consent}
                    onChange={e => update('consent', e.target.checked)}
                    className="mt-0.5 size-4.5 shrink-0 cursor-pointer accent-primary"
                  />
                  <label
                    htmlFor="consent"
                    className="text-[12.5px] leading-snug font-medium text-muted"
                  >
                    Acepto la{' '}
                    <Link
                      href="/politica-de-privacidad"
                      className="font-bold text-accent underline underline-offset-2"
                    >
                      Política de privacidad
                    </Link>{' '}
                    y el tratamiento de mis datos para responder a mi consulta.
                  </label>
                </div>
                {errors.consent && (
                  <span className={`mt-2 block ${errClass}`}>
                    Debes aceptar para continuar.
                  </span>
                )}
              </div>
            </div>

            {error && (
              <div
                role="alert"
                className="mt-6 flex w-full items-center gap-2 rounded-xl border border-danger/20 bg-danger-soft p-4 text-sm text-danger-ink"
              >
                <WarningIcon className="size-5 shrink-0" />
                <p>{error}</p>
              </div>
            )}

            <div className="mt-7 flex flex-wrap items-center gap-4">
              <Button type="submit" size="lg" disabled={isLoading}>
                {isLoading ? (
                  <>
                    <Spinner className="size-5 animate-spin" />
                    Enviando…
                  </>
                ) : (
                  'Enviar mensaje'
                )}
              </Button>
              <span className="flex items-center gap-1.75 text-[12.5px] text-muted">
                <ShieldIcon
                  className="size-3.75 text-faint"
                  strokeWidth={2.1}
                />
                Tus datos están seguros
              </span>
            </div>
          </form>
        </>
      )}
    </div>
  );
}
