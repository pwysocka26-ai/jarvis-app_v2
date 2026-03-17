import { apiGet, apiPost } from '@/src/api/client';

export type TimelineItem = {
  id: string;
  kind: 'event' | 'task' | 'focus' | 'break' | 'lunch';
  title: string;
  start: string;
  end: string;
  location?: string | null;
  category?: string | null;
  priority?: number | null;
};

export type DayPayload = {
  date: string;
  summary: { next_item?: string | null; next_time?: string | null; status: 'ok' | 'warning' | 'empty' };
  timeline: TimelineItem[];
  free_windows: { start: string; end: string }[];
  time_blocks: { start: string; end: string; label: string }[];
  priorities: { title: string; category: string; priority: number; time?: string | null; kind: 'event' | 'task' }[];
};

export type ActionResponse = { status: string; intent?: string; message: string; changed: boolean };

export const getToday = () => apiGet<DayPayload>('/mobile/today');
export const getTomorrow = () => apiGet<DayPayload>('/mobile/tomorrow');
export const getPrioritiesTomorrow = () => apiGet<{status: string; date: string; priorities: DayPayload['priorities']}>('/mobile/priorities/tomorrow');
export const createInboxItem = (text: string) => apiPost<ActionResponse>('/mobile/inbox', { text });
export const planTomorrow = () => apiPost<ActionResponse>('/mobile/plan/tomorrow');
