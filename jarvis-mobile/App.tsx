import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';

let AsyncStorage: any = null;
let Notifications: any = null;
let SpeechRecognitionModule: any = null;

try {
  AsyncStorage = require('@react-native-async-storage/async-storage').default;
} catch {}
try {
  Notifications = require('expo-notifications');
  Notifications?.setNotificationHandler?.({
    handleNotification: async () => ({
      shouldShowAlert: true,
      shouldPlaySound: true,
      shouldSetBadge: false,
      shouldShowBanner: true,
      shouldShowList: true,
    }),
  });
} catch {}
try {
  const speechPkg = require('expo-speech-recognition');
  SpeechRecognitionModule = speechPkg?.ExpoSpeechRecognitionModule || speechPkg?.default || speechPkg;
} catch {}

type TabKey = 'home' | 'chat' | 'plan' | 'brain' | 'inbox' | 'settings';
type PlanMode = 'today' | 'tomorrow';

type TimelineItem = {
  id: string;
  kind: 'event' | 'task' | 'focus' | 'break' | 'lunch';
  title: string;
  start: string;
  end: string;
  location?: string | null;
  category?: string | null;
  priority?: number | null;
};

type DayPayload = {
  date: string;
  summary: {
    next_item?: string | null;
    next_time?: string | null;
    status: 'ok' | 'warning' | 'empty';
  };
  timeline: TimelineItem[];
  free_windows: { start: string; end: string }[];
  time_blocks: { start: string; end: string; label: string }[];
  priorities: { title: string; category: string; priority: number; time?: string | null; kind: 'event' | 'task' }[];
};

type ActionResponse = { status: string; intent?: string; message: string; changed: boolean };
type MemoryResponse = { status: string; message?: string };
type ChatMessage = { id: string; role: 'user' | 'assistant'; text: string; intent?: string | null };
type HealthResponse = { status: string; product: string; version: string };

type BrainNote = {
  id: string;
  title: string;
  text: string;
  tags: string[];
  createdAt: string;
  source: 'chat' | 'voice' | 'inbox' | 'manual';
  pinned?: boolean;
};

type SettingsState = {
  apiBase: string;
  apiToken: string;
  notificationsEnabled: boolean;
  voiceAutoSend: boolean;
  autoplanAfterInbox: boolean;
};

type VoiceState = {
  listening: boolean;
  liveText: string;
  error: string;
};

const STORAGE_KEY = 'jarvis-mobile-v5-settings';
const BRAIN_NOTES_KEY = 'jarvis-mobile-v5-brain-notes';
const REQUEST_TIMEOUT_MS = 9000;
const JARVIS_NOTIFICATION_PREFIX = 'jarvis-mobile-';

const colors = {
  bg: '#0B1020',
  surface: '#121A2C',
  card: '#172033',
  card2: '#1E293B',
  text: '#F8FAFC',
  muted: '#94A3B8',
  border: '#23304A',
  primary: '#60A5FA',
  primaryStrong: '#2563EB',
  good: '#34D399',
  warning: '#FBBF24',
  danger: '#F87171',
  chip: '#111827',
};

const EMPTY_DAY: DayPayload = {
  date: '',
  summary: { status: 'empty', next_item: null, next_time: null },
  timeline: [],
  free_windows: [],
  time_blocks: [],
  priorities: [],
};

const DEFAULT_SETTINGS: SettingsState = {
  apiBase: 'http://192.168.8.118:8011',
  apiToken: '',
  notificationsEnabled: true,
  voiceAutoSend: false,
  autoplanAfterInbox: false,
};

const QUICK_CAPTURE = [
  'jutro 9:00 dentysta',
  'dziś 18:00 zakupy',
  'jutro 8:30 wyślij CV',
  'jutro 19:00 oddzwoń do mamy',
];
const QUICK_CHAT = ['Co mam dziś najważniejsze?', 'Pokaż listę na jutro', 'Zaplanuj mi jutro', 'Co o mnie pamiętasz?'];

function uid(prefix: string) {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

function normalizeBaseUrl(value: string) {
  return value.trim().replace(/\/+$/, '');
}

function buildHeaders(settings: SettingsState) {
  const headers: Record<string, string> = {};
  if (settings.apiToken.trim()) headers['X-API-Token'] = settings.apiToken.trim();
  return headers;
}

function humanizeFetchError(error: unknown) {
  const message = error instanceof Error ? error.message : String(error || 'Nieznany błąd');
  if (message.includes('timeout')) return 'Backend nie odpowiedział w 9 sekund. Sprawdź serwer i Wi‑Fi.';
  if (message.includes('Network request failed') || message.includes('fetch')) return 'Telefon nie może połączyć się z backendem. Sprawdź IP, to samo Wi‑Fi i firewall.';
  return message;
}

async function fetchWithTimeout(url: string, options?: RequestInit): Promise<Response> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  try {
    return await fetch(url, { ...options, signal: controller.signal });
  } catch (error) {
    if ((error as Error)?.name === 'AbortError') throw new Error('timeout');
    throw error;
  } finally {
    clearTimeout(timer);
  }
}

async function parseApiResponse<T>(response: Response): Promise<T> {
  const raw = await response.text().catch(() => '');
  const contentType = response.headers.get('content-type') || '';
  if (!response.ok) throw new Error(raw.trim().slice(0, 180) || `HTTP ${response.status}`);
  if (!raw.trim()) return {} as T;
  if (contentType.includes('application/json')) return JSON.parse(raw) as T;
  const trimmed = raw.trim();
  if (trimmed.startsWith('{') || trimmed.startsWith('[')) return JSON.parse(trimmed) as T;
  if (trimmed.startsWith('<')) throw new Error('Backend zwrócił HTML zamiast JSON. Sprawdź adres backendu.');
  throw new Error(trimmed.slice(0, 180) || 'Nieznana odpowiedź backendu.');
}

async function apiGet<T>(settings: SettingsState, path: string): Promise<T> {
  try {
    const response = await fetchWithTimeout(`${normalizeBaseUrl(settings.apiBase)}${path}`, { headers: buildHeaders(settings) });
    return await parseApiResponse<T>(response);
  } catch (error) {
    throw new Error(humanizeFetchError(error));
  }
}

