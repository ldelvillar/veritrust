'use client';

import { useEffect, useId, useRef, useState } from 'react';
import type { KeyboardEvent, ReactNode } from 'react';
import ChevronDownIcon from '@/assets/ChevronDown';
import CheckIcon from '@/assets/Check';

interface FilterSelectOption<T extends string> {
  value: T;
  label: string;
}

interface FilterSelectProps<T extends string> {
  value: T;
  onChange: (value: T) => void;
  options: readonly FilterSelectOption<T>[];
  icon: ReactNode;
  ariaLabel: string;
  className?: string;
}

export default function FilterSelect<T extends string>({
  value,
  onChange,
  options,
  icon,
  ariaLabel,
  className = '',
}: FilterSelectProps<T>) {
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const rootRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const listRef = useRef<HTMLUListElement>(null);
  const listId = useId();

  const selectedIndex = Math.max(
    0,
    options.findIndex(o => o.value === value)
  );
  const current = options[selectedIndex] ?? options[0];

  const openMenu = () => {
    setActive(selectedIndex);
    setOpen(true);
  };

  // Al abrir: mueve el foco a la lista y cierra al hacer clic fuera.
  useEffect(() => {
    if (!open) return;
    listRef.current?.focus();
    const onDoc = (e: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', onDoc);
    return () => document.removeEventListener('mousedown', onDoc);
  }, [open]);

  // Mantiene visible la opción resaltada al navegar con el teclado.
  useEffect(() => {
    if (!open) return;
    const el = listRef.current?.children[active] as HTMLElement | undefined;
    el?.scrollIntoView({ block: 'nearest' });
  }, [active, open]);

  const commit = (index: number) => {
    onChange(options[index].value);
    setOpen(false);
    buttonRef.current?.focus();
  };

  const onButtonKeyDown = (e: KeyboardEvent) => {
    if (e.key === 'ArrowDown' || e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      openMenu();
    }
  };

  const onListKeyDown = (e: KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setActive(a => Math.min(options.length - 1, a + 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setActive(a => Math.max(0, a - 1));
    } else if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      commit(active);
    } else if (e.key === 'Home') {
      e.preventDefault();
      setActive(0);
    } else if (e.key === 'End') {
      e.preventDefault();
      setActive(options.length - 1);
    } else if (e.key === 'Escape') {
      e.preventDefault();
      setOpen(false);
      buttonRef.current?.focus();
    } else if (e.key === 'Tab') {
      setOpen(false);
    }
  };

  return (
    <div ref={rootRef} className={`relative ${className}`}>
      <button
        ref={buttonRef}
        type="button"
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-label={ariaLabel}
        onClick={() => (open ? setOpen(false) : openMenu())}
        onKeyDown={onButtonKeyDown}
        className={`group flex h-11.5 w-full cursor-pointer items-center gap-2.25 rounded-[13px] border bg-white pr-3.25 pl-3.5 text-[13.5px] font-semibold whitespace-nowrap transition outline-none hover:border-primary hover:text-primary sm:w-auto ${
          open
            ? 'border-primary text-primary ring-4 ring-primary/10'
            : 'border-line-strong text-body'
        }`}
      >
        <span
          className={`grid shrink-0 place-items-center transition-colors group-hover:text-primary ${
            open ? 'text-primary' : 'text-faint'
          }`}
        >
          {icon}
        </span>
        <span className="flex-1 text-left">{current.label}</span>
        <ChevronDownIcon
          aria-hidden
          className={`size-3.75 shrink-0 transition-transform group-hover:text-primary ${
            open ? 'rotate-180 text-primary' : 'text-faint'
          }`}
        />
      </button>
      {open ? (
        <ul
          ref={listRef}
          id={listId}
          role="listbox"
          tabIndex={-1}
          aria-label={ariaLabel}
          aria-activedescendant={`${listId}-opt-${active}`}
          onKeyDown={onListKeyDown}
          className="animate-select-in absolute top-[calc(100%+7px)] right-0 left-0 z-40 m-0 max-h-80 min-w-full list-none overflow-y-auto rounded-[14px] border border-line-strong bg-white p-1.5 shadow-[0_10px_30px_rgba(92,80,200,0.10),0_4px_12px_rgba(20,20,40,0.06)] outline-none sm:right-auto"
        >
          {options.map((opt, i) => {
            const isSelected = opt.value === value;
            const isActive = i === active;
            return (
              <li
                key={opt.value}
                id={`${listId}-opt-${i}`}
                role="option"
                aria-selected={isSelected}
                onMouseEnter={() => setActive(i)}
                onClick={() => commit(i)}
                className={`flex cursor-pointer items-center gap-2.5 rounded-[9px] px-2.75 py-2.25 text-[13.5px] font-semibold whitespace-nowrap transition-colors ${
                  isActive && isSelected
                    ? 'bg-primary/15 text-primary'
                    : isActive
                      ? 'bg-primary/10 text-primary'
                      : isSelected
                        ? 'text-primary'
                        : 'text-body'
                }`}
              >
                <span className="flex-1">{opt.label}</span>
                <span className="grid w-3.75 shrink-0 place-items-center text-primary">
                  {isSelected ? (
                    <CheckIcon className="size-3.75" aria-hidden />
                  ) : null}
                </span>
              </li>
            );
          })}
        </ul>
      ) : null}
    </div>
  );
}
