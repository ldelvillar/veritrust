import { mutate } from 'swr';
import { PENDING_HISTORY_PATH } from '@/lib/historyQuery';

const keyStartsWith = (prefix: string) => (key: unknown) =>
  typeof key === 'string' && key.startsWith(prefix);

// Refresh the indicator, and if its summary changes usePendingAnalyses refreshes the lists.
export function refreshPending(): Promise<unknown> {
  return mutate(PENDING_HISTORY_PATH);
}

let lastListsRefresh: Promise<unknown> | null = null;

// Refresh every cached /history list, the menu and the open History page.
export function refreshHistoryLists(): Promise<unknown> {
  lastListsRefresh = mutate(keyStartsWith('/history?'));
  return lastListsRefresh;
}

// After an own action, the lists are fetched here if the indicator did not see the change.
export async function refreshHistory(): Promise<unknown> {
  const before = lastListsRefresh;
  await refreshPending();
  return lastListsRefresh !== before ? lastListsRefresh : refreshHistoryLists();
}