async function apiPost<T>(settings: SettingsState, path: string, body?: unknown): Promise<T> {
  try {
    const response = await fetchWithTimeout(`${normalizeBaseUrl(settings.apiBase)}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...buildHeaders(settings) },
      body: body ? JSON.stringify(body) : undefined,
    });
    return await parseApiResponse<T>(response);
  } catch (error) {
    throw new Error(humanizeFetchError(error));
  }
}

function formatDayLabel(iso: string) {
  return iso || 'brak daty';
}

function statusColor(status?: string) {
  if (status === 'ok') return colors.good;
  if (status === 'warning') return colors.warning;
  return colors.muted;
}

function summarizeDay(payload: DayPayload, title: string) {
  const rows = payload.timeline.length
    ? payload.timeline.slice(0, 6).map((item) => `• ${item.start} ${item.title}`).join('\n')
    : 'Brak pozycji.';
  return `${title}\nData: ${payload.date || 'brak'}\nNajbliższy punkt: ${payload.summary.next_item || 'brak'}${payload.summary.next_time ? ` o ${payload.summary.next_time}` : ''}\n\n${rows}`;
}

function summarizePriorities(items: DayPayload['priorities']) {
  if (!items.length) return 'Brak priorytetów jutra.';
  return items.slice(0, 6).map((item) => `• P${item.priority} ${item.time || 'bez godziny'} — ${item.title} (${item.category})`).join('\n');
}

function parseTags(value: string) {
  return value
    .split(/[,#]/)
    .map((tag) => tag.trim().toLowerCase())
    .filter(Boolean)
    .slice(0, 6);
}

function notePreview(note: BrainNote) {
  return note.text.length > 120 ? `${note.text.slice(0, 120)}…` : note.text;
}

function createBrainNote(input: { title?: string; text: string; tags?: string[]; source?: BrainNote['source']; pinned?: boolean }): BrainNote {
  const text = input.text.trim();
  const title = (input.title || text.split(/[.!?\n]/)[0] || 'Nowa myśl').trim();
  return {
    id: uid('brain'),
    title: title.slice(0, 80),
    text,
    tags: (input.tags || []).filter(Boolean),
    createdAt: new Date().toISOString(),
    source: input.source || 'manual',
    pinned: input.pinned || false,
  };
}

async function runChatIntent(settings: SettingsState, text: string): Promise<{ reply: string; intent?: string | null }> {
  const lower = text.trim().toLowerCase();
  if (!lower) return { reply: 'Napisz do Jarvisa dowolne polecenie.' };

  if (lower.includes('co o mnie pamiętasz') || lower.includes('co o mnie wiesz') || lower.includes('pamiętasz')) {
    const memory = await apiGet<MemoryResponse>(settings, '/mobile/memory');
    return { reply: memory.message || 'Brak pamięci do wyświetlenia.', intent: 'memory' };
  }
  if (lower.includes('zaplanuj') && lower.includes('jutro')) {
    const result = await apiPost<ActionResponse>(settings, '/mobile/plan/tomorrow');
    return { reply: result.message || 'Plan jutra został zaktualizowany.', intent: result.intent || 'plan_tomorrow' };
  }
  if (lower.includes('priorytet') || lower.includes('najważniejsze jutro') || (lower.includes('jutro') && lower.includes('najważniejsze'))) {
    const result = await apiGet<{ status: string; date: string; priorities: DayPayload['priorities'] }>(settings, '/mobile/priorities/tomorrow');
    return { reply: `Top priorytety na jutro (${result.date}):\n\n${summarizePriorities(result.priorities || [])}`, intent: 'priorities_tomorrow' };
  }
  if (lower.includes('lista na jutro') || lower.includes('pokaż listę na jutro') || lower.includes('co mam jutro') || lower === 'jutro') {
    const result = await apiGet<DayPayload>(settings, '/mobile/tomorrow');
    return { reply: summarizeDay(result, 'Plan na jutro'), intent: 'tomorrow' };
  }
  if (lower.includes('co mam dziś') || lower.includes('co mam dzis') || lower.includes('najważniejsze dziś') || lower.includes('plan dnia') || lower === 'dziś' || lower === 'dzis') {
    const result = await apiGet<DayPayload>(settings, '/mobile/today');
    return { reply: summarizeDay(result, 'Plan na dziś'), intent: 'today' };
  }

  const inboxResult = await apiPost<ActionResponse>(settings, '/mobile/inbox', { text });
  return { reply: inboxResult.message || 'Dodano do inboxa.', intent: inboxResult.intent || 'inbox' };
}

function toDateFromDayAndTime(dayIso: string, timeText: string) {
  if (!dayIso || !timeText || !/^\d{2}:\d{2}$/.test(timeText)) return null;
  const [year, month, day] = dayIso.split('-').map(Number);
  const [hours, minutes] = timeText.split(':').map(Number);
  if (![year, month, day, hours, minutes].every((x) => Number.isFinite(x))) return null;
  return new Date(year, month - 1, day, hours, minutes, 0, 0);
}

async function ensureNotificationPermission() {
  if (!Notifications) throw new Error('Pakiet expo-notifications nie jest dostępny.');
  const existing = await Notifications.getPermissionsAsync?.();
  let granted = existing?.granted || existing?.ios?.status === Notifications.IosAuthorizationStatus?.AUTHORIZED;
  if (!granted) {
    const request = await Notifications.requestPermissionsAsync?.();
    granted = request?.granted || request?.ios?.status === Notifications.IosAuthorizationStatus?.AUTHORIZED;
  }
  if (!granted) throw new Error('Brak zgody na powiadomienia.');
  if (Platform.OS === 'android') {
    await Notifications.setNotificationChannelAsync?.('jarvis-reminders', {
      name: 'Jarvis reminders',
      importance: Notifications.AndroidImportance?.MAX ?? 5,
      vibrationPattern: [0, 200, 100, 200],
      lightColor: '#2563EB',
    });
  }
}

async function clearJarvisNotifications() {
  if (!Notifications?.getAllScheduledNotificationsAsync) return;
  const scheduled = await Notifications.getAllScheduledNotificationsAsync();
  for (const item of scheduled) {
    if (String(item?.content?.data?.jarvisKey || '').startsWith(JARVIS_NOTIFICATION_PREFIX)) {
      await Notifications.cancelScheduledNotificationAsync?.(item.identifier);
    }
  }
}

async function scheduleTimelineNotifications(dayIso: string, items: TimelineItem[]) {
  if (!Notifications) throw new Error('Pakiet expo-notifications nie jest dostępny.');
  await ensureNotificationPermission();
  const now = Date.now();
  let count = 0;
  for (const item of items) {
    const startAt = toDateFromDayAndTime(dayIso, item.start);
    if (!startAt) continue;
    const notifyAt = new Date(startAt.getTime() - 15 * 60 * 1000);
    if (notifyAt.getTime() <= now + 5000) continue;
    count += 1;
    await Notifications.scheduleNotificationAsync?.({
      content: {
        title: 'Jarvis przypomina',
        body: `${item.start} • ${item.title}${item.location ? ` • ${item.location}` : ''}`,
        data: { jarvisKey: `${JARVIS_NOTIFICATION_PREFIX}${dayIso}-${item.id}`, itemId: item.id },
        sound: true,
      },
      trigger: Platform.OS === 'android'
        ? { channelId: 'jarvis-reminders', type: Notifications.SchedulableTriggerInputTypes?.DATE, date: notifyAt }
        : { type: Notifications.SchedulableTriggerInputTypes?.DATE, date: notifyAt },
    });
  }
  return count;
}

async function saveSettings(next: SettingsState) {
  if (!AsyncStorage) return;
  try { await AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(next)); } catch {}
}

async function loadSavedSettings(): Promise<SettingsState | null> {
  if (!AsyncStorage) return null;
  try {
    const raw = await AsyncStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    return { ...DEFAULT_SETTINGS, ...JSON.parse(raw) };
  } catch {
    return null;
  }
}

async function loadBrainNotes(): Promise<BrainNote[]> {
  if (!AsyncStorage) return [];
  try {
    const raw = await AsyncStorage.getItem(BRAIN_NOTES_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

async function saveBrainNotes(notes: BrainNote[]) {
  if (!AsyncStorage) return;
  try { await AsyncStorage.setItem(BRAIN_NOTES_KEY, JSON.stringify(notes)); } catch {}
}

async function startVoiceCapture(options: {
  onStart?: () => void;
  onPartial?: (text: string) => void;
  onResult: (text: string) => void;
  onError: (message: string) => void;
  onEnd?: () => void;
}) {
  if (!SpeechRecognitionModule) {
    options.onError('Ten build nie ma jeszcze natywnego modułu voice capture. Uruchom development build przez npx expo run:android.');
    return () => {};
  }
  if (typeof SpeechRecognitionModule.isRecognitionAvailable === 'function' && !SpeechRecognitionModule.isRecognitionAvailable()) {
    options.onError('Rozpoznawanie mowy nie jest dostępne na tym urządzeniu albo usługa rozpoznawania jest wyłączona.');
    return () => {};
  }

  const subscriptions: Array<{ remove?: () => void } | undefined> = [];
  let finished = false;

  const cleanup = (shouldStop = true) => {
    if (finished) return;
    finished = true;
    for (const sub of subscriptions) {
      try { sub?.remove?.(); } catch {}
    }
    if (shouldStop) {
      try { SpeechRecognitionModule.stop?.(); } catch {}
    }
  };

  try {
    const permissionResult = await (SpeechRecognitionModule.requestPermissionsAsync?.() ?? SpeechRecognitionModule.requestMicrophonePermissionsAsync?.());
    if (permissionResult && permissionResult.granted === false) {
      options.onError('Brak zgody na mikrofon lub rozpoznawanie mowy. Nadaj uprawnienia w telefonie i spróbuj ponownie.');
      return () => {};
    }

    const partialHandler = (event: any) => {
      const transcript = event?.results?.[0]?.transcript || event?.transcript || '';
      if (transcript) options.onPartial?.(String(transcript));
    };
    const resultHandler = (event: any) => {
      const transcript =
        event?.results?.[0]?.transcript ||
        event?.result ||
        event?.transcript ||
        (Array.isArray(event?.results) ? event.results.map((x: any) => x?.transcript || x).join(' ') : '');
      if (transcript) {
        options.onResult(String(transcript));
        cleanup(true);
      }
    };
    const errorHandler = (event: any) => {
      const code = String(event?.error || '').toLowerCase();
      if (code === 'aborted') {
        cleanup(false);
        options.onEnd?.();
        return;
      }
      options.onError(String(event?.message || event?.error || 'Błąd rozpoznawania mowy.'));
      cleanup(false);
    };
    const endHandler = () => {
      cleanup(false);
      options.onEnd?.();
    };
    const noMatchHandler = () => {
      options.onError('Nie udało się rozpoznać wypowiedzi. Spróbuj jeszcze raz i mów trochę wolniej.');
      cleanup(false);
    };

    subscriptions.push(SpeechRecognitionModule.addListener?.('start', options.onStart));
    subscriptions.push(SpeechRecognitionModule.addListener?.('audiostart', options.onStart));
    subscriptions.push(SpeechRecognitionModule.addListener?.('volumechange', partialHandler));
    subscriptions.push(SpeechRecognitionModule.addListener?.('result', resultHandler));
    subscriptions.push(SpeechRecognitionModule.addListener?.('partialresult', partialHandler));
    subscriptions.push(SpeechRecognitionModule.addListener?.('error', errorHandler));
    subscriptions.push(SpeechRecognitionModule.addListener?.('end', endHandler));
    subscriptions.push(SpeechRecognitionModule.addListener?.('nomatch', noMatchHandler));

    await SpeechRecognitionModule.start?.({
      lang: 'pl-PL',
      interimResults: true,
      continuous: false,
      maxAlternatives: 1,
      requiresOnDeviceRecognition: false,
    });

    return () => cleanup(true);
  } catch (error) {
    cleanup(false);
    options.onError(humanizeFetchError(error));
    return () => {};
  }
}

function SectionCard({ title, subtitle, right, children }: { title: string; subtitle?: string; right?: React.ReactNode; children: React.ReactNode }) {
  return (
    <View style={styles.card}>
      <View style={styles.sectionTop}>
        <View style={styles.sectionTopText}>
          <Text style={styles.sectionTitle}>{title}</Text>
          {subtitle ? <Text style={styles.sectionSubtitle}>{subtitle}</Text> : null}
        </View>
        {right ? <View>{right}</View> : null}
      </View>
      {children}
    </View>
  );
}

function Chip({ text, active = false, danger = false }: { text: string; active?: boolean; danger?: boolean }) {
  return <View style={[styles.chip, active && styles.chipActive, danger && styles.chipDanger]}><Text style={[styles.chipText, active && styles.chipTextActive, danger && styles.chipTextDanger]}>{text}</Text></View>;
}

function MiniStat({ label, value, accent }: { label: string; value: string; accent?: string }) {
  return <View style={styles.miniStat}><Text style={[styles.miniStatValue, accent ? { color: accent } : null]}>{value}</Text><Text style={styles.miniStatLabel}>{label}</Text></View>;
}

function ToggleCard({ label, value, onPress }: { label: string; value: boolean; onPress: () => void }) {
  return (
    <Pressable style={[styles.toggleCard, value && styles.toggleCardActive]} onPress={onPress}>
      <Text style={styles.toggleLabel}>{label}</Text>
      <Chip text={value ? 'ON' : 'OFF'} active={value} />
    </Pressable>
  );
}

function TimelineList({ items, emptyText }: { items: TimelineItem[]; emptyText: string }) {
  if (!items.length) return <Text style={styles.emptyText}>{emptyText}</Text>;
  return (
    <View style={styles.columnGap}>
      {items.map((item) => (
        <View key={item.id} style={styles.timelineRow}>
          <View style={styles.timelineTimeBlock}>
            <Text style={styles.timelineTime}>{item.start}</Text>
            <Text style={styles.timelineTimeEnd}>{item.end}</Text>
          </View>
          <View style={[styles.timelineDot, item.kind === 'focus' ? styles.focusDot : item.kind === 'lunch' ? styles.lunchDot : null]} />
          <View style={styles.timelineBody}>
            <Text style={styles.timelineTitle}>{item.title}</Text>
            <Text style={styles.timelineMeta}>{[item.kind, item.category, item.location].filter(Boolean).join(' • ') || 'bez szczegółów'}</Text>
          </View>
        </View>
      ))}
    </View>
  );
}

function PriorityList({ items, emptyText }: { items: DayPayload['priorities']; emptyText: string }) {
  if (!items.length) return <Text style={styles.emptyText}>{emptyText}</Text>;
  return (
    <View style={styles.columnGap}>
      {items.map((item, index) => (
        <View key={`${item.title}-${index}`} style={styles.priorityRow}>
          <View style={styles.priorityBadge}><Text style={styles.priorityBadgeText}>P{item.priority}</Text></View>
          <View style={styles.priorityBody}>
            <Text style={styles.priorityTitle}>{item.title}</Text>
            <Text style={styles.priorityMeta}>{[item.time || 'bez godziny', item.category, item.kind].filter(Boolean).join(' • ')}</Text>
          </View>
        </View>
      ))}
    </View>
  );
}

function QuickPromptRow({ items, onPress }: { items: string[]; onPress: (value: string) => void }) {
  return (
    <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.quickRow}>
      {items.map((item) => (
        <Pressable key={item} style={styles.quickButton} onPress={() => onPress(item)}><Text style={styles.quickButtonText}>{item}</Text></Pressable>
      ))}
    </ScrollView>
  );
}

function VoicePill({ voiceState }: { voiceState: VoiceState }) {
  if (!voiceState.listening && !voiceState.liveText && !voiceState.error) return null;
  return (
    <View style={[styles.voiceLiveCard, voiceState.error ? styles.voiceLiveCardError : null]}>
      <Text style={styles.voiceLiveTitle}>{voiceState.listening ? '🎤 Słucham...' : voiceState.error ? 'Błąd voice capture' : 'Transkrypcja'}</Text>
      <Text style={styles.voiceLiveText}>{voiceState.error || voiceState.liveText || 'Powiedz komendę do Jarvisa.'}</Text>
    </View>
  );
}

function NoteList({ notes, onTogglePin, onDelete }: { notes: BrainNote[]; onTogglePin: (id: string) => void; onDelete: (id: string) => void }) {
  if (!notes.length) return <Text style={styles.emptyText}>Brak zapisanych myśli. Dodaj pierwszą notatkę z Brain, Chatu albo Inboxa.</Text>;
  return (
    <View style={styles.columnGap}>
      {notes.map((note) => (
        <View key={note.id} style={styles.noteCard}>
          <View style={styles.noteTopRow}>
            <View style={{ flex: 1 }}>
              <Text style={styles.noteTitle}>{note.title}</Text>
              <Text style={styles.noteMeta}>{new Date(note.createdAt).toLocaleString('pl-PL')} • {note.source}</Text>
            </View>
            {note.pinned ? <Chip text="PIN" active /> : null}
          </View>
          <Text style={styles.noteText}>{notePreview(note)}</Text>
          <View style={styles.noteTagsWrap}>
            {note.tags.map((tag) => <Chip key={`${note.id}-${tag}`} text={`#${tag}`} />)}
          </View>
          <View style={styles.inlineActionsWrap}>
            <Pressable style={styles.secondaryButton} onPress={() => onTogglePin(note.id)}><Text style={styles.secondaryButtonText}>{note.pinned ? 'Odepnij' : 'Przypnij'}</Text></Pressable>
            <Pressable style={styles.secondaryDangerButton} onPress={() => onDelete(note.id)}><Text style={styles.secondaryDangerButtonText}>Usuń</Text></Pressable>
          </View>
        </View>
      ))}
    </View>
  );
}

