'use client';

import { Show, SignInButton, UserButton, useUser } from '@clerk/nextjs';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useState } from 'react';
import SidebarIcon from '@/assets/Sidebar';
import Logo from '@/assets/Logo';

type IconProps = { className?: string };

function GridIcon({ className }: IconProps) {
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
      <rect x="3" y="3" width="7" height="7" rx="1.5" />
      <rect x="14" y="3" width="7" height="7" rx="1.5" />
      <rect x="3" y="14" width="7" height="7" rx="1.5" />
      <rect x="14" y="14" width="7" height="7" rx="1.5" />
    </svg>
  );
}

function ScanIcon({ className }: IconProps) {
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
      <path d="M4 8V5.5A1.5 1.5 0 0 1 5.5 4H8M16 4h2.5A1.5 1.5 0 0 1 20 5.5V8M20 16v2.5a1.5 1.5 0 0 1-1.5 1.5H16M8 20H5.5A1.5 1.5 0 0 1 4 18.5V16M7.5 12h9" />
    </svg>
  );
}

function ListIcon({ className }: IconProps) {
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
      <line x1="8" y1="6" x2="20" y2="6" />
      <line x1="8" y1="12" x2="20" y2="12" />
      <line x1="8" y1="18" x2="20" y2="18" />
      <circle cx="3.5" cy="6" r="1" />
      <circle cx="3.5" cy="12" r="1" />
      <circle cx="3.5" cy="18" r="1" />
    </svg>
  );
}

function HelpIcon({ className }: IconProps) {
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
      <circle cx="12" cy="12" r="9" />
      <path d="M9.5 9a2.5 2.5 0 1 1 3.5 2.3c-.7.3-1 .8-1 1.7M12 17h.01" />
    </svg>
  );
}

const navItems = [
  { href: '/app/dashboard', label: 'Dashboard', Icon: GridIcon },
  { href: '/app/analisis', label: 'Analizar', Icon: ScanIcon },
  { href: '/app/historial', label: 'Análisis anteriores', Icon: ListIcon },
];

function Brand({
  onNavigate,
  onCollapse,
  onExpand,
  collapsed,
}: {
  onNavigate?: () => void;
  onCollapse?: () => void;
  onExpand?: () => void;
  collapsed?: boolean;
}) {
  if (collapsed) {
    return (
      <button
        onClick={onExpand}
        aria-label="Expandir menú"
        title="Expandir menú"
        className="group relative mx-auto mt-1 mb-5.5 flex size-10 items-center justify-center rounded-xl transition hover:bg-[#f4f2fd]"
      >
        <Logo className="h-6 w-auto transition-opacity group-hover:opacity-0" />
        <div className="absolute inset-0 flex items-center justify-center text-xl text-[#33344c] opacity-0 transition-opacity group-hover:opacity-100">
          <SidebarIcon />
        </div>
      </button>
    );
  }

  return (
    <div className="flex items-center justify-between px-2.5 pt-1 pb-5.5">
      <Link
        href="/app/analisis"
        onClick={onNavigate}
        className="flex items-center"
      >
        <span className="text-[19px] font-bold tracking-[-0.02em] text-[#15162c]">
          VeriTrust
        </span>
      </Link>
      {onCollapse && (
        <button
          onClick={onCollapse}
          className="-mr-1.5 flex size-8 items-center justify-center rounded-lg text-[#a3a4ba] transition hover:bg-[#f4f2fd] hover:text-[#33344c]"
          aria-label="Colapsar menú"
          title="Colapsar menú"
        >
          <SidebarIcon />
        </button>
      )}
    </div>
  );
}

