'use client';

import { useUser } from '@clerk/nextjs';
import CalendarIcon from '@/assets/Calendar';
import ListIcon from '@/assets/List';
import LockIcon from '@/assets/Lock';

interface AccountSummaryCardProps {
  totalCount: number;
}

const numberFormatter = new Intl.NumberFormat('es-ES');

function formatMemberSince(date: Date | null): string {
  if (!date) return '—';
  return new Intl.DateTimeFormat('es-ES', {
    month: 'long',
    year: 'numeric',
  }).format(date);
}

function getInitials(name: string | null | undefined, email: string): string {
  const source = (name ?? '').trim();
  if (source) {
    const parts = source.split(/\s+/);
    const first = parts[0]?.[0] ?? '';
    const last = parts.length > 1 ? (parts[parts.length - 1]?.[0] ?? '') : '';
    return (first + last).toUpperCase() || first.toUpperCase();
  }
  return (email[0] ?? '?').toUpperCase();
}

export default function AccountSummaryCard({
  totalCount,
}: AccountSummaryCardProps) {
  const { user, isLoaded } = useUser();

  const fullName = user?.fullName ?? null;
  const email = user?.primaryEmailAddress?.emailAddress ?? '';
  const memberSince = formatMemberSince(
    user?.createdAt ? new Date(user.createdAt) : null
  );
  const initials = getInitials(fullName, email);

  return (
    <section
      aria-labelledby="cuenta-resumen-title"
      className="rounded-2xl border border-line bg-white p-6 shadow-[0_1px_2px_rgba(18,33,31,.05),0_10px_30px_rgba(18,33,31,.06)] md:p-7"
    >
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <h2
            id="cuenta-resumen-title"
            className="text-lg font-bold tracking-tight text-ink"
          >
            Resumen de la cuenta
          </h2>
          <p className="mt-1 text-sm font-medium text-muted">
            Tu perfil tal y como lo conoce VeriTrust. Solo de lectura.
          </p>
        </div>
        <span className="hidden shrink-0 items-center gap-1.5 rounded-full border border-line bg-surface-subtle px-3 py-1.5 text-xs font-bold text-muted sm:inline-flex">
          <LockIcon className="size-3.5 text-faint" aria-hidden />
          Edítalo desde tu cuenta
        </span>
      </div>

      {!isLoaded ? (
        <div className="mt-6 animate-pulse">
          <div className="flex items-center gap-4">
            <div className="size-14 rounded-full bg-surface" />
            <div className="flex-1 space-y-2.5">
              <div className="h-4 w-40 rounded bg-surface" />
              <div className="h-3 w-56 rounded bg-surface" />
            </div>
          </div>
          <div className="mt-6 grid grid-cols-1 gap-3 border-t border-line pt-6 sm:grid-cols-2">
            <div className="h-16 rounded-xl bg-surface" />
            <div className="h-16 rounded-xl bg-surface" />
          </div>
        </div>
      ) : (
        <>
          <div className="mt-6 flex items-center gap-4">
            {user?.imageUrl ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={user.imageUrl}
                alt=""
                className="size-14 shrink-0 rounded-full object-cover"
              />
            ) : (
              <span
                aria-hidden
                className="grid size-14 shrink-0 place-items-center rounded-full bg-primary text-xl font-bold text-white"
              >
                {initials}
              </span>
            )}
            <div className="min-w-0">
              <div className="truncate text-lg font-bold tracking-tight text-ink">
                {fullName ?? 'Mi cuenta'}
              </div>
              <div className="truncate text-sm text-muted">{email}</div>
            </div>
          </div>

          <dl className="mt-6 grid grid-cols-1 gap-3 border-t border-line pt-6 sm:grid-cols-2">
            <div className="flex items-center gap-3 rounded-xl border border-line bg-surface-subtle px-4 py-3.5">
              <span className="grid size-9 shrink-0 place-items-center rounded-lg border border-line bg-white text-accent">
                <CalendarIcon className="size-4.5" aria-hidden />
              </span>
              <div className="min-w-0">
                <dt className="text-2xs font-extrabold tracking-[0.08em] text-faint uppercase">
                  Miembro desde
                </dt>
                <dd className="mt-0.5 text-base font-bold text-body capitalize">
                  {memberSince}
                </dd>
              </div>
            </div>
            <div className="flex items-center gap-3 rounded-xl border border-line bg-surface-subtle px-4 py-3.5">
              <span className="grid size-9 shrink-0 place-items-center rounded-lg border border-line bg-white text-accent">
                <ListIcon className="size-4.5" aria-hidden />
              </span>
              <div className="min-w-0">
                <dt className="text-2xs font-extrabold tracking-[0.08em] text-faint uppercase">
                  Análisis totales
                </dt>
                <dd className="mt-0.5 text-base font-bold text-body">
                  {numberFormatter.format(totalCount)}
                </dd>
              </div>
            </div>
          </dl>
        </>
      )}
    </section>
  );
}