function HomeScreen({
  settings,
  notes,
  onOpenTab,
  onUseCapture,
  onUseChat,
  onQuickPlan,
}: {
  settings: SettingsState;
  notes: BrainNote[];
  onOpenTab: (tab: TabKey) => void;
  onUseCapture: (value: string) => void;
  onUseChat: (value: string) => void;
  onQuickPlan: () => void;
}) {
  const [today, setToday] = useState<DayPayload>(EMPTY_DAY);
  const [tomorrow, setTomorrow] = useState<DayPayload>(EMPTY_DAY);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const pinned = useMemo(() => notes.filter((n) => n.pinned).slice(0, 2), [notes]);

  const load = useCallback(async () => {
    setLoading(true); setError('');
    try {
      const [healthData, todayData, tomorrowData] = await Promise.all([
        apiGet<HealthResponse>(settings, '/mobile/health'),
        apiGet<DayPayload>(settings, '/mobile/today'),
        apiGet<DayPayload>(settings, '/mobile/tomorrow'),
      ]);
      setHealth(healthData); setToday(todayData); setTomorrow(tomorrowData);
    } catch (err) { setError(humanizeFetchError(err)); }
    finally { setLoading(false); }
  }, [settings]);

  useEffect(() => { load(); }, [load]);

  return (
    <ScrollView style={styles.screenFill} contentContainerStyle={styles.screenContent}>
      <View style={styles.heroCard}>
        <Text style={styles.heroEyebrow}>Jarvis Mobile v5</Text>
        <Text style={styles.heroTitle}>REAL Second Brain</Text>
        <Text style={styles.heroText}>Organizer, AI planner dnia, pamięć, priorytety, voice capture i lokalny second brain w jednym stabilnym ekranie mobilnym.</Text>
        <View style={styles.heroStats}>
          <MiniStat label="status" value={health?.status || '—'} accent={statusColor(health?.status)} />
          <MiniStat label="dziś" value={String(today.timeline.length)} />
          <MiniStat label="brain" value={String(notes.length)} />
        </View>
      </View>

      <SectionCard title="Co teraz najważniejsze?" subtitle="centrum dowodzenia dla Twojego dnia" right={loading ? <ActivityIndicator color={colors.primary} /> : null}>
        {error ? <Text style={styles.errorText}>{error}</Text> : null}
        <Text style={styles.homeFocusTitle}>{today.summary.next_item || 'Brak pozycji do pokazania'}</Text>
        <Text style={styles.homeFocusMeta}>Najbliższy punkt: {today.summary.next_time || '—'} • {formatDayLabel(today.date)}</Text>
        <View style={styles.inlineActionsWrap}>
          <Pressable style={styles.primaryButton} onPress={onQuickPlan}><Text style={styles.primaryButtonText}>AI planner jutra</Text></Pressable>
          <Pressable style={styles.secondaryButton} onPress={() => onOpenTab('plan')}><Text style={styles.secondaryButtonText}>Plan dnia</Text></Pressable>
          <Pressable style={styles.secondaryButton} onPress={() => onOpenTab('brain')}><Text style={styles.secondaryButtonText}>Otwórz Brain</Text></Pressable>
        </View>
      </SectionCard>

      <SectionCard title="Szybki start" subtitle="najkrótsze drogi do działania">
        <View style={styles.grid2}>
          <Pressable style={styles.featureTile} onPress={() => onOpenTab('chat')}>
            <Text style={styles.featureTitle}>AI Chat</Text>
            <Text style={styles.featureText}>Pytaj Jarvisa o plan dnia, priorytety i pamięć.</Text>
          </Pressable>
          <Pressable style={styles.featureTile} onPress={() => onOpenTab('inbox')}>
            <Text style={styles.featureTitle}>Voice Inbox</Text>
            <Text style={styles.featureText}>Mów naturalnie: „jutro 9 dentysta”.</Text>
          </Pressable>
          <Pressable style={styles.featureTile} onPress={() => onUseCapture('pomysł: usprawnić onboarding Jarvisa')}>
            <Text style={styles.featureTitle}>Capture myśli</Text>
            <Text style={styles.featureText}>Wrzuć pomysł do Inboxa albo do Brain.</Text>
          </Pressable>
          <Pressable style={styles.featureTile} onPress={() => onUseChat('Co mam dziś najważniejsze?')}>
            <Text style={styles.featureTitle}>Focus na dziś</Text>
            <Text style={styles.featureText}>Jarvis zbierze plan dnia w jednym miejscu.</Text>
          </Pressable>
        </View>
      </SectionCard>

      <SectionCard title="Top priorytety jutra" subtitle={formatDayLabel(tomorrow.date)}>
        <PriorityList items={tomorrow.priorities} emptyText="Brak priorytetów jutra." />
      </SectionCard>

      <SectionCard title="Pinned brain" subtitle="najważniejsze notatki drugiego mózgu" right={<Chip text={`${notes.length} notatek`} active />}>
        {pinned.length ? <NoteList notes={pinned} onTogglePin={() => {}} onDelete={() => {}} /> : <Text style={styles.emptyText}>Przypnij ważne notatki w zakładce Brain, żeby zawsze były pod ręką.</Text>}
      </SectionCard>
    </ScrollView>
  );
}