function SidebarContent({
  onNavigate,
  onCollapse,
  onExpand,
  collapsed,
}: {
  onNavigate?: () => void;
  onCollapse?: () => void;
  onExpand?: () => void;
  collapsed?: boolean;
}) {
  const pathname = usePathname();
  const { user } = useUser();

  const isActive = (href: string) =>
    pathname === href || pathname.startsWith(`${href}/`);

  return (
    <div className="flex h-full w-full flex-col">
      <Brand
        onNavigate={onNavigate}
        onCollapse={onCollapse}
        onExpand={onExpand}
        collapsed={collapsed}
      />

      {!collapsed && (
        <div className="px-3 pt-4.5 pb-2 text-[10.5px] font-bold tracking-[0.13em] text-[#9698b1] uppercase">
          Menú
        </div>
      )}
      <div className={collapsed ? 'flex flex-col items-center gap-2' : ''}>
        {navItems.map(({ href, label, Icon }) => {
          const active = isActive(href);
          return (
            <Link
              key={href}
              href={href}
              onClick={onNavigate}
              aria-current={active ? 'page' : undefined}
              title={collapsed ? label : undefined}
              className={`mb-0.5 flex items-center rounded-xl py-2.5 text-[14.5px] font-semibold transition ${
                collapsed ? 'h-11 w-11 justify-center' : 'gap-3.5 px-3.5'
              } ${
                active
                  ? 'bg-[#efedfc] text-[#5446dc]'
                  : 'text-[#7e7f99] hover:bg-[#f4f2fd] hover:text-[#33344c]'
              }`}
            >
              <Icon
                className={`size-4.75 shrink-0 ${active ? 'text-primary' : ''}`}
              />
              {!collapsed && <span>{label}</span>}
            </Link>
          );
        })}
      </div>

      {!collapsed && (
        <div className="px-3 pt-4.5 pb-2 text-[10.5px] font-bold tracking-[0.13em] text-[#9698b1] uppercase">
          Cuenta
        </div>
      )}
      <div
        className={collapsed ? 'mt-2.5 flex flex-col items-center gap-2' : ''}
      >
        <Link
          href="/app/ayuda"
          onClick={onNavigate}
          title={collapsed ? 'Ayuda' : undefined}
          className={`mb-0.5 flex items-center rounded-xl py-2.5 text-[14.5px] font-semibold text-[#7e7f99] transition hover:bg-[#f4f2fd] hover:text-[#33344c] ${
            collapsed ? 'h-11 w-11 justify-center' : 'gap-3.5 px-3.5'
          }`}
        >
          <HelpIcon className="size-4.75 shrink-0" />
          {!collapsed && <span>Ayuda</span>}
        </Link>
      </div>

      <div className="mt-auto">
        {!collapsed && (
          <div className="mb-3.5 rounded-2xl border border-[#e8e6f4] bg-[#f4f2fd] p-4">
            <h4 className="text-[13.5px] font-bold text-[#15162c]">
              ¿Necesitas más análisis?
            </h4>
            <p className="mt-1 mb-3 text-xs leading-snug text-[#7e7f99]">
              Mejora tu plan para verificar sin límites.
            </p>
            <Link
              href="/#precios"
              onClick={onNavigate}
              className="flex w-full items-center justify-center rounded-lg bg-primary px-3 py-2 text-[13px] font-semibold text-white transition hover:bg-[#3722b8]"
            >
              Ver planes
            </Link>
          </div>
        )}

        <Show when="signed-in">
          <div
            className={`flex items-center py-1.5 ${collapsed ? 'mt-2 justify-center border-t border-[#e8e6f4] pt-4' : 'gap-3 px-1.5'}`}
          >
            <UserButton />
            {!collapsed && (
              <div className="min-w-0">
                <div className="truncate text-[13.5px] font-bold text-[#33344c]">
                  {user?.fullName ?? 'Mi cuenta'}
                </div>
                <div className="truncate text-[11.5px] text-[#a3a4ba]">
                  {user?.primaryEmailAddress?.emailAddress ?? ''}
                </div>
              </div>
            )}
          </div>
        </Show>
        <Show when="signed-out">
          <SignInButton>
            {collapsed ? (
              <button
                aria-label="Iniciar sesión"
                className="mx-auto flex size-11 cursor-pointer items-center justify-center rounded-xl border border-[#dcd9ee] text-[#33344c] transition hover:border-primary hover:text-primary"
              >
                <svg
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth={1.9}
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  className="size-5"
                >
                  <path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4" />
                  <polyline points="10 17 15 12 10 7" />
                  <line x1="15" y1="12" x2="3" y2="12" />
                </svg>
              </button>
            ) : (
              <button className="w-full cursor-pointer rounded-lg border border-[#dcd9ee] px-3 py-2.5 text-[14px] font-semibold text-[#33344c] transition hover:border-primary hover:text-primary">
                Iniciar sesión
              </button>
            )}
          </SignInButton>
        </Show>
      </div>
    </div>
  );
}

export default function Sidebar() {
  const [open, setOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const close = () => setOpen(false);

  return (
    <>
      {/* Desktop sidebar */}
      <aside
        className={`sticky top-0 hidden h-screen shrink-0 flex-col border-r border-[#e8e6f4] bg-white transition-all duration-300 md:flex print:hidden ${collapsed ? 'w-16 items-center px-0 pt-2 pb-5.5' : 'w-66.5 px-1.5 pt-2 pb-5.5'}`}
      >
        <SidebarContent
          onCollapse={() => setCollapsed(true)}
          onExpand={() => setCollapsed(false)}
          collapsed={collapsed}
        />
      </aside>

      {/* Mobile launcher bar */}
      <div className="sticky top-0 z-40 flex h-14 items-center gap-3 border-b border-[#e8e6f4] bg-white/90 px-4 backdrop-blur-sm md:hidden print:hidden">
        <button
          type="button"
          aria-label="Abrir menú"
          aria-expanded={open}
          onClick={() => setOpen(true)}
          className="inline-flex size-9 items-center justify-center rounded-lg border border-[#e8e6f4] text-[#33344c] transition hover:bg-gray-100"
        >
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth={2}
            strokeLinecap="round"
            className="size-5"
          >
            <path d="M4 6h16M4 12h16M4 18h16" />
          </svg>
        </button>
        <Link href="/app/dashboard" className="flex items-center gap-2">
          <Logo className="h-6 w-auto" />
          <span className="text-base font-bold tracking-[-0.02em] text-[#15162c]">
            VeriTrust
          </span>
        </Link>
      </div>

      {/* Mobile drawer */}
      {open && (
        <div className="fixed inset-0 z-50 md:hidden">
          <div
            className="absolute inset-0 bg-black/40"
            onClick={close}
            aria-hidden="true"
          />
          <aside className="absolute top-0 left-0 flex h-full w-70 max-w-[85%] flex-col overflow-y-auto border-r border-[#e8e6f4] bg-white px-4.5 pt-6.5 pb-5.5">
            <SidebarContent onNavigate={close} />
          </aside>
        </div>
      )}
    </>
  );
}
