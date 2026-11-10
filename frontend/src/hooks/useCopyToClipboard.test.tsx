import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { useCopyToClipboard } from './useCopyToClipboard';

const writeText = vi.fn();

describe('useCopyToClipboard', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    writeText.mockReset();
    Object.defineProperty(navigator, 'clipboard', {
      value: { writeText },
      configurable: true,
    });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('writes the text, reports copied and returns to idle after 2 s', async () => {
    writeText.mockResolvedValueOnce(undefined);
    const { result } = renderHook(() => useCopyToClipboard());

    await act(() => result.current.copy('hola'));

    expect(writeText).toHaveBeenCalledWith('hola');
    expect(result.current.state).toBe('copied');

    act(() => vi.advanceTimersByTime(2000));
    expect(result.current.state).toBe('idle');
  });

  it('reports error when the clipboard rejects and still resets', async () => {
    writeText.mockRejectedValueOnce(new Error('denied'));
    const { result } = renderHook(() => useCopyToClipboard());

    await act(() => result.current.copy('hola'));
    expect(result.current.state).toBe('error');

    act(() => vi.advanceTimersByTime(2000));
    expect(result.current.state).toBe('idle');
  });

  it('restarts the timer when copying again', async () => {
    writeText.mockResolvedValue(undefined);
    const { result } = renderHook(() => useCopyToClipboard());

    await act(() => result.current.copy('a'));
    act(() => vi.advanceTimersByTime(1500));
    await act(() => result.current.copy('b'));
    act(() => vi.advanceTimersByTime(1500));

    expect(result.current.state).toBe('copied');
    act(() => vi.advanceTimersByTime(500));
    expect(result.current.state).toBe('idle');
  });

  it('reset returns to idle at once and cancels the pending timer', async () => {
    writeText.mockResolvedValueOnce(undefined);
    const { result } = renderHook(() => useCopyToClipboard());

    await act(() => result.current.copy('hola'));
    act(() => result.current.reset());

    expect(result.current.state).toBe('idle');
    expect(vi.getTimerCount()).toBe(0);
  });

  it('clears the pending timer on unmount', async () => {
    writeText.mockResolvedValueOnce(undefined);
    const { result, unmount } = renderHook(() => useCopyToClipboard());

    await act(() => result.current.copy('hola'));
    unmount();

    expect(vi.getTimerCount()).toBe(0);
  });
});