function ChatScreen({
  settings,
  seedMessage,
  onMessageConsumed,
  notes,
  onAddBrainNote,
}: {
  settings: SettingsState;
  seedMessage: string | null;
  onMessageConsumed: () => void;
  notes: BrainNote[];
  onAddBrainNote: (note: BrainNote) => void;
}) {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: uid('msg'),
      role: 'assistant',
      text: 'Jarvis Mobile v5 gotowy. Pytaj o plan, priorytety, pamięć, a ważne odpowiedzi zapisuj do Brain.',
      intent: 'welcome',
    },
  ]);
  const [text, setText] = useState('');
  const [sending, setSending] = useState(false);
  const [voiceState, setVoiceState] = useState<VoiceState>({ listening: false, liveText: '', error: '' });
  const stopVoiceRef = useRef<null | (() => void)>(null);

  const pinnedHint = useMemo(() => notes.filter((n) => n.pinned).slice(0, 2).map((n) => n.title).join(' • '), [notes]);

  useEffect(() => {
    if (seedMessage) {
      setText(seedMessage);
      onMessageConsumed();
    }
  }, [seedMessage, onMessageConsumed]);

  useEffect(() => () => { stopVoiceRef.current?.(); }, []);

  const send = useCallback(async (raw?: string) => {
    const message = (raw ?? text).trim();
    if (!message) return;
    const userMessage: ChatMessage = { id: uid('msg'), role: 'user', text: message };
    setMessages((prev) => [...prev, userMessage]);
    setText('');
    setSending(true);
    try {
      const result = await runChatIntent(settings, message);
      const assistantMessage: ChatMessage = { id: uid('msg'), role: 'assistant', text: result.reply, intent: result.intent };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err) {
      setMessages((prev) => [...prev, { id: uid('msg'), role: 'assistant', text: humanizeFetchError(err), intent: 'error' }]);
    } finally { setSending(false); }
  }, [settings, text]);

  const saveLastAssistantToBrain = useCallback(() => {
    const lastAssistant = [...messages].reverse().find((item) => item.role === 'assistant');
    if (!lastAssistant) {
      Alert.alert('Jarvis', 'Najpierw uzyskaj odpowiedź od Jarvisa.');
      return;
    }
    const note = createBrainNote({ title: `Chat: ${lastAssistant.intent || 'odpowiedź'}`, text: lastAssistant.text, source: 'chat', tags: ['chat', lastAssistant.intent || 'jarvis'] });
    onAddBrainNote(note);
    Alert.alert('Jarvis', 'Ostatnia odpowiedź została zapisana do Brain.');
  }, [messages, onAddBrainNote]);

  const startVoice = useCallback(async () => {
    if (voiceState.listening) {
      stopVoiceRef.current?.();
      stopVoiceRef.current = null;
      setVoiceState({ listening: false, liveText: '', error: '' });
      return;
    }
    setVoiceState({ listening: true, liveText: '', error: '' });
    stopVoiceRef.current = await startVoiceCapture({
      onStart: () => setVoiceState({ listening: true, liveText: '', error: '' }),
      onPartial: (value) => setVoiceState((prev) => ({ ...prev, liveText: value, error: '' })),
      onResult: (value) => {
        setVoiceState({ listening: false, liveText: value, error: '' });
        setText(value);
        send(value);
      },
      onError: (message) => setVoiceState({ listening: false, liveText: '', error: message }),
      onEnd: () => setVoiceState((prev) => ({ ...prev, listening: false })),
    });
  }, [send, voiceState.listening]);

  return (
    <KeyboardAvoidingView style={styles.screenFill} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <ScrollView style={styles.screenFill} contentContainerStyle={styles.screenContent}>
        <Text style={styles.h1}>Chat</Text>
        <Text style={styles.sub}>AI chat z kontekstem dnia, priorytetami i możliwością zapisu odpowiedzi do Brain.</Text>
        {pinnedHint ? <Text style={styles.helperText}>Pinned context: {pinnedHint}</Text> : null}
        <QuickPromptRow items={QUICK_CHAT} onPress={setText} />
        <VoicePill voiceState={voiceState} />
        <SectionCard title="Rozmowa" subtitle="pisz albo mów do Jarvisa" right={sending ? <ActivityIndicator color={colors.primary} /> : null}>
          <View style={styles.columnGap}>
            {messages.map((item) => (
              <View key={item.id} style={item.role === 'assistant' ? styles.chatBubbleAssistant : styles.chatBubbleUser}>
                <Text style={item.role === 'assistant' ? styles.chatRoleAssistant : styles.chatRoleUser}>{item.role === 'assistant' ? 'Jarvis' : 'Ty'}</Text>
                <Text style={item.role === 'assistant' ? styles.chatTextAssistant : styles.chatTextUser}>{item.text}</Text>
                {item.intent ? <Text style={styles.intentText}>intent: {item.intent}</Text> : null}
              </View>
            ))}
          </View>
        </SectionCard>
      </ScrollView>

      <View style={styles.composerWrap}>
        <TextInput
          value={text}
          onChangeText={setText}
          placeholder="Napisz do Jarvisa..."
          placeholderTextColor={colors.muted}
          multiline
          style={styles.composerInput}
        />
        <View style={styles.inlineActionsWrap}>
          <Pressable style={styles.primaryButton} onPress={() => send()}><Text style={styles.primaryButtonText}>{sending ? 'Wysyłanie...' : 'Wyślij'}</Text></Pressable>
          <Pressable style={[styles.voiceButton, voiceState.listening && styles.voiceButtonActive]} onPress={startVoice}><Text style={styles.voiceButtonText}>{voiceState.listening ? '⏹ Stop' : '🎤 Mów'}</Text></Pressable>
          <Pressable style={styles.secondaryButton} onPress={saveLastAssistantToBrain}><Text style={styles.secondaryButtonText}>Zapisz do Brain</Text></Pressable>
        </View>
      </View>
    </KeyboardAvoidingView>
  );
}

