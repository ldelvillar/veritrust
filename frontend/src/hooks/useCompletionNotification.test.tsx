import { renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useCompletionNotification } from './useCompletionNotification';

class MockNotification {
  static permission: NotificationPermission = 'granted';
  static requestPermission = vi.fn(async () => MockNotification.permission);
  static instances: MockNotification[] = [];
  onclick: (() => void) | null = null;
  close = vi.fn();

  constructor(
    public title: string,
    public options?: NotificationOptions
  ) {
    MockNotification.instances.push(this);
  }
}

const setVisibility = (state: DocumentVisibilityState) =>
  Object.defineProperty(document, 'visibilityState', {
    value: state,
    configurable: true,
  });

const renderForStatus = (status: string) =>
  renderHook(({ s }) => useCompletionNotification('abc', s), {
    initialProps: { s: status },
  });

describe('useCompletionNotification', () => {
  beforeEach(() => {
    MockNotification.instances = [];
    MockNotification.requestPermission.mockClear();
    MockNotification.permission = 'granted';
    vi.stubGlobal('Notification', MockNotification);
    setVisibility('hidden');
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('fires a notification when a pending analysis completes in the background', () => {
    const { rerender } = renderForStatus('pending');
    rerender({ s: 'done' });

    expect(MockNotification.instances).toHaveLength(1);
    expect(MockNotification.instances[0].title).toBe('Análisis completado');
    expect(MockNotification.instances[0].options?.tag).toBe(
      'veritrust-analysis-abc'
    );
  });

  it('uses the failure copy when the analysis fails', () => {
    const { rerender } = renderForStatus('pending');
    rerender({ s: 'failed' });

    expect(MockNotification.instances).toHaveLength(1);
    expect(MockNotification.instances[0].title).toBe('El análisis ha fallado');
  });

  it('does not fire while the tab is in the foreground', () => {
    setVisibility('visible');
    const { rerender } = renderForStatus('pending');
    rerender({ s: 'done' });

    expect(MockNotification.instances).toHaveLength(0);
  });

  it('does not fire without a pending → completed transition', () => {
    renderForStatus('done');

    expect(MockNotification.instances).toHaveLength(0);
  });

  it('stays silent when permission is denied', () => {
    MockNotification.permission = 'default';
    const { rerender } = renderForStatus('pending');

    MockNotification.permission = 'denied';
    rerender({ s: 'done' });

    expect(MockNotification.instances).toHaveLength(0);
  });

  it('focuses the window when the notification is clicked', () => {
    const focusSpy = vi.spyOn(window, 'focus').mockImplementation(() => {});
    const { rerender } = renderForStatus('pending');
    rerender({ s: 'done' });

    MockNotification.instances[0].onclick?.();

    expect(focusSpy).toHaveBeenCalledTimes(1);
  });
});