function PlanScreen({ settings, notificationsEnabled }: { settings: SettingsState; notificationsEnabled: boolean }) {
  const [mode, setMode] = useState<PlanMode>('today');
  const [today, setToday] = useState<DayPayload>(EMPTY_DAY);
  const [tomorrow, setTomorrow] = useState<DayPayload>(EMPTY_DAY);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const activePayload = mode === 'today' ? today : tomorrow;

  const load = useCallback(async () => {
    setLoading(true); setError(''); setMessage('');
    try {
      const [todayData, tomorrowData] = await Promise.all([
        apiGet<DayPayload>(settings, '/mobile/today'),
        apiGet<DayPayload>(settings, '/mobile/tomorrow'),
      ]);
      setToday(todayData); setTomorrow(tomorrowData);
    } catch (err) {
      setError(humanizeFetchError(err));
    } finally {
      setLoading(false);
    }
  }, [settings]);

  useEffect(() => { load(); }, [load]);

  const planTomorrow = useCallback(async () => {
    setLoading(true); setError(''); setMessage('');
    try {
      const result = await apiPost<ActionResponse>(settings, '/mobile/plan/tomorrow');
      const tomorrowData = await apiGet<DayPayload>(settings, '/mobile/tomorrow');
      setTomorrow(tomorrowData);
      let note = result.message || 'Plan jutra został zaktualizowany.';
      if (notificationsEnabled) {
        await clearJarvisNotifications();
        const count = await scheduleTimelineNotifications(tomorrowData.date, tomorrowData.timeline);
        note += count ? ` Przypomnienia: ${count}.` : ' Brak przyszłych przypomnień do ustawienia.';
      }
      setMode('tomorrow');
      setMessage(note);
    } catch (err) { setError(humanizeFetchError(err)); }
    finally { setLoading(false); }
  }, [notificationsEnabled, settings]);

  return (
    <ScrollView style={styles.screenFill} contentContainerStyle={styles.screenContent}>
      <Text style={styles.h1}>Plan dnia</Text>
      <Text style={styles.sub}>Timeline, wolne okna, AI planner jutra i lokalne przypomnienia 15 minut przed wydarzeniem.</Text>

      <View style={styles.segmentWrap}>
        <Pressable style={[styles.segmentButton, mode === 'today' && styles.segmentButtonActive]} onPress={() => setMode('today')}><Text style={[styles.segmentText, mode === 'today' && styles.segmentTextActive]}>Dziś</Text></Pressable>
        <Pressable style={[styles.segmentButton, mode === 'tomorrow' && styles.segmentButtonActive]} onPress={() => setMode('tomorrow')}><Text style={[styles.segmentText, mode === 'tomorrow' && styles.segmentTextActive]}>Jutro</Text></Pressable>
      </View>

      <View style={styles.inlineActionsWrap}>
        <Pressable style={styles.primaryButton} onPress={load}><Text style={styles.primaryButtonText}>{loading ? 'Odświeżam...' : 'Odśwież'}</Text></Pressable>
        <Pressable style={styles.secondaryButton} onPress={planTomorrow}><Text style={styles.secondaryButtonText}>AI planner jutra</Text></Pressable>
      </View>

      {message ? <Text style={styles.okText}>{message}</Text> : null}
      {error ? <Text style={styles.errorText}>{error}</Text> : null}

      <SectionCard title={mode === 'today' ? 'Dziś' : 'Jutro'} subtitle={formatDayLabel(activePayload.date)} right={loading ? <ActivityIndicator color={colors.primary} /> : null}>
        <Text style={styles.homeFocusTitle}>{activePayload.summary.next_item || 'Brak pozycji do pokazania'}</Text>
        <Text style={styles.homeFocusMeta}>Najbliższy punkt: {activePayload.summary.next_time || '—'}</Text>
      </SectionCard>

      <SectionCard title="Timeline" subtitle="kalendarz + zadania + focus/lunch">
        <TimelineList items={activePayload.timeline} emptyText="Brak elementów w planie." />
      </SectionCard>

      <SectionCard title="Wolne okna">
        <Text style={styles.infoLine}>{activePayload.free_windows.length ? activePayload.free_windows.map((x) => `${x.start}–${x.end}`).join('  |  ') : 'Brak wolnych okien.'}</Text>
      </SectionCard>

      <SectionCard title="Priorytety w planie">
        <PriorityList items={activePayload.priorities} emptyText="Brak priorytetów do pokazania." />
      </SectionCard>
    </ScrollView>
  );
}

function BrainScreen({
  settings,
  notes,
  onAddBrainNote,
  onDeleteNote,
  onTogglePin,
}: {
  settings: SettingsState;
  notes: BrainNote[];
  onAddBrainNote: (note: BrainNote) => void;
  onDeleteNote: (id: string) => void;
  onTogglePin: (id: string) => void;
}) {
  const [memoryText, setMemoryText] = useState('');
  const [priorities, setPriorities] = useState<DayPayload['priorities']>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [draft, setDraft] = useState('');
  const [draftTitle, setDraftTitle] = useState('');
  const [draftTags, setDraftTags] = useState('brain, idea');
  const [filter, setFilter] = useState('');

  const filteredNotes = useMemo(() => {
    const query = filter.trim().toLowerCase();
    const sorted = [...notes].sort((a, b) => {
      if (a.pinned && !b.pinned) return -1;
      if (!a.pinned && b.pinned) return 1;
      return b.createdAt.localeCompare(a.createdAt);
    });
    if (!query) return sorted;
    return sorted.filter((note) => [note.title, note.text, note.tags.join(' ')].join(' ').toLowerCase().includes(query));
  }, [notes, filter]);

  const load = useCallback(async () => {
    setLoading(true); setError('');
    try {
      const [memory, prioritiesData] = await Promise.all([
        apiGet<MemoryResponse>(settings, '/mobile/memory'),
        apiGet<{ status: string; date: string; priorities: DayPayload['priorities'] }>(settings, '/mobile/priorities/tomorrow'),
      ]);
      setMemoryText(memory.message || 'Brak danych z pamięci backendu.');
      setPriorities(prioritiesData.priorities || []);
    } catch (err) { setError(humanizeFetchError(err)); }
    finally { setLoading(false); }
  }, [settings]);

  useEffect(() => { load(); }, [load]);

  const saveNote = useCallback(() => {
    if (!draft.trim()) {
      Alert.alert('Jarvis', 'Najpierw wpisz treść notatki.');
      return;
    }
    const note = createBrainNote({ title: draftTitle, text: draft, tags: parseTags(draftTags), source: 'manual' });
    onAddBrainNote(note);
    setDraft('');
    setDraftTitle('');
    Alert.alert('Jarvis', 'Notatka została dodana do Second Brain.');
  }, [draft, draftTags, draftTitle, onAddBrainNote]);

  return (
    <ScrollView style={styles.screenFill} contentContainerStyle={styles.screenContent}>
      <Text style={styles.h1}>Brain</Text>
      <Text style={styles.sub}>Priorytety jutra, pamięć backendu i lokalny Second Brain do notatek, myśli i pomysłów.</Text>
      <View style={styles.inlineActionsWrap}>
        <Pressable style={styles.primaryButton} onPress={load}><Text style={styles.primaryButtonText}>{loading ? 'Odświeżam...' : 'Odśwież'}</Text></Pressable>
        <Chip text={`${notes.length} notatek`} active />
      </View>
      {error ? <Text style={styles.errorText}>{error}</Text> : null}

      <SectionCard title="Top priorytety jutra">
        <PriorityList items={priorities} emptyText="Brak priorytetów jutra." />
      </SectionCard>

      <SectionCard title="Pamięć Jarvisa" subtitle="co backend o Tobie pamięta" right={loading ? <ActivityIndicator color={colors.primary} /> : null}>
        <Text style={styles.memoryText}>{memoryText || 'Brak danych.'}</Text>
      </SectionCard>

      <SectionCard title="Dodaj do Second Brain" subtitle="zapisuj decyzje, wnioski, pomysły, zasady działania">
        <TextInput value={draftTitle} onChangeText={setDraftTitle} placeholder="Tytuł notatki" placeholderTextColor={colors.muted} style={styles.textInput} />
        <TextInput value={draftTags} onChangeText={setDraftTags} placeholder="tagi, np. praca, pomysł" placeholderTextColor={colors.muted} style={styles.textInput} />
        <TextInput value={draft} onChangeText={setDraft} placeholder="Treść myśli lub wiedzy do zapamiętania" placeholderTextColor={colors.muted} multiline style={styles.largeInput} />
        <Pressable style={styles.primaryButton} onPress={saveNote}><Text style={styles.primaryButtonText}>Dodaj notatkę</Text></Pressable>
      </SectionCard>

      <SectionCard title="Przeszukaj Brain">
        <TextInput value={filter} onChangeText={setFilter} placeholder="szukaj po tytule, treści albo tagu" placeholderTextColor={colors.muted} style={styles.textInput} />
        <NoteList notes={filteredNotes} onTogglePin={onTogglePin} onDelete={onDeleteNote} />
      </SectionCard>
    </ScrollView>
  );
}

function InboxScreen({
  settings,
  seedCapture,
  onCaptureConsumed,
  voiceAutoSend,
  autoplanAfterInbox,
  onAddBrainNote,
}: {
  settings: SettingsState;
  seedCapture: string | null;
  onCaptureConsumed: () => void;
  voiceAutoSend: boolean;
  autoplanAfterInbox: boolean;
  onAddBrainNote: (note: BrainNote) => void;
}) {
  const [text, setText] = useState('');
  const [busy, setBusy] = useState(false);
  const [voiceState, setVoiceState] = useState<VoiceState>({ listening: false, liveText: '', error: '' });
  const stopVoiceRef = useRef<null | (() => void)>(null);

  useEffect(() => {
    if (seedCapture) {
      setText(seedCapture);
      onCaptureConsumed();
    }
  }, [seedCapture, onCaptureConsumed]);

  useEffect(() => () => { stopVoiceRef.current?.(); }, []);

  const submitInbox = useCallback(async (raw?: string) => {
    const value = (raw ?? text).trim();
    if (!value) {
      Alert.alert('Jarvis', 'Wpisz albo powiedz coś do Inboxa.');
      return;
    }
    setBusy(true);
    try {
      const result = await apiPost<ActionResponse>(settings, '/mobile/inbox', { text: value });
      let body = result.message || 'Dodano do inboxa.';
      if (autoplanAfterInbox) {
        const planner = await apiPost<ActionResponse>(settings, '/mobile/plan/tomorrow');
        body += `\n\nAI planner: ${planner.message || 'zaktualizowano jutro.'}`;
      }
      Alert.alert('Jarvis', body);
      setText('');
    } catch (err) {
      Alert.alert('Jarvis', humanizeFetchError(err));
    } finally { setBusy(false); }
  }, [autoplanAfterInbox, settings, text]);

  const saveThought = useCallback(() => {
    if (!text.trim()) {
      Alert.alert('Jarvis', 'Najpierw wpisz myśl do zapisania.');
      return;
    }
    const note = createBrainNote({ text, tags: ['capture', 'brain'], source: 'inbox' });
    onAddBrainNote(note);
    setText('');
    Alert.alert('Jarvis', 'Myśl została zapisana do Brain bez wrzucania do Inboxa.');
  }, [onAddBrainNote, text]);

  const startVoice = useCallback(async () => {
    if (voiceState.listening) {
      stopVoiceRef.current?.();
      stopVoiceRef.current = null;
      setVoiceState({ listening: false, liveText: '', error: '' });
      return;
    }
    setVoiceState({ listening: true, liveText: '', error: '' });
    stopVoiceRef.current = await startVoiceCapture({
      onStart: () => setVoiceState({ listening: true, liveText: '', error: '' }),
      onPartial: (value) => setVoiceState((prev) => ({ ...prev, liveText: value, error: '' })),
      onResult: (value) => {
        setVoiceState({ listening: false, liveText: value, error: '' });
        setText(value);
        if (voiceAutoSend) submitInbox(value);
      },
      onError: (message) => setVoiceState({ listening: false, liveText: '', error: message }),
      onEnd: () => setVoiceState((prev) => ({ ...prev, listening: false })),
    });
  }, [submitInbox, voiceAutoSend, voiceState.listening]);

  return (
    <ScrollView style={styles.screenFill} contentContainerStyle={styles.screenContent}>
      <Text style={styles.h1}>Inbox</Text>
      <Text style={styles.sub}>Szybki capture dla nowego zadania, wydarzenia albo myśli do Second Brain.</Text>
      <SectionCard title="Wrzuć myśl do Jarvisa" subtitle="naturalny język, bez sztywnego formularza">
        <QuickPromptRow items={QUICK_CAPTURE} onPress={setText} />
        <VoicePill voiceState={voiceState} />
        <TextInput value={text} onChangeText={setText} placeholder="Np. jutro 9 dentysta albo pomysł: uprościć onboarding" placeholderTextColor={colors.muted} multiline style={styles.largeInput} />
        <View style={styles.inlineActionsWrap}>
          <Pressable style={styles.primaryButton} onPress={() => submitInbox()}><Text style={styles.primaryButtonText}>{busy ? 'Dodaję...' : 'Dodaj do Inboxa'}</Text></Pressable>
          <Pressable style={[styles.voiceButton, voiceState.listening && styles.voiceButtonActive]} onPress={startVoice}><Text style={styles.voiceButtonText}>{voiceState.listening ? '⏹ Stop' : '🎤 Mów'}</Text></Pressable>
          <Pressable style={styles.secondaryButton} onPress={saveThought}><Text style={styles.secondaryButtonText}>Zapisz do Brain</Text></Pressable>
        </View>
      </SectionCard>

      <SectionCard title="Tryb działania" subtitle="jak zachowuje się capture">
        <Text style={styles.memoryText}>• Voice auto-send: {voiceAutoSend ? 'włączony' : 'wyłączony'}{`\n`}• Auto-plan po dodaniu do Inboxa: {autoplanAfterInbox ? 'włączony' : 'wyłączony'}</Text>
      </SectionCard>
    </ScrollView>
  );
}

function SettingsScreen({ settings, onChange }: { settings: SettingsState; onChange: (next: SettingsState) => void }) {
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState('');

  const testConnection = useCallback(async () => {
    setTesting(true); setTestResult('');
    try {
      const health = await apiGet<HealthResponse>(settings, '/mobile/health');
      setTestResult(`OK: ${health.product} ${health.version}`);
    } catch (err) { setTestResult(humanizeFetchError(err)); }
    finally { setTesting(false); }
  }, [settings]);

  const askNotificationPermission = useCallback(async () => {
    try {
      await ensureNotificationPermission();
      Alert.alert('Jarvis', 'Powiadomienia włączone.');
    } catch (err) {
      Alert.alert('Jarvis', humanizeFetchError(err));
    }
  }, []);

  return (
    <ScrollView style={styles.screenFill} contentContainerStyle={styles.screenContent}>
      <Text style={styles.h1}>Ustawienia</Text>
      <Text style={styles.sub}>Backend, voice capture, powiadomienia i tryby działania drugiego mózgu.</Text>

      <SectionCard title="Połączenie z backendem">
        <Text style={styles.inputLabel}>Backend URL</Text>
        <TextInput value={settings.apiBase} onChangeText={(value) => onChange({ ...settings, apiBase: value })} placeholder="http://192.168.x.x:8011" placeholderTextColor={colors.muted} autoCapitalize="none" autoCorrect={false} style={styles.textInput} />
        <Text style={styles.inputLabel}>Opcjonalny token</Text>
        <TextInput value={settings.apiToken} onChangeText={(value) => onChange({ ...settings, apiToken: value })} placeholder="zostaw puste, jeśli backend nie wymaga tokena" placeholderTextColor={colors.muted} autoCapitalize="none" autoCorrect={false} style={styles.textInput} />
        <Text style={styles.helperText}>Na telefonie wpisuj IP komputera w tym samym Wi‑Fi, np. http://192.168.8.118:8011</Text>
        <Pressable style={styles.primaryButton} onPress={testConnection}><Text style={styles.primaryButtonText}>{testing ? 'Testuję...' : 'Przetestuj połączenie'}</Text></Pressable>
        {testing ? <ActivityIndicator color={colors.primary} /> : null}
        {testResult ? <Text style={testResult.startsWith('OK:') ? styles.okText : styles.errorText}>{testResult}</Text> : null}
      </SectionCard>

      <SectionCard title="Tryby Jarvisa" subtitle="sterowanie aplikacją mobilną">
        <ToggleCard label="Lokalne powiadomienia" value={settings.notificationsEnabled} onPress={() => onChange({ ...settings, notificationsEnabled: !settings.notificationsEnabled })} />
        <ToggleCard label="Voice auto-send do Inbox" value={settings.voiceAutoSend} onPress={() => onChange({ ...settings, voiceAutoSend: !settings.voiceAutoSend })} />
        <ToggleCard label="Auto-plan po dodaniu do Inboxa" value={settings.autoplanAfterInbox} onPress={() => onChange({ ...settings, autoplanAfterInbox: !settings.autoplanAfterInbox })} />
        <Pressable style={styles.secondaryButton} onPress={askNotificationPermission}><Text style={styles.secondaryButtonText}>Nadaj zgodę na powiadomienia</Text></Pressable>
      </SectionCard>

      <SectionCard title="Co jest w v5?">
        <Text style={styles.memoryText}>• Organizer: Home, Chat, Plan, Brain, Inbox, Ustawienia{`\n`}• AI Second Brain: lokalne notatki + pamięć backendu{`\n`}• AI planner dnia: planowanie jutra + przypomnienia{`\n`}• Voice capture: prawdziwy mikrofon w Chacie i Inboxie{`\n`}• Push notifications: lokalne przypomnienia 15 minut przed punktem planu</Text>
      </SectionCard>
    </ScrollView>
  );
}

export default function App() {
  const [activeTab, setActiveTab] = useState<TabKey>('home');
  const [settings, setSettings] = useState<SettingsState>(DEFAULT_SETTINGS);
  const [seedCapture, setSeedCapture] = useState<string | null>(null);
  const [seedChat, setSeedChat] = useState<string | null>(null);
  const [settingsLoaded, setSettingsLoaded] = useState(false);
  const [brainNotes, setBrainNotes] = useState<BrainNote[]>([]);

  useEffect(() => {
    Promise.all([loadSavedSettings(), loadBrainNotes()]).then(([savedSettings, savedNotes]) => {
      if (savedSettings) setSettings(savedSettings);
      setBrainNotes(savedNotes || []);
      setSettingsLoaded(true);
    });
  }, []);

  useEffect(() => { if (settingsLoaded) saveSettings(settings); }, [settings, settingsLoaded]);
  useEffect(() => { if (settingsLoaded) saveBrainNotes(brainNotes); }, [brainNotes, settingsLoaded]);

  const title = activeTab === 'home' ? 'Dashboard' : activeTab === 'chat' ? 'Chat' : activeTab === 'plan' ? 'Plan dnia' : activeTab === 'brain' ? 'Brain' : activeTab === 'inbox' ? 'Inbox' : 'Ustawienia';

  const openCapture = useCallback((value: string) => { setSeedCapture(value); setActiveTab('inbox'); }, []);
  const openChat = useCallback((value: string) => { setSeedChat(value); setActiveTab('chat'); }, []);
  const consumeCapture = useCallback(() => setSeedCapture(null), []);
  const consumeChat = useCallback(() => setSeedChat(null), []);

  const addBrainNote = useCallback((note: BrainNote) => {
    setBrainNotes((prev) => [note, ...prev]);
  }, []);

  const deleteBrainNote = useCallback((id: string) => {
    setBrainNotes((prev) => prev.filter((note) => note.id !== id));
  }, []);

  const togglePinBrainNote = useCallback((id: string) => {
    setBrainNotes((prev) => prev.map((note) => note.id === id ? { ...note, pinned: !note.pinned } : note));
  }, []);

  const quickPlan = useCallback(async () => {
    try {
      const result = await apiPost<ActionResponse>(settings, '/mobile/plan/tomorrow');
      let extra = '';
      if (settings.notificationsEnabled) {
        const tomorrow = await apiGet<DayPayload>(settings, '/mobile/tomorrow');
        await clearJarvisNotifications();
        const count = await scheduleTimelineNotifications(tomorrow.date, tomorrow.timeline);
        extra = count ? `\nPrzypomnienia: ${count}` : '\nBrak przyszłych przypomnień.';
      }
      Alert.alert('Jarvis', `${result.message || 'Plan jutra zaktualizowany.'}${extra}`);
      setActiveTab('plan');
    } catch (err) {
      Alert.alert('Jarvis', humanizeFetchError(err));
    }
  }, [settings]);

  if (!settingsLoaded) {
    return <SafeAreaView style={styles.safeArea}><View style={[styles.mainArea, styles.centered]}><ActivityIndicator color={colors.primary} /><Text style={styles.sub}>Ładuję ustawienia Jarvisa...</Text></View></SafeAreaView>;
  }

  return (
    <SafeAreaView style={styles.safeArea}>
      <View style={styles.appHeader}>
        <View>
          <Text style={styles.appTitle}>Jarvis Mobile v5</Text>
          <Text style={styles.appSubtitle}>{title}</Text>
        </View>
        <Chip text="stable" active />
      </View>
      <View style={styles.mainArea}>
        {activeTab === 'home' ? <HomeScreen settings={settings} notes={brainNotes} onOpenTab={setActiveTab} onUseCapture={openCapture} onUseChat={openChat} onQuickPlan={quickPlan} /> : null}
        {activeTab === 'chat' ? <ChatScreen settings={settings} seedMessage={seedChat} onMessageConsumed={consumeChat} notes={brainNotes} onAddBrainNote={addBrainNote} /> : null}
        {activeTab === 'plan' ? <PlanScreen settings={settings} notificationsEnabled={settings.notificationsEnabled} /> : null}
        {activeTab === 'brain' ? <BrainScreen settings={settings} notes={brainNotes} onAddBrainNote={addBrainNote} onDeleteNote={deleteBrainNote} onTogglePin={togglePinBrainNote} /> : null}
        {activeTab === 'inbox' ? <InboxScreen settings={settings} seedCapture={seedCapture} onCaptureConsumed={consumeCapture} voiceAutoSend={settings.voiceAutoSend} autoplanAfterInbox={settings.autoplanAfterInbox} onAddBrainNote={addBrainNote} /> : null}
        {activeTab === 'settings' ? <SettingsScreen settings={settings} onChange={setSettings} /> : null}
      </View>
      <View style={styles.tabBar}>
        {[
          { key: 'home', label: 'Home' },
          { key: 'chat', label: 'Chat' },
          { key: 'plan', label: 'Plan' },
          { key: 'brain', label: 'Brain' },
          { key: 'inbox', label: 'Inbox' },
          { key: 'settings', label: 'Ustaw.' },
        ].map((tab) => {
          const isActive = activeTab === tab.key;
          return (
            <Pressable key={tab.key} style={[styles.tabButton, isActive && styles.tabButtonActive]} onPress={() => setActiveTab(tab.key as TabKey)}>
              <Text style={[styles.tabButtonText, isActive && styles.tabButtonTextActive]}>{tab.label}</Text>
            </Pressable>
          );
        })}
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: colors.bg },
  screenFill: { flex: 1 },
  appHeader: { paddingHorizontal: 16, paddingTop: 14, paddingBottom: 12, borderBottomWidth: 1, borderBottomColor: colors.border, backgroundColor: colors.surface, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  appTitle: { fontSize: 24, fontWeight: '800', color: colors.text },
  appSubtitle: { marginTop: 2, fontSize: 13, color: colors.muted },
  mainArea: { flex: 1 },
  centered: { alignItems: 'center', justifyContent: 'center', gap: 12 },
  screenContent: { padding: 16, rowGap: 16, paddingBottom: 24 },
  h1: { fontSize: 28, fontWeight: '800', color: colors.text },
  sub: { marginTop: -8, color: colors.muted, fontSize: 14 },
  heroCard: { backgroundColor: colors.card2, borderRadius: 24, padding: 18, rowGap: 8, borderWidth: 1, borderColor: colors.border },
  heroEyebrow: { color: '#BFDBFE', fontSize: 12, textTransform: 'uppercase', letterSpacing: 1 },
  heroTitle: { color: colors.text, fontSize: 22, fontWeight: '800' },
  heroText: { color: '#D6E3F5', lineHeight: 20 },
  heroStats: { flexDirection: 'row', columnGap: 10, marginTop: 6 },
  miniStat: { flex: 1, backgroundColor: 'rgba(15,23,42,0.45)', borderRadius: 18, paddingVertical: 12, paddingHorizontal: 10, borderWidth: 1, borderColor: colors.border },
  miniStatValue: { color: colors.text, fontWeight: '800', fontSize: 16 },
  miniStatLabel: { color: colors.muted, marginTop: 4, fontSize: 12 },
  grid2: { flexDirection: 'row', flexWrap: 'wrap', gap: 10 },
  featureTile: { width: '48%', backgroundColor: colors.card2, borderRadius: 18, padding: 14, borderWidth: 1, borderColor: colors.border, minHeight: 108, rowGap: 6 },
  featureTitle: { color: colors.text, fontWeight: '800', fontSize: 16 },
  featureText: { color: colors.muted, lineHeight: 18, fontSize: 13 },
  card: { backgroundColor: colors.card, borderRadius: 22, borderWidth: 1, borderColor: colors.border, padding: 16, rowGap: 12 },
  sectionTop: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start', columnGap: 12 },
  sectionTopText: { flex: 1, rowGap: 4 },
  sectionTitle: { color: colors.text, fontWeight: '800', fontSize: 16 },
  sectionSubtitle: { color: colors.muted, fontSize: 13, lineHeight: 18 },
  chip: { alignSelf: 'flex-start', paddingHorizontal: 12, paddingVertical: 8, borderRadius: 999, borderWidth: 1, borderColor: colors.border, backgroundColor: colors.chip },
  chipActive: { backgroundColor: '#172554', borderColor: colors.primaryStrong },
  chipDanger: { borderColor: '#7F1D1D', backgroundColor: '#2A0E12' },
  chipText: { color: colors.muted, fontWeight: '700' },
  chipTextActive: { color: colors.text },
  chipTextDanger: { color: colors.danger },
  quickRow: { columnGap: 10, paddingRight: 10 },
  quickButton: { backgroundColor: '#111827', borderRadius: 999, borderWidth: 1, borderColor: colors.border, paddingHorizontal: 14, paddingVertical: 10 },
  quickButtonText: { color: colors.text, fontWeight: '700' },
  homeFocusTitle: { color: colors.text, fontWeight: '800', fontSize: 20 },
  homeFocusMeta: { color: colors.muted, fontSize: 14 },
  columnGap: { rowGap: 12 },
  timelineRow: { flexDirection: 'row', columnGap: 10 },
  timelineTimeBlock: { width: 56 },
  timelineTime: { color: colors.text, fontWeight: '800' },
  timelineTimeEnd: { color: colors.muted, fontSize: 12, marginTop: 2 },
  timelineDot: { width: 10, height: 10, borderRadius: 5, backgroundColor: colors.primary, marginTop: 6 },
  focusDot: { backgroundColor: colors.good },
  lunchDot: { backgroundColor: colors.warning },
  timelineBody: { flex: 1, rowGap: 2 },
  timelineTitle: { color: colors.text, fontWeight: '700' },
  timelineMeta: { color: colors.muted, fontSize: 12, lineHeight: 16 },
  priorityRow: { flexDirection: 'row', columnGap: 10, alignItems: 'center' },
  priorityBadge: { width: 42, height: 42, borderRadius: 21, backgroundColor: '#172554', borderWidth: 1, borderColor: colors.primaryStrong, alignItems: 'center', justifyContent: 'center' },
  priorityBadgeText: { color: colors.text, fontWeight: '800' },
  priorityBody: { flex: 1, rowGap: 2 },
  priorityTitle: { color: colors.text, fontWeight: '700' },
  priorityMeta: { color: colors.muted, fontSize: 12, lineHeight: 16 },
  emptyText: { color: colors.muted, lineHeight: 20 },
  inlineActionsWrap: { flexDirection: 'row', columnGap: 12, alignItems: 'center', flexWrap: 'wrap', rowGap: 12 },
  primaryButton: { alignSelf: 'flex-start', backgroundColor: colors.primaryStrong, borderRadius: 999, paddingHorizontal: 18, paddingVertical: 12 },
  primaryButtonText: { color: '#EFF6FF', fontWeight: '800', fontSize: 15 },
  secondaryButton: { alignSelf: 'flex-start', backgroundColor: colors.card2, borderRadius: 999, paddingHorizontal: 18, paddingVertical: 12, borderWidth: 1, borderColor: colors.border },
  secondaryButtonText: { color: colors.text, fontWeight: '800', fontSize: 15 },
  secondaryDangerButton: { alignSelf: 'flex-start', backgroundColor: '#2A0E12', borderRadius: 999, paddingHorizontal: 18, paddingVertical: 12, borderWidth: 1, borderColor: '#7F1D1D' },
  secondaryDangerButtonText: { color: '#FCA5A5', fontWeight: '800', fontSize: 15 },
  voiceButton: { alignSelf: 'flex-start', backgroundColor: '#0F172A', borderRadius: 999, paddingHorizontal: 18, paddingVertical: 12, borderWidth: 1, borderColor: colors.border },
  voiceButtonActive: { backgroundColor: '#172554', borderColor: colors.primaryStrong },
  voiceButtonText: { color: colors.text, fontWeight: '800', fontSize: 15 },
  voiceLiveCard: { backgroundColor: '#0F172A', borderRadius: 18, padding: 14, borderWidth: 1, borderColor: colors.border, rowGap: 6 },
  voiceLiveCardError: { borderColor: '#7F1D1D', backgroundColor: '#2A0E12' },
  voiceLiveTitle: { color: colors.text, fontWeight: '800' },
  voiceLiveText: { color: '#D6E3F5', lineHeight: 20 },
  composerWrap: { paddingHorizontal: 16, paddingTop: 12, paddingBottom: 14, borderTopWidth: 1, borderTopColor: colors.border, backgroundColor: colors.surface, rowGap: 12 },
  composerInput: { minHeight: 88, maxHeight: 160, borderRadius: 20, backgroundColor: colors.card2, borderWidth: 1, borderColor: colors.border, color: colors.text, paddingHorizontal: 16, paddingVertical: 14, textAlignVertical: 'top' },
  chatBubbleAssistant: { alignSelf: 'flex-start', maxWidth: '88%', backgroundColor: colors.card2, borderRadius: 24, padding: 16, rowGap: 8, borderWidth: 1, borderColor: colors.border },
  chatBubbleUser: { alignSelf: 'flex-end', maxWidth: '88%', backgroundColor: colors.primaryStrong, borderRadius: 24, padding: 16, rowGap: 8 },
  chatRoleAssistant: { color: '#CBD5E1', fontWeight: '800', fontSize: 13 },
  chatRoleUser: { color: '#DBEAFE', fontWeight: '800', fontSize: 13 },
  chatTextAssistant: { color: colors.text, fontSize: 15, lineHeight: 24 },
  chatTextUser: { color: '#FFFFFF', fontSize: 15, lineHeight: 24 },
  intentText: { color: '#93C5FD', fontSize: 12 },
  segmentWrap: { flexDirection: 'row', backgroundColor: colors.card, borderRadius: 999, padding: 6, borderWidth: 1, borderColor: colors.border },
  segmentButton: { flex: 1, borderRadius: 999, paddingVertical: 16, alignItems: 'center' },
  segmentButtonActive: { backgroundColor: colors.primaryStrong },
  segmentText: { color: colors.muted, fontWeight: '800', fontSize: 18 },
  segmentTextActive: { color: '#FFFFFF' },
  infoLine: { color: colors.text, lineHeight: 22 },
  memoryText: { color: colors.text, lineHeight: 24 },
  largeInput: { minHeight: 160, borderRadius: 20, backgroundColor: colors.card2, borderWidth: 1, borderColor: colors.border, color: colors.text, paddingHorizontal: 16, paddingVertical: 14, textAlignVertical: 'top' },
  textInput: { minHeight: 58, borderRadius: 18, backgroundColor: colors.card2, borderWidth: 1, borderColor: colors.border, color: colors.text, paddingHorizontal: 16, paddingVertical: 12 },
  inputLabel: { color: colors.text, fontWeight: '700', fontSize: 14 },
  helperText: { color: colors.muted, lineHeight: 20 },
  okText: { color: colors.good, lineHeight: 20 },
  errorText: { color: colors.danger, lineHeight: 20 },
  toggleCard: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', backgroundColor: colors.card2, borderRadius: 18, paddingHorizontal: 14, paddingVertical: 14, borderWidth: 1, borderColor: colors.border },
  toggleCardActive: { borderColor: colors.primaryStrong },
  toggleLabel: { color: colors.text, fontWeight: '700', flex: 1, paddingRight: 10 },
  tabBar: { flexDirection: 'row', justifyContent: 'space-between', columnGap: 8, paddingHorizontal: 12, paddingTop: 10, paddingBottom: Platform.OS === 'ios' ? 24 : 12, borderTopWidth: 1, borderTopColor: colors.border, backgroundColor: colors.surface },
  tabButton: { flex: 1, minHeight: 52, borderRadius: 18, alignItems: 'center', justifyContent: 'center', borderWidth: 1, borderColor: colors.border, backgroundColor: '#0F172A' },
  tabButtonActive: { backgroundColor: colors.primaryStrong, borderColor: colors.primaryStrong },
  tabButtonText: { color: colors.muted, fontWeight: '800', fontSize: 14 },
  tabButtonTextActive: { color: '#FFFFFF' },
  noteCard: { backgroundColor: colors.card2, borderRadius: 18, borderWidth: 1, borderColor: colors.border, padding: 14, rowGap: 10 },
  noteTopRow: { flexDirection: 'row', alignItems: 'flex-start', columnGap: 10 },
  noteTitle: { color: colors.text, fontWeight: '800', fontSize: 16 },
  noteMeta: { color: colors.muted, fontSize: 12, marginTop: 4 },
  noteText: { color: colors.text, lineHeight: 20 },
  noteTagsWrap: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
});
