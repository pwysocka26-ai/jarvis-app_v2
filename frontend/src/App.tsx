import React, { createContext, useContext, useEffect, useMemo, useRef, useState } from 'react';
import {
  Bell,
  Home,
  MessageCircle,
  Calendar,
  Package,
  Settings,
  CheckSquare,
  ChevronRight,
  Plus,
  Search,
  ChevronDown,
  ChevronLeft,
  ChevronUp,
  ChevronRight as ChevronRightIcon,
  MapPin,
  Mic,
  Send,
  MoreVertical,
  UserCircle2,
  BookOpen,
  Lightbulb,
  ShoppingCart,
  Box,
  Mail,
  Cog,
  Check,
  CalendarDays,
  Loader2,
  ClipboardList,
  X,
  Square,
  Trash2,
  Unlink,
  Shield,
  CreditCard,
  Link2,
  Database,
  LogOut,
  Download,
  Upload,
  AlertTriangle,
  BarChart3,
  Lock,
  KeyRound,
  Smartphone,
  Sun,
  ListTodo,
  CalendarRange,
  FolderKanban,
  Clock,
} from 'lucide-react';
import type { IconType } from 'react-icons';
import {
  SiGooglecalendar,
  SiApple,
  SiGoogledrive,
  SiNotion,
  SiSlack,
  SiOllama,
} from 'react-icons/si';
import { FaMicrosoft } from 'react-icons/fa6';

type TabId = 'home' | 'chat' | 'plan' | 'calendar' | 'projects' | 'settings';

type ChatMessage = {
  id: string;
  role: 'user' | 'assistant' | 'system';
  text: string;
};

type CalendarChecklistItem = {
  id: string;
  label: string;
  done: boolean;
};

type ShoppingPoolItem = {
  id: string;
  label: string;
  done: boolean;
  linkedEventIds: string[];
};

type ProjectCategory = 'shopping' | 'reading' | 'ideas' | 'to_check' | 'general';

type ChecklistItem = {
  id: string;
  label: string;
  done: boolean;
};

type ProjectItem = {
  id: string;
  label: string;
  category: ProjectCategory;
  done: boolean;
  source: 'chat' | 'manual' | 'calendar';
  dueAt: string | null;
  time: string | null;
  checklist: ChecklistItem[];
};

type CalendarEvent = {
  id: string;
  title: string;
  date: string;
  time: string;
  location: string;
  badge: string;
  dotClass: string;
  badgeClass: string;
  note?: string;
  checklist?: CalendarChecklistItem[];
  linkedShoppingItemIds?: string[];
  shoppingItems?: ShoppingPoolItem[];
};

const copy = {
  version: 'Wersja 9.7.5',
  beta: 'BETA',
  welcome: 'Witaj Mateusz!',
  wave: '👋',
  todayLine1: 'Masz dziś ',
  tasks10: '10 zadań',
  todayLine2: ' i ',
  meeting1: '1 spotkanie',
  todayLine3: ' o ',
  todayLine4: '11:00',
  cardToday: 'Dzisiaj',
  cardTodo: 'Do zrobienia',
  cardWeek: 'Ten tydzień',
  cardProjects: 'Projekty',
  tasksLabel: 'zadań',
  upcoming: 'Nadchodzące',
  seeAll: 'Zobacz wszystko',
  event1: 'Umówione spotkanie z zespołem',
  event2: 'Przegląd zadań tygodniowych',
  meetingTag: 'Spotkanie',
  taskTag: 'Zadanie',
  navHome: 'Home',
  navChat: 'Czat',
  navCalendar: 'Kalendarz',
  navProjects: 'Projekty',
  navSettings: 'Ustawienia',
};

const DEFAULT_OLLAMA_URL = 'http://127.0.0.1:11434';
const DEFAULT_OLLAMA_MODEL = 'llama3:latest';

const OLLAMA_URL_KEY = 'jarvis_ollama_url_v1';
const OLLAMA_MODEL_KEY = 'jarvis_ollama_model_v1';
const PERM_NOTIFICATIONS_KEY = 'jarvis_perm_notifications_v1';
const PERM_MIC_KEY = 'jarvis_perm_mic_v1';
const PERM_LOCATION_KEY = 'jarvis_perm_location_v1';

function cleanUrl(url: string) {
  return url.trim().replace(/\/+$/, '');
}

function readOllamaUrl(): string {
  try {
    const v = localStorage.getItem(OLLAMA_URL_KEY)?.trim();
    return v || DEFAULT_OLLAMA_URL;
  } catch {
    return DEFAULT_OLLAMA_URL;
  }
}

function readOllamaModel(): string {
  try {
    const v = localStorage.getItem(OLLAMA_MODEL_KEY)?.trim();
    return v || DEFAULT_OLLAMA_MODEL;
  } catch {
    return DEFAULT_OLLAMA_MODEL;
  }
}

type UserProfile = {
  firstName: string;
  lastName: string;
  email: string;
};

const PROFILE_KEY = 'jarvis_profile_v1';
const DEFAULT_PROFILE: UserProfile = {
  firstName: 'Mateusz',
  lastName: '',
  email: '',
};

function readProfile(): UserProfile {
  try {
    const raw = localStorage.getItem(PROFILE_KEY);
    if (!raw) return { ...DEFAULT_PROFILE };
    const parsed = JSON.parse(raw);
    return {
      firstName: typeof parsed?.firstName === 'string' ? parsed.firstName : DEFAULT_PROFILE.firstName,
      lastName: typeof parsed?.lastName === 'string' ? parsed.lastName : DEFAULT_PROFILE.lastName,
      email: typeof parsed?.email === 'string' ? parsed.email : DEFAULT_PROFILE.email,
    };
  } catch {
    return { ...DEFAULT_PROFILE };
  }
}

function writeProfile(p: UserProfile) {
  try {
    localStorage.setItem(PROFILE_KEY, JSON.stringify(p));
  } catch {}
}

function getInitials(p: UserProfile): string {
  const first = p.firstName.trim()[0] || '';
  const last = p.lastName.trim()[0] || '';
  const combined = (first + last).toUpperCase();
  return combined || '?';
}

type Consents = {
  marketing: boolean;
  analytics: boolean;
  personalization: boolean;
};

const CONSENTS_KEY = 'jarvis_consents_v1';
const DEFAULT_CONSENTS: Consents = {
  marketing: false,
  analytics: false,
  personalization: false,
};

function readConsents(): Consents {
  try {
    const raw = localStorage.getItem(CONSENTS_KEY);
    if (!raw) return { ...DEFAULT_CONSENTS };
    const parsed = JSON.parse(raw);
    return {
      marketing: typeof parsed?.marketing === 'boolean' ? parsed.marketing : DEFAULT_CONSENTS.marketing,
      analytics: typeof parsed?.analytics === 'boolean' ? parsed.analytics : DEFAULT_CONSENTS.analytics,
      personalization:
        typeof parsed?.personalization === 'boolean' ? parsed.personalization : DEFAULT_CONSENTS.personalization,
    };
  } catch {
    return { ...DEFAULT_CONSENTS };
  }
}

function writeConsents(c: Consents) {
  try {
    localStorage.setItem(CONSENTS_KEY, JSON.stringify(c));
  } catch {}
}

type NotificationKind = 'reminder' | 'task' | 'ai' | 'integration';

type AppNotification = {
  id: string;
  kind: NotificationKind;
  title: string;
  body: string;
  time: string;
};

const MOCK_NOTIFICATIONS: AppNotification[] = [
  {
    id: 'n1',
    kind: 'reminder',
    title: 'Spotkanie z zespołem za 30 minut',
    body: 'O 11:00 • Sala konferencyjna',
    time: '10:30',
  },
  {
    id: 'n2',
    kind: 'task',
    title: 'Nowe zadanie w projekcie',
    body: 'Dokończyć raport tygodniowy',
    time: '09:15',
  },
  {
    id: 'n3',
    kind: 'ai',
    title: 'Jarvis sugeruje',
    body: 'Przełóż zakupy na środę — jutro masz 4 spotkania pod rząd',
    time: 'wczoraj',
  },
  {
    id: 'n4',
    kind: 'reminder',
    title: 'Siłownia',
    body: 'Dziś o 18:00',
    time: 'wczoraj',
  },
  {
    id: 'n5',
    kind: 'integration',
    title: 'Google Calendar',
    body: 'Dodano wydarzenie: Dentysta (czwartek 10:30)',
    time: '2 dni temu',
  },
];

const NOTIFICATIONS_READ_KEY = 'jarvis_notifications_read_v1';
const NOTIFICATIONS_DISMISSED_KEY = 'jarvis_notifications_dismissed_v1';

function readIdList(key: string): string[] {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed.filter((x) => typeof x === 'string') : [];
  } catch {
    return [];
  }
}

function writeIdList(key: string, ids: string[]) {
  try {
    localStorage.setItem(key, JSON.stringify(ids));
  } catch {}
}

type NavContextType = {
  goToAccount: () => void;
  openNotifications: () => void;
  unreadCount: number;
};

const NavContext = createContext<NavContextType | null>(null);

type HomeDetailView = null | 'inbox-tasks' | 'seven-days';

const STORAGE_KEY = 'jarvis_calendar_v6_state';

const WEEKDAYS_SHORT = ['Pon', 'Wt', 'Śr', 'Czw', 'Pt', 'Sob', 'Ndz'];
const MONTHS_PL = [
  'Styczeń',
  'Luty',
  'Marzec',
  'Kwiecień',
  'Maj',
  'Czerwiec',
  'Lipiec',
  'Sierpień',
  'Wrzesień',
  'Październik',
  'Listopad',
  'Grudzień',
];

function pad2(value: number) {
  return String(value).padStart(2, '0');
}

function toDateKey(date: Date) {
  return `${date.getFullYear()}-${pad2(date.getMonth() + 1)}-${pad2(date.getDate())}`;
}

function parseDateKey(dateKey: string) {
  const [year, month, day] = dateKey.split('-').map(Number);
  return new Date(year, month - 1, day);
}

function startOfWeek(date: Date) {
  const next = new Date(date);
  const day = next.getDay();
  const diff = day === 0 ? -6 : 1 - day;
  next.setDate(next.getDate() + diff);
  next.setHours(0, 0, 0, 0);
  return next;
}

function addDays(date: Date, days: number) {
  const next = new Date(date);
  next.setDate(next.getDate() + days);
  return next;
}

function todayKey(): string {
  return toDateKey(new Date());
}

function tomorrowKey(): string {
  const d = new Date();
  d.setDate(d.getDate() + 1);
  return toDateKey(d);
}

function endOfWeekKey(): string {
  const d = new Date();
  const day = d.getDay();
  const offsetToSunday = day === 0 ? 0 : 7 - day;
  d.setDate(d.getDate() + offsetToSunday);
  return toDateKey(d);
}

function isInNext7Days(key: string): boolean {
  const t = new Date();
  t.setHours(0, 0, 0, 0);
  const limit = new Date(t);
  limit.setDate(t.getDate() + 7);
  const [y, m, day] = key.split('-').map(Number);
  if (!y || !m || !day) return false;
  const target = new Date(y, m - 1, day);
  return target >= t && target < limit;
}

function formatDueLabel(key: string | null): string {
  if (!key) return 'Bez daty';
  if (key === todayKey()) return 'Dziś';
  if (key === tomorrowKey()) return 'Jutro';
  const [, m, d] = key.split('-').map(Number);
  return `${d} ${MONTHS_PL[m - 1].toLowerCase()}`;
}

function formatDueWithTime(date: string | null, time: string | null): string {
  if (!date && !time) return '';
  if (!date) return time ?? '';
  if (!time) return formatDueLabel(date);
  return `${formatDueLabel(date)}, ${time}`;
}

function pluralPL(n: number, forms: [string, string, string]): string {
  const abs = Math.abs(n);
  const mod10 = abs % 10;
  const mod100 = abs % 100;
  if (abs === 1) return forms[0];
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return forms[1];
  return forms[2];
}

function nowHHMM(now: Date): string {
  return `${pad2(now.getHours())}:${pad2(now.getMinutes())}`;
}

function timeUntilLabel(eventTime: string, now: Date): string {
  const [h, m] = eventTime.split(':').map(Number);
  if (Number.isNaN(h) || Number.isNaN(m)) return '';
  const target = new Date(now);
  target.setHours(h, m, 0, 0);
  const diffMin = Math.round((target.getTime() - now.getTime()) / 60000);
  if (diffMin <= 0) return 'teraz';
  if (diffMin < 60) return `${diffMin} min`;
  const hrs = Math.floor(diffMin / 60);
  const mins = diffMin % 60;
  if (mins === 0) return `${hrs} h`;
  return `${hrs} h ${mins} min`;
}

function formatMonthYear(date: Date) {
  return `${MONTHS_PL[date.getMonth()]} ${date.getFullYear()}`;
}

function formatDayLabel(dateKey: string) {
  const date = parseDateKey(dateKey);
  const weekdayIndex = date.getDay() === 0 ? 6 : date.getDay() - 1;
  return `${WEEKDAYS_SHORT[weekdayIndex]}, ${date.getDate()} ${MONTHS_PL[date.getMonth()].toLowerCase()}`;
}

function isShoppingEventTitle(title: string) {
  const normalized = title.toLowerCase();
  return (
    normalized.includes('zakupy') ||
    normalized.includes('zrób zakupy') ||
    normalized.includes('zrob zakupy') ||
    normalized.includes('muszę zrobić zakupy') ||
    normalized.includes('musze zrobic zakupy') ||
    normalized.includes('biedron') ||
    normalized.includes('lidl') ||
    normalized.includes('sklep')
  );
}

function extractShoppingItemFromChat(text: string) {
  const normalized = text.trim();
  const lower = normalized.toLowerCase();

  const triggers = [
    'muszę kupić ',
    'musze kupic ',
    'kup ',
    'dodaj do zakupów ',
    'dodaj do zakupow ',
    'potrzebuję ',
    'potrzebuje ',
  ];

  for (const trigger of triggers) {
    const index = lower.indexOf(trigger);
    if (index >= 0) {
      const extracted = normalized.slice(index + trigger.length).trim();
      if (extracted.length > 1) {
        return extracted.charAt(0).toUpperCase() + extracted.slice(1);
      }
    }
  }

  return null;
}


function extractProjectCategoryFromChat(text: string): ProjectCategory {
  const normalized = text.trim().toLowerCase();

  if (
    normalized.includes('kupić') ||
    normalized.includes('kupic') ||
    normalized.includes('kup ') ||
    normalized.includes('zakupy') ||
    normalized.includes('potrzebuję') ||
    normalized.includes('potrzebuje')
  ) {
    return 'shopping';
  }

  if (
    normalized.includes('przeczytać') ||
    normalized.includes('przeczytac') ||
    normalized.includes('książk') ||
    normalized.includes('ksiazk') ||
    normalized.includes('artykuł') ||
    normalized.includes('artykul')
  ) {
    return 'reading';
  }

  if (
    normalized.includes('pomysł') ||
    normalized.includes('pomysl') ||
    normalized.includes('idea') ||
    normalized.includes('mam pomysł') ||
    normalized.includes('mam pomysl')
  ) {
    return 'ideas';
  }

  if (
    normalized.includes('sprawdzić') ||
    normalized.includes('sprawdzic') ||
    normalized.includes('ogarnąć') ||
    normalized.includes('ogarnac') ||
    normalized.includes('przetestować') ||
    normalized.includes('przetestowac')
  ) {
    return 'to_check';
  }

  return 'general';
}

function looksLikeUndatedThought(text: string) {
  const normalized = text.trim().toLowerCase();

  const timeIndicators = [
    'jutro',
    'pojutrze',
    'za tydzień',
    'za tydzien',
    'za miesiąc',
    'za miesiac',
    'w poniedziałek',
    'w poniedzialek',
    'we wtorek',
    'w środę',
    'w srode',
    'w czwartek',
    'w piątek',
    'w piatek',
    'w sobotę',
    'w sobote',
    'w niedzielę',
    'w niedziele',
    'dziś o',
    'dzis o',
    'o 1',
    'o 2',
    'o 3',
    'o 4',
    'o 5',
    'o 6',
    'o 7',
    'o 8',
    'o 9',
    'o 10',
    'o 11',
    'o 12',
    'o 13',
    'o 14',
    'o 15',
    'o 16',
    'o 17',
    'o 18',
    'o 19',
    'o 20',
  ];

  return !timeIndicators.some((indicator) => normalized.includes(indicator));
}

function projectCategoryLabel(category: ProjectCategory) {
  switch (category) {
    case 'shopping':
      return 'Lista zakupów';
    case 'reading':
      return 'Do przeczytania';
    case 'ideas':
      return 'Pomysły';
    case 'to_check':
      return 'Do sprawdzenia';
    case 'general':
    default:
      return 'Ogólne';
  }
}

function Header({
  title,
  icon,
  showProfile = true,
  showBell = true,
  subtitle = copy.version,
  beta = false,
  extraLeft,
  extraRight,
}: {
  title: string;
  icon?: React.ReactNode;
  showProfile?: boolean;
  showBell?: boolean;
  subtitle?: string;
  beta?: boolean;
  extraLeft?: React.ReactNode;
  extraRight?: React.ReactNode;
}) {
  return (
    <header className="mb-3 flex items-start justify-between gap-4">
      <div className="min-w-0 flex items-start gap-3">
        {extraLeft}
        {icon ? <div className="pt-1">{icon}</div> : null}
        <div className="min-w-0">
          <h1 className="text-[34px] font-semibold leading-none text-slate-800">
            {title}
          </h1>
          <div className="mt-3 flex flex-wrap items-center gap-3">
            <span className="text-[17px] text-slate-500">{subtitle}</span>
            {beta ? (
              <span className="rounded-full bg-indigo-100 px-3 py-1 text-sm font-medium text-indigo-400">
                BETA
              </span>
            ) : null}
          </div>
        </div>
      </div>

      <div className="flex shrink-0 items-center gap-3">
        {extraRight}
        {showBell ? <HeaderBell /> : null}
        {showProfile ? <HeaderAvatar /> : null}
      </div>
    </header>
  );
}

function HeaderBell() {
  const nav = useContext(NavContext);
  const unread = nav?.unreadCount ?? 0;
  return (
    <button
      type="button"
      onClick={() => nav?.openNotifications()}
      className="relative flex h-10 w-10 items-center justify-center rounded-full transition hover:bg-white/60"
      aria-label="Powiadomienia"
    >
      <Bell className="h-8 w-8 text-slate-700" />
      {unread > 0 ? (
        <div className="absolute -right-0.5 -top-1 flex h-6 min-w-[24px] items-center justify-center rounded-full bg-pink-400 px-1 text-[13px] font-semibold text-white">
          {unread > 9 ? '9+' : unread}
        </div>
      ) : null}
    </button>
  );
}

function HeaderAvatar() {
  const nav = useContext(NavContext);
  const profile = readProfile();
  const initials = getInitials(profile);
  return (
    <button
      type="button"
      onClick={() => nav?.goToAccount()}
      className="flex h-14 w-14 shrink-0 items-center justify-center rounded-full border-2 border-indigo-200 bg-[linear-gradient(180deg,#7196ff_0%,#4f75ff_100%)] text-[18px] font-bold text-white shadow-sm transition hover:scale-105"
      aria-label="Moje konto"
    >
      {initials}
    </button>
  );
}

function SearchBar({ placeholder = 'Szukaj...' }: { placeholder?: string }) {
  return (
    <div className="mb-4 -mx-5 bg-[linear-gradient(180deg,#edf1f9_0%,#ebedf5_100%)] px-5 py-4">
      <div className="flex items-center gap-3 rounded-[24px] bg-white/70 px-5 py-4 shadow-sm">
        <Search className="h-7 w-7 text-slate-400" />
        <span className="text-[16px] text-slate-400">{placeholder}</span>
      </div>
    </div>
  );
}

function DashboardCard({
  icon,
  title,
  value,
  subtitle,
  bg,
  onClick,
}: {
  icon: React.ReactNode;
  title: string;
  value: string;
  subtitle: string;
  bg: string;
  onClick?: () => void;
}) {
  return (
    <button
      className={`h-[118px] rounded-[22px] ${bg} px-4 py-3 text-left shadow-sm`}
      onClick={onClick}
      type="button"
    >
      <div className="mb-2 flex items-start justify-between gap-2">
        <div className="flex min-w-0 items-center gap-3">
          <div className="shrink-0 rounded-2xl bg-white/85 p-2 shadow-sm">{icon}</div>
          <span className="text-[16px] font-semibold text-slate-700">{title}</span>
        </div>
        <ChevronRight className="h-5 w-5 shrink-0 text-slate-400" />
      </div>

      <div className="text-center text-[26px] font-semibold leading-none text-slate-800">
        {value}
      </div>
      <div className="mt-2 text-center text-[12px] text-slate-500">{subtitle}</div>
    </button>
  );
}

function NavItem({
  id,
  label,
  activeTab,
  setActiveTab,
  icon: Icon,
}: {
  id: 'home' | 'chat' | 'calendar' | 'projects' | 'settings';
  label: string;
  activeTab: TabId;
  setActiveTab: (tab: TabId) => void;
  icon: React.ElementType;
}) {
  const active = activeTab === id;

  return (
    <button
      onClick={() => setActiveTab(id)}
      className="flex flex-col items-center justify-center gap-1"
      type="button"
    >
      <div
        className={`flex h-11 w-11 items-center justify-center rounded-2xl transition ${
          active ? 'bg-indigo-100 text-indigo-500' : 'text-slate-500'
        }`}
      >
        <Icon className="h-6 w-6" />
      </div>
      <span className={`text-[11px] ${active ? 'text-indigo-500' : 'text-slate-600'}`}>
        {label}
      </span>
    </button>
  );
}

function BottomNav({
  activeTab,
  setActiveTab,
}: {
  activeTab: TabId;
  setActiveTab: (tab: TabId) => void;
}) {
  return (
    <nav className="rounded-[30px] bg-white/75 px-4 py-4 shadow-[0_10px_24px_rgba(15,23,42,0.06)]">
      <div className="grid grid-cols-5 items-center">
        <NavItem id="home" label={copy.navHome} activeTab={activeTab} setActiveTab={setActiveTab} icon={Home} />
        <NavItem id="chat" label={copy.navChat} activeTab={activeTab} setActiveTab={setActiveTab} icon={MessageCircle} />
        <NavItem id="calendar" label={copy.navCalendar} activeTab={activeTab} setActiveTab={setActiveTab} icon={Calendar} />
        <NavItem id="projects" label={copy.navProjects} activeTab={activeTab} setActiveTab={setActiveTab} icon={Package} />
        <NavItem id="settings" label={copy.navSettings} activeTab={activeTab} setActiveTab={setActiveTab} icon={Settings} />
      </div>
    </nav>
  );
}

function PhoneShell({
  children,
  activeTab,
  setActiveTab,
}: {
  children: React.ReactNode;
  activeTab: TabId;
  setActiveTab: (tab: TabId) => void;
}) {
  return (
    <div className="min-h-screen bg-[linear-gradient(180deg,#f3f3f9_0%,#ececf5_100%)] px-4 py-4">
      <div className="mx-auto w-full max-w-[430px]">
        <div className="relative h-[860px] overflow-hidden rounded-[46px] border border-white/70 bg-[linear-gradient(180deg,rgba(255,255,255,0.86),rgba(243,241,249,0.98))] px-5 pb-5 pt-4 shadow-[0_30px_70px_rgba(99,102,241,0.10)]">
          <div className="mx-auto mb-3 h-1.5 w-28 rounded-full bg-indigo-200" />
          <div className="flex h-[calc(100%-18px)] flex-col">
            <div className="min-h-0 flex-1 overflow-hidden">{children}</div>
            <div className="mt-4">
              <BottomNav activeTab={activeTab} setActiveTab={setActiveTab} />
              <div className="mx-auto mt-4 h-1.5 w-40 rounded-full bg-slate-800" />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function HomeScreen({
  setActiveTab,
  projectItems,
  events,
  onOpenInbox,
  onOpenWeek,
}: {
  setActiveTab: (tab: TabId) => void;
  projectItems: ProjectItem[];
  events: CalendarEvent[];
  onOpenInbox: () => void;
  onOpenWeek: () => void;
}) {
  const profile = readProfile();
  const firstName = profile.firstName.trim() || DEFAULT_PROFILE.firstName;

  const [now, setNow] = useState<Date>(() => new Date());
  useEffect(() => {
    const id = window.setInterval(() => setNow(new Date()), 60_000);
    return () => window.clearInterval(id);
  }, []);

  const today = todayKey();
  const inboxCount = projectItems.filter(
    (i) => !i.done && (!i.dueAt || i.dueAt === today)
  ).length;

  const weekEventsCount = events.filter((e) => isInNext7Days(e.date)).length;
  const weekTasksCount = projectItems.filter(
    (i) => !i.done && i.dueAt && isInNext7Days(i.dueAt)
  ).length;
  const weekCount = weekEventsCount + weekTasksCount;

  const projectsCount = projectItems.filter((i) => !i.done).length;

  const todayTasksCount = projectItems.filter(
    (i) => !i.done && i.dueAt === today
  ).length;
  const todayEventsSorted = events
    .filter((e) => e.date === today)
    .slice()
    .sort((a, b) => (a.time || '').localeCompare(b.time || ''));
  const todayEventsCount = todayEventsSorted.length;

  const nowTime = nowHHMM(now);

  type UpcomingItem = {
    id: string;
    kind: 'event' | 'task';
    time: string;
    title: string;
    note: string | null;
    dotClass: string;
    badge: string;
    badgeClass: string;
  };

  const upcomingEventItems: UpcomingItem[] = todayEventsSorted
    .filter((e) => e.time && e.time >= nowTime)
    .map((e) => ({
      id: e.id,
      kind: 'event',
      time: e.time,
      title: e.title,
      note: e.note ?? null,
      dotClass: e.dotClass,
      badge: e.badge,
      badgeClass: e.badgeClass,
    }));

  const upcomingTaskItems: UpcomingItem[] = projectItems
    .filter((i) => !i.done && i.dueAt === today && i.time && i.time >= nowTime)
    .map((i) => ({
      id: i.id,
      kind: 'task',
      time: i.time as string,
      title: i.label,
      note: null,
      dotClass: 'bg-indigo-400',
      badge: 'Zadanie',
      badgeClass: 'bg-indigo-100 text-indigo-500',
    }));

  const upcomingToday = [...upcomingEventItems, ...upcomingTaskItems]
    .sort((a, b) => a.time.localeCompare(b.time))
    .slice(0, 2);
  const nextItem = upcomingToday[0] ?? null;

  const nextEventTime =
    [
      ...todayEventsSorted.filter((e) => e.time).map((e) => e.time),
      ...projectItems
        .filter((i) => !i.done && i.dueAt === today && i.time)
        .map((i) => i.time as string),
    ].sort()[0] ?? null;

  function renderTodayMessage(): React.ReactNode {
    if (todayTasksCount === 0 && todayEventsCount === 0) {
      return 'Dziś nic nie zaplanowane.';
    }
    const parts: React.ReactNode[] = ['Masz dziś '];
    if (todayTasksCount > 0) {
      parts.push(
        <span key="t" className="font-semibold text-slate-800">
          {todayTasksCount} {pluralPL(todayTasksCount, ['zadanie', 'zadania', 'zadań'])}
        </span>
      );
    }
    if (todayTasksCount > 0 && todayEventsCount > 0) parts.push(' i ');
    if (todayEventsCount > 0) {
      parts.push(
        <span key="e" className="font-semibold text-slate-800">
          {todayEventsCount} {pluralPL(todayEventsCount, ['spotkanie', 'spotkania', 'spotkań'])}
        </span>
      );
    }
    if (nextEventTime) {
      parts.push(todayEventsCount === 1 ? ' o ' : ' — najbliższe o ');
      parts.push(
        <span key="time" className="font-semibold text-slate-800">
          {nextEventTime}
        </span>
      );
    }
    parts.push('.');
    return <>{parts}</>;
  }

  return (
    <div className="flex h-full flex-col">
      <Header title="Home" subtitle={copy.version} beta />
      <section className="-mx-5 mb-3 bg-[linear-gradient(180deg,#edf1f9_0%,#ebedf5_100%)] px-5 py-0">
        <div className="flex h-[122px] items-center gap-3">
          <div className="flex w-[170px] shrink-0 items-center justify-center">
            <img
              src="/robot-premium.png"
              alt="Jarvis robot"
              className="object-contain drop-shadow-[0_18px_24px_rgba(99,102,241,0.18)]"
              style={{ width: 168, height: 168 }}
            />
          </div>

          <div className="min-w-0 flex-1 pr-1 text-center">
            <h2 className="text-[24px] font-semibold leading-tight text-slate-800">
              Witaj {firstName}
            </h2>
            <p className="mt-2 text-[16px] font-medium leading-6 text-slate-700">
              {renderTodayMessage()}
            </p>
          </div>
        </div>
      </section>

      <section className="mb-3 grid grid-cols-2 gap-4">
        <DashboardCard
          icon={<Sun className="h-5 w-5 text-orange-400" />}
          title={copy.cardToday}
          value={String(inboxCount)}
          subtitle={copy.tasksLabel}
          bg="bg-[linear-gradient(135deg,#f7efe9_0%,#f4efed_100%)]"
          onClick={onOpenInbox}
        />
        <DashboardCard
          icon={<CalendarRange className="h-5 w-5 text-cyan-400" />}
          title={copy.cardWeek}
          value={String(weekCount)}
          subtitle={copy.tasksLabel}
          bg="bg-[linear-gradient(135deg,#ecf5f5_0%,#edf2f2_100%)]"
          onClick={onOpenWeek}
        />
        <DashboardCard
          icon={<FolderKanban className="h-5 w-5 text-violet-400" />}
          title={copy.cardProjects}
          value={String(projectsCount)}
          subtitle={copy.tasksLabel}
          bg="bg-[linear-gradient(135deg,#f0eefb_0%,#f2f0fb_100%)]"
          onClick={() => setActiveTab('projects')}
        />
      </section>

      <section className="mb-2">
        {nextItem ? (
          <button
            type="button"
            onClick={onOpenInbox}
            className="mb-3 flex w-full items-start gap-3 rounded-[18px] bg-[linear-gradient(135deg,#eef2ff_0%,#f5f3ff_100%)] p-3 text-left shadow-sm"
          >
            <div className="shrink-0 rounded-full bg-white/80 p-2">
              <Bell className="h-4 w-4 text-indigo-500" />
            </div>
            <div className="min-w-0 flex-1">
              <div className="text-[12px] font-semibold uppercase tracking-wide text-indigo-500">
                Nadchodzące — {nextItem.time} {nextItem.title}
              </div>
              <div className="mt-0.5 text-[13px] leading-5 text-slate-700">
                Masz {timeUntilLabel(nextItem.time, now)}
                {nextItem.note ? `, pamiętaj o ${nextItem.note}` : ''}.
              </div>
            </div>
          </button>
        ) : null}

        <div className="mb-2 flex items-center gap-3">
          <Clock className="h-7 w-7 text-violet-400" />
          <h3 className="text-[18px] font-semibold text-slate-800">
            {copy.upcoming}
          </h3>
        </div>

        <div className="rounded-[22px] bg-white/75 p-3 shadow-sm">
          {upcomingToday.length === 0 ? (
            <div className="px-1 py-2 text-[13px] text-slate-400">
              Nic więcej zaplanowanego na dziś.
            </div>
          ) : (
            upcomingToday.map((it, idx) => (
              <button
                key={`${it.kind}-${it.id}`}
                type="button"
                onClick={onOpenInbox}
                className={`flex w-full items-center justify-between gap-3 text-left ${
                  idx > 0 ? 'mt-3 border-t border-slate-200 pt-3' : ''
                }`}
              >
                <div className="flex min-w-0 items-center gap-3">
                  <div className={`h-4 w-4 shrink-0 rounded-full ${it.dotClass}`} />
                  <div className="shrink-0 text-[15px] font-semibold text-slate-800">
                    {it.time}
                  </div>
                  <div className="truncate text-[15px] text-slate-700">{it.title}</div>
                </div>
                <div
                  className={`shrink-0 rounded-2xl px-3 py-1.5 text-[13px] font-medium ${it.badgeClass}`}
                >
                  {it.badge}
                </div>
              </button>
            ))
          )}
        </div>
      </section>

    </div>
  );
}

function PlanScreen() {
  const items = [
    ['09:00', 'Sprawdzić plan dnia', 'Dzisiaj', 'bg-blue-500'],
    ['11:00', 'Umówione spotkanie z zespołem', 'Spotkanie', 'bg-violet-500'],
    ['15:30', 'Przegląd zadań tygodniowych', 'Zadanie', 'bg-orange-400'],
    ['18:00', 'Siłownia', 'Prywatne', 'bg-emerald-500'],
    ['19:00', 'Zakupy', 'Dom', 'bg-amber-400'],
  ] as const;

  return (
    <div className="flex h-full flex-col">
      <Header
        title="Plan"
        subtitle={copy.version}
        icon={<ClipboardList className="h-10 w-10 text-indigo-400" />}
      />
      <div className="min-h-0 flex-1 overflow-y-auto pr-1">
        <div className="mb-4 rounded-[22px] bg-[linear-gradient(180deg,#edf1f9_0%,#ebedf5_100%)] p-5">
          <div className="text-[18px] font-semibold text-slate-800">Dzisiejszy plan</div>
          <div className="mt-2 text-[15px] leading-6 text-slate-600">
            Wszystkie najważniejsze rzeczy zebrane w jednym miejscu.
          </div>
        </div>

        <div className="space-y-3">
          {items.map(([time, title, tag, dotClass]) => (
            <div key={title} className="rounded-[22px] bg-white/75 p-4 shadow-sm">
              <div className="flex items-start justify-between gap-3">
                <div className="flex min-w-0 items-start gap-3">
                  <div className={`mt-1 h-4 w-4 shrink-0 rounded-full ${dotClass}`} />
                  <div className="min-w-0">
                    <div className="text-[14px] font-medium text-slate-500">{time}</div>
                    <div className="mt-1 text-[18px] font-semibold text-slate-800">{title}</div>
                  </div>
                </div>

                <div className="shrink-0 rounded-2xl bg-indigo-100 px-3 py-1.5 text-[13px] font-medium text-indigo-500">
                  {tag}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function ChatScreen({
  onShoppingDetected,
  onProjectDetected,
  chatMessages,
  setChatMessages,
}: {
  onShoppingDetected: (itemLabel: string) => void;
  onProjectDetected: (text: string) => void;
  chatMessages: ChatMessage[];
  setChatMessages: React.Dispatch<React.SetStateAction<ChatMessage[]>>;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [message, setMessage] = useState('');
  const [isSending, setIsSending] = useState(false);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages, isSending]);

  async function sendMessage() {
    const trimmed = message.trim();
    if (!trimmed || isSending) return;

    const userMessage: ChatMessage = {
      id: `u-${Date.now()}`,
      role: 'user',
      text: trimmed,
    };

    const nextMessages = [...chatMessages, userMessage];
    setChatMessages(nextMessages);
    setMessage('');

    const extractedShoppingItem = extractShoppingItemFromChat(trimmed);
    if (extractedShoppingItem) {
      onShoppingDetected(extractedShoppingItem);
      onProjectDetected(trimmed);
      setChatMessages((prev) => [
        ...prev,
        {
          id: `local-${Date.now()}`,
          role: 'assistant',
          text: `Dodałem do listy zakupów: ${extractedShoppingItem}. Zapisałem to też w Projektach.`,
        },
      ]);
      inputRef.current?.focus();
      return;
    }

    if (looksLikeUndatedThought(trimmed)) {
      onProjectDetected(trimmed);
      setChatMessages((prev) => [
        ...prev,
        {
          id: `local-${Date.now()}`,
          role: 'assistant',
          text: 'Zapisałem to w Projektach jako rzecz bez konkretnej daty.',
        },
      ]);
      inputRef.current?.focus();
      return;
    }

    setIsSending(true);
    const ollamaUrl = readOllamaUrl();
    const ollamaModel = readOllamaModel();

    try {
      const response = await fetch(`${ollamaUrl}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model: ollamaModel,
          stream: false,
          messages: nextMessages
            .filter((m) => m.role !== 'system')
            .map((m) => ({
              role: m.role,
              content: m.text,
            })),
        }),
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(errorText || `HTTP ${response.status}`);
      }

      const data = await response.json();
      const assistantText =
        data?.message?.content?.trim() ||
        'Nie udało się pobrać odpowiedzi z Ollamy.';

      setChatMessages((prev) => [
        ...prev,
        {
          id: `a-${Date.now()}`,
          role: 'assistant',
          text: assistantText,
        },
      ]);
    } catch (error) {
      const message =
        error instanceof Error ? error.message.toLowerCase() : '';

      let userError = `Nie mogę połączyć się z Ollamą. Upewnij się, że Ollama działa pod ${ollamaUrl} i masz model ${ollamaModel}.`;

      if (message.includes('not found') || message.includes('model')) {
        userError = `Ollama działa, ale model ${ollamaModel} nie jest dostępny.`;
      } else if (message.includes('failed to fetch') || message.includes('network')) {
        userError = `Nie udało się połączyć z Ollamą pod adresem ${ollamaUrl}. Sprawdź adres w Ustawieniach.`;
      }

      setChatMessages((prev) => [
        ...prev,
        {
          id: `e-${Date.now()}`,
          role: 'assistant',
          text: userError,
        },
      ]);
    } finally {
      setIsSending(false);
      inputRef.current?.focus();
    }
  }

  return (
    <div className="flex h-full flex-col">
      <Header
        title="Chat"
        subtitle={copy.version}
        icon={<MessageCircle className="h-10 w-10 text-indigo-500" />}
      />

      <div className="-mx-5 min-h-0 flex-1 bg-[linear-gradient(180deg,#edf1f9_0%,#ebedf5_100%)] px-5 py-5">
        <div className="flex h-full flex-col">
          <div className="min-h-0 flex-1 overflow-y-auto rounded-[30px] bg-transparent">
            {chatMessages.length === 0 ? (
              <div className="flex h-full items-center justify-center px-8 text-center text-[16px] text-slate-400">
                Napisz pierwszą wiadomość do Jarvisa.
              </div>
            ) : (
              <div className="space-y-4 pb-4">
                {chatMessages.map((msg) => (
                  <div
                    key={msg.id}
                    className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    <div
                      className={`max-w-[80%] rounded-[24px] px-4 py-3 text-[16px] leading-6 shadow-sm ${
                        msg.role === 'user'
                          ? 'rounded-br-[8px] bg-[linear-gradient(180deg,#7196ff_0%,#4f75ff_100%)] text-white'
                          : 'rounded-bl-[8px] bg-white/85 text-slate-800'
                      }`}
                    >
                      {msg.text}
                    </div>
                  </div>
                ))}

                {isSending ? (
                  <div className="flex justify-start">
                    <div className="rounded-[24px] rounded-bl-[8px] bg-white/85 px-4 py-3 text-slate-500 shadow-sm">
                      <Loader2 className="h-5 w-5 animate-spin" />
                    </div>
                  </div>
                ) : null}

                <div ref={messagesEndRef} />
              </div>
            )}
          </div>

          <div className="mt-4">
            <div className="flex items-center gap-3 rounded-[28px] bg-white/80 px-5 py-4 shadow-sm">
              <input
                ref={inputRef}
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault();
                    sendMessage();
                  }
                }}
                placeholder="Napisz do Jarvisa..."
                className="flex-1 bg-transparent text-[18px] text-slate-700 outline-none placeholder:text-slate-400"
                autoFocus
              />
              <button className="text-indigo-400" type="button">
                <Mic className="h-7 w-7" />
              </button>
              <button
                className="rounded-full bg-[linear-gradient(180deg,#7196ff_0%,#4f75ff_100%)] p-4 text-white shadow-sm disabled:opacity-60"
                onClick={sendMessage}
                disabled={isSending || !message.trim()}
                type="button"
              >
                <Send className="h-6 w-6" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function CalendarScreen({
  shoppingPool,
  setShoppingPool,
  events,
  setEvents,
}: {
  shoppingPool: ShoppingPoolItem[];
  setShoppingPool: React.Dispatch<React.SetStateAction<ShoppingPoolItem[]>>;
  events: CalendarEvent[];
  setEvents: React.Dispatch<React.SetStateAction<CalendarEvent[]>>;
}) {
  const today = useMemo(() => new Date(), []);
  const initialWeekStart = useMemo(() => startOfWeek(today), [today]);

  const [weekStart, setWeekStart] = useState(initialWeekStart);
  const [selectedDate, setSelectedDate] = useState(toDateKey(today));
  const [expandedEventId, setExpandedEventId] = useState<string | null>(null);
  const [showMonthPicker, setShowMonthPicker] = useState(false);
  const [pickerDate, setPickerDate] = useState(today);
  const [showNewEventModal, setShowNewEventModal] = useState(false);

  const [newEventTitle, setNewEventTitle] = useState('');
  const [newEventTime, setNewEventTime] = useState('10:00');
  const [newEventLocation, setNewEventLocation] = useState('');
  const [newEventNote, setNewEventNote] = useState('');
  const [newEventChecklist, setNewEventChecklist] = useState('');
  const [newShoppingPoolItem, setNewShoppingPoolItem] = useState('');

  const eventsByDate = useMemo(() => {
    const grouped: Record<string, CalendarEvent[]> = {};
    for (const event of events) {
      if (!grouped[event.date]) grouped[event.date] = [];
      grouped[event.date].push(event);
    }
    Object.keys(grouped).forEach((key) => {
      grouped[key].sort((a, b) => a.time.localeCompare(b.time));
    });
    return grouped;
  }, [events]);

  const weekDays = useMemo(
    () => Array.from({ length: 7 }, (_, index) => addDays(weekStart, index)),
    [weekStart]
  );

  const selectedDateInVisibleWeek = useMemo(
    () => weekDays.some((date) => toDateKey(date) === selectedDate),
    [weekDays, selectedDate]
  );

  const effectiveSelectedDate = selectedDateInVisibleWeek ? selectedDate : toDateKey(weekStart);
  const selectedEvents = eventsByDate[effectiveSelectedDate] || [];

  useEffect(() => {
    if (!selectedDateInVisibleWeek) {
      setSelectedDate(toDateKey(weekStart));
    }
  }, [selectedDateInVisibleWeek, weekStart]);

  useEffect(() => {
    if (showMonthPicker) {
      setPickerDate(parseDateKey(effectiveSelectedDate));
    }
  }, [showMonthPicker, effectiveSelectedDate]);

  function goWeek(delta: number) {
    setWeekStart((prev) => addDays(prev, delta * 7));
  }

  function buildChecklistItems(source: string) {
    return source
      .split('\n')
      .map((item) => item.trim())
      .filter(Boolean)
      .map((label, index) => ({
        id: `c-${Date.now()}-${index}`,
        label,
        done: false,
      }));
  }

  function createEvent() {
    const trimmedTitle = newEventTitle.trim();
    if (!trimmedTitle) return;

    const shoppingEvent = isShoppingEventTitle(trimmedTitle);

    const event: CalendarEvent = {
      id: `event-${Date.now()}`,
      title: trimmedTitle,
      date: effectiveSelectedDate,
      time: newEventTime || '10:00',
      location: newEventLocation.trim() || 'Brak miejsca',
      badge: shoppingEvent ? 'Zakupy' : 'Nowe',
      dotClass: shoppingEvent ? 'bg-rose-500' : 'bg-indigo-500',
      badgeClass: shoppingEvent
        ? 'bg-rose-500/10 text-rose-600'
        : 'bg-indigo-500/10 text-indigo-600',
      note: newEventNote.trim(),
      checklist: shoppingEvent ? [] : buildChecklistItems(newEventChecklist),
      linkedShoppingItemIds: [],
      shoppingItems: [],
    };

    setEvents((prev) => [...prev, event]);
    setExpandedEventId(event.id);
    setShowNewEventModal(false);
    setNewEventTitle('');
    setNewEventTime('10:00');
    setNewEventLocation('');
    setNewEventNote('');
    setNewEventChecklist('');
  }

  function applyMonthPicker(date: Date) {
    const nextDateKey = toDateKey(date);
    setSelectedDate(nextDateKey);
    setWeekStart(startOfWeek(date));
    setShowMonthPicker(false);
  }

  function toggleChecklistItem(eventId: string, itemId: string) {
    setEvents((prev) =>
      prev.map((event) =>
        event.id !== eventId
          ? event
          : {
              ...event,
              checklist: (event.checklist || []).map((item) =>
                item.id === itemId ? { ...item, done: !item.done } : item
              ),
            }
      )
    );
  }

  function removeChecklistItem(eventId: string, itemId: string) {
    setEvents((prev) =>
      prev.map((event) =>
        event.id !== eventId
          ? event
          : {
              ...event,
              checklist: (event.checklist || []).filter((item) => item.id !== itemId),
            }
      )
    );
  }

  function addShoppingPoolItem(eventId?: string) {
    const trimmed = newShoppingPoolItem.trim();
    if (!trimmed || !eventId) return;

    const localItem: ShoppingPoolItem = {
      id: `local-${Date.now()}`,
      label: trimmed,
      done: false,
      linkedEventIds: [eventId],
    };

    setEvents((prev) =>
      prev.map((event) =>
        event.id !== eventId
          ? event
          : {
              ...event,
              shoppingItems: [...(event.shoppingItems || []), localItem],
            }
      )
    );

    setNewShoppingPoolItem('');
  }

  function attachShoppingItemToEvent(eventId: string, itemId: string) {
    setEvents((prev) =>
      prev.map((event) =>
        event.id !== eventId
          ? event
          : {
              ...event,
              linkedShoppingItemIds: event.linkedShoppingItemIds?.includes(itemId)
                ? event.linkedShoppingItemIds
                : [...(event.linkedShoppingItemIds || []), itemId],
            }
      )
    );

    setShoppingPool((prev) =>
      prev.map((item) =>
        item.id !== itemId
          ? item
          : {
              ...item,
              linkedEventIds: item.linkedEventIds.includes(eventId)
                ? item.linkedEventIds
                : [...item.linkedEventIds, eventId],
            }
      )
    );
  }

  function detachShoppingItemFromEvent(eventId: string, itemId: string) {
    setEvents((prev) =>
      prev.map((event) =>
        event.id !== eventId
          ? event
          : {
              ...event,
              linkedShoppingItemIds: (event.linkedShoppingItemIds || []).filter((id) => id !== itemId),
            }
      )
    );

    setShoppingPool((prev) =>
      prev.map((item) =>
        item.id !== itemId
          ? item
          : {
              ...item,
              linkedEventIds: item.linkedEventIds.filter((id) => id !== eventId),
            }
      )
    );
  }

  function toggleShoppingItemDone(itemId: string) {
    setShoppingPool((prev) =>
      prev.map((item) => (item.id === itemId ? { ...item, done: !item.done } : item))
    );
  }

  function removeShoppingItemGlobally(itemId: string) {
    setShoppingPool((prev) => prev.filter((item) => item.id !== itemId));
    setEvents((prev) =>
      prev.map((event) => ({
        ...event,
        linkedShoppingItemIds: (event.linkedShoppingItemIds || []).filter((id) => id !== itemId),
      }))
    );
  }

  function renderMonthGrid() {
    const monthStart = new Date(pickerDate.getFullYear(), pickerDate.getMonth(), 1);
    const gridStart = startOfWeek(monthStart);
    const days = Array.from({ length: 42 }, (_, index) => addDays(gridStart, index));

    return (
      <div className="grid grid-cols-7 gap-2">
        {WEEKDAYS_SHORT.map((day) => (
          <div key={day} className="text-center text-[12px] font-medium text-slate-500">
            {day}
          </div>
        ))}

        {days.map((date) => {
          const dateKey = toDateKey(date);
          const isCurrentMonth = date.getMonth() === pickerDate.getMonth();
          const isSelected = dateKey === effectiveSelectedDate;
          const hasEvents = (eventsByDate[dateKey] || []).length > 0;

          return (
            <button
              key={dateKey}
              type="button"
              onClick={() => applyMonthPicker(date)}
              className={`flex h-10 flex-col items-center justify-center rounded-xl text-[14px] ${
                isSelected
                  ? 'bg-indigo-500 text-white'
                  : isCurrentMonth
                    ? 'bg-slate-50 text-slate-800'
                    : 'bg-slate-50/60 text-slate-400'
              }`}
            >
              <span>{date.getDate()}</span>
              <span className={`mt-1 h-1.5 w-1.5 rounded-full ${hasEvents ? (isSelected ? 'bg-white' : 'bg-indigo-500') : 'bg-transparent'}`} />
            </button>
          );
        })}
      </div>
    );
  }

  return (
    <div className="relative flex h-full flex-col">
      <Header
        title="Kalendarz"
        subtitle={copy.version}
        icon={<Calendar className="h-10 w-10 text-indigo-500" />}
      />

      <div className="-mx-5 mb-4 bg-[linear-gradient(180deg,#edf1f9_0%,#ebedf5_100%)] px-5 py-4">
        <div className="mb-4 flex items-center justify-between">
          <button type="button" onClick={() => goWeek(-1)} className="rounded-full p-1">
            <ChevronLeft className="h-8 w-8 text-indigo-500" />
          </button>
          <button
            type="button"
            onClick={() => setShowMonthPicker(true)}
            className="flex items-center gap-2 text-[24px] font-semibold text-slate-800"
          >
            {formatMonthYear(weekStart)}
            <ChevronDown className="h-6 w-6 text-slate-400" />
          </button>
          <button type="button" onClick={() => goWeek(1)} className="rounded-full p-1">
            <ChevronRightIcon className="h-8 w-8 text-indigo-500" />
          </button>
        </div>

        <div className="rounded-[26px] bg-white/80 p-5 shadow-sm">
          <div className="grid grid-cols-7 text-center">
            {weekDays.map((date) => {
              const dateKey = toDateKey(date);
              const active = dateKey === effectiveSelectedDate;
              const isWeekend = date.getDay() === 0 || date.getDay() === 6;
              const hasEvents = (eventsByDate[dateKey] || []).length > 0;
              const weekdayIndex = date.getDay() === 0 ? 6 : date.getDay() - 1;

              return (
                <button
                  key={dateKey}
                  type="button"
                  onClick={() => setSelectedDate(dateKey)}
                  className="flex flex-col items-center gap-2"
                >
                  <span className={`text-[14px] font-medium ${isWeekend ? 'text-indigo-500' : 'text-slate-700'}`}>
                    {WEEKDAYS_SHORT[weekdayIndex]}
                  </span>
                  <div
                    className={`flex h-12 w-12 items-center justify-center rounded-full text-[18px] ${
                      active
                        ? 'bg-indigo-500 text-white'
                        : isWeekend
                          ? 'text-indigo-500'
                          : 'text-slate-800'
                    }`}
                  >
                    {date.getDate()}
                  </div>
                  <div className={`h-2.5 w-2.5 rounded-full ${hasEvents ? 'bg-indigo-500' : 'bg-transparent'}`} />
                </button>
              );
            })}
          </div>
        </div>

        <div className="mt-4 flex items-center justify-between gap-3">
          <h3 className="text-[22px] font-semibold text-slate-800">{formatDayLabel(effectiveSelectedDate)}</h3>
          <button
            onClick={() => setShowNewEventModal(true)}
            className="flex shrink-0 items-center gap-2 rounded-full bg-[linear-gradient(90deg,#4f75ff,#3b82f6)] px-5 py-3 text-[16px] text-white shadow-sm"
            type="button"
          >
            <Plus className="h-5 w-5" />
            Nowe wydarzenie
          </button>
        </div>
      </div>

      <div className="-mx-5 min-h-0 flex-1 overflow-y-auto bg-white/20 px-5 pb-2">
        {selectedEvents.length === 0 ? (
          <div className="rounded-[24px] bg-white/70 px-5 py-6 text-[16px] text-slate-500 shadow-sm">
            Brak wydarzeń na ten dzień.
          </div>
        ) : (
          <div className="space-y-0">
            {selectedEvents.map((event) => {
              const expanded = expandedEventId === event.id;
              const isShopping = isShoppingEventTitle(event.title);
              const linkedPoolItems = shoppingPool.filter((item) =>
                (event.linkedShoppingItemIds || []).includes(item.id)
              );
              const localEventItems = event.shoppingItems || [];
              const suggestedPoolItems = shoppingPool.filter(
                (item) =>
                  item.linkedEventIds.length === 0 &&
                  !(event.linkedShoppingItemIds || []).includes(item.id)
              );

              return (
                <div key={event.id} className="border-b border-indigo-100 py-4">
                  <button
                    type="button"
                    onClick={() => setExpandedEventId(expanded ? null : event.id)}
                    className="grid w-full grid-cols-[88px_1fr] text-left"
                  >
                    <div className="text-[18px] text-slate-500">{event.time}</div>
                    <div className="flex items-start justify-between gap-4">
                      <div className="min-w-0">
                        <div className="flex items-center gap-3">
                          <div className={`h-5 w-5 shrink-0 rounded-full ${event.dotClass}`} />
                          <div className="text-[18px] font-semibold text-slate-800">{event.title}</div>
                        </div>
                        <div className="ml-8 mt-2 flex items-center gap-2 text-[14px] text-slate-500">
                          <MapPin className="h-4 w-4" />
                          <span className="truncate">{event.location}</span>
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        <div className={`shrink-0 rounded-xl px-3 py-1.5 text-[14px] font-medium ${event.badgeClass}`}>
                          {event.badge}
                        </div>
                        {expanded ? (
                          <ChevronUp className="h-5 w-5 text-slate-400" />
                        ) : (
                          <ChevronDown className="h-5 w-5 text-slate-400" />
                        )}
                      </div>
                    </div>
                  </button>

                  {expanded ? (
                    <div className="ml-[88px] mt-4 rounded-[20px] bg-white/70 p-4 shadow-sm">
                      <div className="space-y-4">
                        <div>
                          <div className="mb-1 text-[13px] font-semibold uppercase tracking-wide text-slate-400">
                            Miejsce
                          </div>
                          <div className="text-[15px] text-slate-700">{event.location}</div>
                        </div>

                        <div>
                          <div className="mb-1 text-[13px] font-semibold uppercase tracking-wide text-slate-400">
                            Notatka
                          </div>
                          <div className="text-[15px] text-slate-700">
                            {event.note?.trim() ? event.note : 'Brak notatki.'}
                          </div>
                        </div>

                        {!isShopping ? (
                          <div>
                            <div className="mb-2 text-[13px] font-semibold uppercase tracking-wide text-slate-400">
                              Checklista
                            </div>
                            <div className="space-y-2">
                              {event.checklist && event.checklist.length > 0 ? (
                                event.checklist.map((item) => (
                                  <div
                                    key={item.id}
                                    className="flex items-center justify-between gap-3 rounded-2xl bg-slate-50 px-3 py-2"
                                  >
                                    <button
                                      type="button"
                                      onClick={() => toggleChecklistItem(event.id, item.id)}
                                      className="flex min-w-0 items-center gap-3 text-left text-[15px] text-slate-700"
                                    >
                                      {item.done ? (
                                        <Check className="h-4 w-4 shrink-0 text-indigo-500" />
                                      ) : (
                                        <Square className="h-4 w-4 shrink-0 text-slate-400" />
                                      )}
                                      <span className={item.done ? 'line-through text-slate-400' : ''}>
                                        {item.label}
                                      </span>
                                    </button>

                                    <button
                                      type="button"
                                      onClick={() => removeChecklistItem(event.id, item.id)}
                                      className="rounded-full bg-rose-50 p-2 text-rose-500"
                                      title="Usuń z checklisty"
                                    >
                                      <Trash2 className="h-4 w-4" />
                                    </button>
                                  </div>
                                ))
                              ) : (
                                <div className="text-[15px] text-slate-500">Brak checklisty.</div>
                              )}
                            </div>
                          </div>
                        ) : (
                          <div>
                            <div className="mb-2 text-[13px] font-semibold uppercase tracking-wide text-slate-400">
                              Lista zakupów dla tego wydarzenia
                            </div>

                            <div className="space-y-2">
                              {linkedPoolItems.length > 0 || localEventItems.length > 0 ? (
                                <>
                                  {localEventItems.map((item) => (
                                    <div
                                      key={item.id}
                                      className="rounded-2xl bg-slate-50 px-3 py-2"
                                    >
                                      <div className="flex items-center justify-between gap-3">
                                        <button
                                          type="button"
                                          onClick={() =>
                                            setEvents((prev) =>
                                              prev.map((currentEvent) =>
                                                currentEvent.id !== event.id
                                                  ? currentEvent
                                                  : {
                                                      ...currentEvent,
                                                      shoppingItems: (currentEvent.shoppingItems || []).map(
                                                        (shoppingItem) =>
                                                          shoppingItem.id === item.id
                                                            ? {
                                                                ...shoppingItem,
                                                                done: !shoppingItem.done,
                                                              }
                                                            : shoppingItem
                                                      ),
                                                    }
                                              )
                                            )
                                          }
                                          className="flex min-w-0 items-center gap-3 text-left text-[15px] text-slate-700"
                                        >
                                          {item.done ? (
                                            <Check className="h-4 w-4 shrink-0 text-indigo-500" />
                                          ) : (
                                            <Square className="h-4 w-4 shrink-0 text-slate-400" />
                                          )}
                                          <span className={item.done ? 'line-through text-slate-400' : ''}>
                                            {item.label}
                                          </span>
                                        </button>

                                        <div className="flex items-center gap-2">
                                          <button
                                            type="button"
                                            onClick={() => {
                                              setEvents((prev) =>
                                                prev.map((currentEvent) =>
                                                  currentEvent.id !== event.id
                                                    ? currentEvent
                                                    : {
                                                        ...currentEvent,
                                                        shoppingItems: (currentEvent.shoppingItems || []).filter(
                                                          (shoppingItem) => shoppingItem.id !== item.id
                                                        ),
                                                      }
                                                )
                                              );

                                              setShoppingPool((prev) => {
                                                const exists = prev.some(
                                                  (shoppingItem) =>
                                                    shoppingItem.label.toLowerCase() === item.label.toLowerCase() &&
                                                    shoppingItem.linkedEventIds.length === 0
                                                );

                                                if (exists) {
                                                  return prev;
                                                }

                                                return [
                                                  ...prev,
                                                  {
                                                    id: `pool-${Date.now()}`,
                                                    label: item.label,
                                                    done: item.done,
                                                    linkedEventIds: [],
                                                  },
                                                ];
                                              });
                                            }}
                                            className="rounded-full bg-amber-50 p-2 text-amber-600"
                                            title="Odepnij do ogólnej listy zakupów"
                                          >
                                            <Unlink className="h-4 w-4" />
                                          </button>

                                          <button
                                            type="button"
                                            onClick={() =>
                                              setEvents((prev) =>
                                                prev.map((currentEvent) =>
                                                  currentEvent.id !== event.id
                                                    ? currentEvent
                                                    : {
                                                        ...currentEvent,
                                                        shoppingItems: (currentEvent.shoppingItems || []).filter(
                                                          (shoppingItem) => shoppingItem.id !== item.id
                                                        ),
                                                      }
                                                )
                                              )
                                            }
                                            className="rounded-full bg-rose-50 p-2 text-rose-500"
                                            title="Usuń z tego wydarzenia"
                                          >
                                            <Trash2 className="h-4 w-4" />
                                          </button>
                                        </div>
                                      </div>
                                    </div>
                                  ))}

                                  {linkedPoolItems.map((item) => (
                                  <div
                                    key={item.id}
                                    className="rounded-2xl bg-slate-50 px-3 py-2"
                                  >
                                    <div className="flex items-center justify-between gap-3">
                                      <button
                                        type="button"
                                        onClick={() => toggleShoppingItemDone(item.id)}
                                        className="flex min-w-0 items-center gap-3 text-left text-[15px] text-slate-700"
                                      >
                                        {item.done ? (
                                          <Check className="h-4 w-4 shrink-0 text-indigo-500" />
                                        ) : (
                                          <Square className="h-4 w-4 shrink-0 text-slate-400" />
                                        )}
                                        <span className={item.done ? 'line-through text-slate-400' : ''}>
                                          {item.label}
                                        </span>
                                      </button>

                                      <div className="flex items-center gap-2">
                                        <button
                                          type="button"
                                          onClick={() => detachShoppingItemFromEvent(event.id, item.id)}
                                          className="rounded-full bg-amber-50 p-2 text-amber-600"
                                          title="Odepnij od wydarzenia"
                                        >
                                          <Unlink className="h-4 w-4" />
                                        </button>

                                        <button
                                          type="button"
                                          onClick={() => removeShoppingItemGlobally(item.id)}
                                          className="rounded-full bg-rose-50 p-2 text-rose-500"
                                          title="Usuń z listy zakupów"
                                        >
                                          <Trash2 className="h-4 w-4" />
                                        </button>
                                      </div>
                                    </div>
                                  </div>
                                ))}
                                </>
                              ) : (
                                <div className="text-[15px] text-slate-500">Brak przypiętych produktów.</div>
                              )}
                            </div>

                            <div className="mt-4">
                              <div className="mb-2 text-[13px] font-semibold uppercase tracking-wide text-slate-400">
                                Sugerowane z listy zakupów
                              </div>

                              <div className="space-y-2">
                                {suggestedPoolItems.length > 0 ? (
                                  suggestedPoolItems.map((item) => (
                                    <div key={item.id} className="flex items-center justify-between gap-3 rounded-2xl bg-slate-50 px-3 py-2">
                                      <span className="text-[14px] text-slate-700">{item.label}</span>
                                      <div className="flex items-center gap-2">
                                        <button
                                          type="button"
                                          onClick={() => attachShoppingItemToEvent(event.id, item.id)}
                                          className="rounded-full bg-indigo-100 px-3 py-1 text-[13px] font-medium text-indigo-600"
                                        >
                                          Dodaj
                                        </button>
                                        <button
                                          type="button"
                                          onClick={() => removeShoppingItemGlobally(item.id)}
                                          className="rounded-full bg-rose-50 p-2 text-rose-500"
                                          title="Usuń z listy zakupów"
                                        >
                                          <Trash2 className="h-4 w-4" />
                                        </button>
                                      </div>
                                    </div>
                                  ))
                                ) : (
                                  <div className="text-[15px] text-slate-500">Brak dodatkowych sugestii.</div>
                                )}
                              </div>
                            </div>

                            <div className="mt-4">
                              <div className="mb-2 text-[13px] font-semibold uppercase tracking-wide text-slate-400">
                                Dodaj do listy zakupów
                              </div>
                              <div className="flex items-center gap-2">
                                <input
                                  value={newShoppingPoolItem}
                                  onChange={(e) => setNewShoppingPoolItem(e.target.value)}
                                  className="flex-1 rounded-2xl border border-slate-200 px-4 py-2.5 text-[14px] outline-none"
                                  placeholder="Np. Płyn do naczyń"
                                />
                                <button
                                  type="button"
                                  onClick={() => addShoppingPoolItem(event.id)}
                                  className="rounded-full bg-[linear-gradient(90deg,#4f75ff,#3b82f6)] px-4 py-2.5 text-[14px] text-white"
                                >
                                  Dodaj
                                </button>
                              </div>
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  ) : null}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {showMonthPicker ? (
        <div className="absolute inset-0 z-30 flex items-center justify-center bg-slate-900/20 px-4">
          <div className="w-full max-w-[360px] rounded-[28px] bg-white p-5 shadow-[0_20px_60px_rgba(15,23,42,0.18)]">
            <div className="mb-4 flex items-center justify-between">
              <div className="text-[20px] font-semibold text-slate-800">Wybierz miesiąc</div>
              <button type="button" onClick={() => setShowMonthPicker(false)}>
                <X className="h-5 w-5 text-slate-400" />
              </button>
            </div>

            <div className="mb-4 flex items-center justify-between gap-3">
              <button
                type="button"
                onClick={() => setPickerDate(new Date(pickerDate.getFullYear() - 1, pickerDate.getMonth(), 1))}
                className="rounded-full bg-slate-100 px-3 py-2 text-[14px] text-slate-700"
              >
                - Rok
              </button>

              <div className="text-[18px] font-semibold text-slate-800">
                {MONTHS_PL[pickerDate.getMonth()]} {pickerDate.getFullYear()}
              </div>

              <button
                type="button"
                onClick={() => setPickerDate(new Date(pickerDate.getFullYear() + 1, pickerDate.getMonth(), 1))}
                className="rounded-full bg-slate-100 px-3 py-2 text-[14px] text-slate-700"
              >
                + Rok
              </button>
            </div>

            <div className="mb-4 grid grid-cols-3 gap-2">
              {MONTHS_PL.map((month, index) => (
                <button
                  key={month}
                  type="button"
                  onClick={() => setPickerDate(new Date(pickerDate.getFullYear(), index, 1))}
                  className={`rounded-2xl px-3 py-2 text-[14px] ${
                    pickerDate.getMonth() === index
                      ? 'bg-indigo-500 text-white'
                      : 'bg-slate-100 text-slate-700'
                  }`}
                >
                  {month}
                </button>
              ))}
            </div>

            {renderMonthGrid()}
          </div>
        </div>
      ) : null}

      {showNewEventModal ? (
        <div className="absolute inset-0 z-30 flex items-center justify-center bg-slate-900/20 px-4">
          <div className="max-h-[88%] w-full max-w-[370px] overflow-y-auto rounded-[28px] bg-white p-5 shadow-[0_20px_60px_rgba(15,23,42,0.18)]">
            <div className="mb-4 flex items-center justify-between">
              <div>
                <div className="text-[20px] font-semibold text-slate-800">Nowe wydarzenie</div>
                <div className="mt-1 text-[14px] text-slate-500">{formatDayLabel(effectiveSelectedDate)}</div>
              </div>
              <button type="button" onClick={() => setShowNewEventModal(false)}>
                <X className="h-5 w-5 text-slate-400" />
              </button>
            </div>

            <div className="space-y-3">
              <label className="block">
                <div className="mb-1 text-[13px] font-medium text-slate-500">Tytuł</div>
                <input
                  value={newEventTitle}
                  onChange={(e) => setNewEventTitle(e.target.value)}
                  className="w-full rounded-2xl border border-slate-200 px-4 py-3 text-[15px] outline-none"
                  placeholder="Np. Zakupy w Biedronce"
                />
              </label>

              <div className="grid grid-cols-2 gap-3">
                <label className="block">
                  <div className="mb-1 text-[13px] font-medium text-slate-500">Godzina</div>
                  <input
                    type="time"
                    value={newEventTime}
                    onChange={(e) => setNewEventTime(e.target.value)}
                    className="w-full rounded-2xl border border-slate-200 px-4 py-3 text-[15px] outline-none"
                  />
                </label>

                <label className="block">
                  <div className="mb-1 text-[13px] font-medium text-slate-500">Miejsce</div>
                  <input
                    value={newEventLocation}
                    onChange={(e) => setNewEventLocation(e.target.value)}
                    className="w-full rounded-2xl border border-slate-200 px-4 py-3 text-[15px] outline-none"
                    placeholder="Np. Lidl / Dom / Online"
                  />
                </label>
              </div>

              <label className="block">
                <div className="mb-1 text-[13px] font-medium text-slate-500">Notatka</div>
                <textarea
                  value={newEventNote}
                  onChange={(e) => setNewEventNote(e.target.value)}
                  className="min-h-[90px] w-full rounded-2xl border border-slate-200 px-4 py-3 text-[15px] outline-none"
                  placeholder="Krótka notatka do wydarzenia"
                />
              </label>

              {!isShoppingEventTitle(newEventTitle) ? (
                <label className="block">
                  <div className="mb-1 text-[13px] font-medium text-slate-500">Checklista</div>
                  <textarea
                    value={newEventChecklist}
                    onChange={(e) => setNewEventChecklist(e.target.value)}
                    className="min-h-[90px] w-full rounded-2xl border border-slate-200 px-4 py-3 text-[15px] outline-none"
                    placeholder="Jedna pozycja w linii&#10;Np. Kupić bilet&#10;Sprawdzić agendę"
                  />
                </label>
              ) : (
                <div className="rounded-2xl bg-rose-50 px-4 py-3 text-[14px] text-rose-700">
                  Dla wydarzeń zakupowych nie pokazujemy checklisty. Zamiast tego po utworzeniu pojawi się lista zakupów z sugestiami ze wspólnej listy.
                </div>
              )}
            </div>

            <div className="mt-5 flex items-center justify-end gap-3">
              <button
                type="button"
                onClick={() => setShowNewEventModal(false)}
                className="rounded-full bg-slate-100 px-4 py-2.5 text-[15px] text-slate-700"
              >
                Anuluj
              </button>
              <button
                type="button"
                onClick={createEvent}
                className="rounded-full bg-[linear-gradient(90deg,#4f75ff,#3b82f6)] px-5 py-2.5 text-[15px] text-white"
              >
                Dodaj wydarzenie
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}

function ProjectsScreen({
  projectItems,
  setProjectItems,
  shoppingPool,
  setShoppingPool,
}: {
  projectItems: ProjectItem[];
  setProjectItems: React.Dispatch<React.SetStateAction<ProjectItem[]>>;
  shoppingPool: ShoppingPoolItem[];
  setShoppingPool: React.Dispatch<React.SetStateAction<ShoppingPoolItem[]>>;
}) {
  const [newProjectItem, setNewProjectItem] = useState('');
  const [pickingId, setPickingId] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  function addChecklist(taskId: string, label: string) {
    setProjectItems((prev) =>
      prev.map((i) =>
        i.id === taskId
          ? {
              ...i,
              checklist: [
                ...i.checklist,
                { id: `chk-${Date.now()}`, label, done: false },
              ],
            }
          : i
      )
    );
  }

  function toggleChecklist(taskId: string, chkId: string) {
    setProjectItems((prev) =>
      prev.map((i) =>
        i.id === taskId
          ? {
              ...i,
              checklist: i.checklist.map((c) =>
                c.id === chkId ? { ...c, done: !c.done } : c
              ),
            }
          : i
      )
    );
  }

  function removeChecklist(taskId: string, chkId: string) {
    setProjectItems((prev) =>
      prev.map((i) =>
        i.id === taskId
          ? { ...i, checklist: i.checklist.filter((c) => c.id !== chkId) }
          : i
      )
    );
  }

  function toggleShopping(poolId: string) {
    setShoppingPool((prev) => prev.filter((p) => p.id !== poolId));
  }

  function setDueAt(id: string, nextDate: string | null, nextTime: string | null) {
    setProjectItems((prev) =>
      prev.map((item) =>
        item.id === id ? { ...item, dueAt: nextDate, time: nextTime } : item
      )
    );
  }

  function addManualProjectItem() {
    const trimmed = newProjectItem.trim();
    if (!trimmed) return;

    setProjectItems((prev) => [
      ...prev,
      {
        id: `project-${Date.now()}`,
        label: trimmed,
        category: extractProjectCategoryFromChat(trimmed),
        done: false,
        source: 'manual',
        dueAt: null,
        time: null,
        checklist: [],
      },
    ]);

    setNewProjectItem('');
  }

  function toggleProjectItem(itemId: string) {
    setProjectItems((prev) =>
      prev.map((item) => (item.id === itemId ? { ...item, done: !item.done } : item))
    );
  }

  function removeProjectItem(itemId: string) {
    setProjectItems((prev) => prev.filter((item) => item.id !== itemId));
  }

  const groups = useMemo(() => {
    const categories: ProjectCategory[] = ['general', 'shopping', 'ideas', 'reading', 'to_check'];

    return categories.map((category) => {
      const items = projectItems.filter((item) => item.category === category);

      const icon =
        category === 'shopping' ? (
          <ShoppingCart className="h-4 w-4 text-indigo-400" />
        ) : category === 'reading' ? (
          <BookOpen className="h-4 w-4 text-indigo-400" />
        ) : category === 'ideas' ? (
          <Lightbulb className="h-4 w-4 text-indigo-400" />
        ) : category === 'to_check' ? (
          <Search className="h-4 w-4 text-indigo-400" />
        ) : (
          <Box className="h-4 w-4 text-indigo-400" />
        );

      return {
        key: category,
        title: projectCategoryLabel(category),
        count: String(items.length),
        icon,
        items,
      };
    });
  }, [projectItems]);

  return (
    <div className="flex h-full flex-col">
      <Header title="Projekty" subtitle={copy.version} icon={<Package className="h-10 w-10 text-indigo-300" />} />

      <div className="mb-3 rounded-[18px] bg-white/75 p-3 shadow-sm">
        <div className="flex items-center gap-2">
          <input
            value={newProjectItem}
            onChange={(e) => setNewProjectItem(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                e.preventDefault();
                addManualProjectItem();
              }
            }}
            className="flex-1 rounded-2xl border border-slate-200 px-4 py-2.5 text-[14px] outline-none"
            placeholder="Nowy projekt..."
          />
          <button
            type="button"
            onClick={addManualProjectItem}
            className="rounded-full bg-[linear-gradient(90deg,#4f75ff,#3b82f6)] px-4 py-2.5 text-[13px] font-semibold text-white"
          >
            Dodaj
          </button>
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto pr-1 pb-6">
        <div className="mb-3 text-[13px] leading-5 text-slate-500">
          Pomysły i zadania pogrupowane wg kategorii. Strzałka — przenieś na inny dzień. Ptaszek — zrobione. Krzyżyk — usuń.
        </div>

        <div className="space-y-4">
          {groups.map((group) => (
            <div key={group.key}>
              <div className="mb-2 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-indigo-400">{group.icon}</span>
                  <div className="text-[15px] font-bold text-slate-800">{group.title}</div>
                </div>
                {group.items.length > 0 ? (
                  <div className="text-[12px] text-slate-400">
                    {group.items.length} {pluralPL(group.items.length, ['pozycja', 'pozycje', 'pozycji'])}
                  </div>
                ) : null}
              </div>

              {group.items.length === 0 ? (
                <div className="rounded-[14px] bg-white/40 px-3 py-2 text-[12px] text-slate-400">
                  Brak pozycji w tej kategorii.
                </div>
              ) : (
                <div className="space-y-2">
                  {group.items.map((item) => (
                    <TaskRow
                      key={item.id}
                      item={item}
                      onToggle={() => toggleProjectItem(item.id)}
                      onPickDate={() => setPickingId(item.id)}
                      onDelete={() => removeProjectItem(item.id)}
                      expanded={expandedId === item.id}
                      onToggleExpand={() =>
                        setExpandedId((cur) => (cur === item.id ? null : item.id))
                      }
                      shoppingPool={shoppingPool}
                      onShoppingToggle={toggleShopping}
                      onChecklistAdd={(label) => addChecklist(item.id, label)}
                      onChecklistToggle={(chkId) => toggleChecklist(item.id, chkId)}
                      onChecklistRemove={(chkId) => removeChecklist(item.id, chkId)}
                    />
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {pickingId ? (() => {
        const item = projectItems.find((i) => i.id === pickingId);
        if (!item) return null;
        return (
          <DatePickerPopup
            value={item.dueAt}
            valueTime={item.time}
            onChange={(d, t) => setDueAt(item.id, d, t)}
            onClose={() => setPickingId(null)}
          />
        );
      })() : null}
    </div>
  );
}

function ToggleRow({
  icon,
  title,
  checked,
  onChange,
}: {
  icon: React.ReactNode;
  title: string;
  checked: boolean;
  onChange: (next: boolean) => void;
}) {
  return (
    <button
      type="button"
      onClick={() => onChange(!checked)}
      className="flex w-full items-center justify-between px-3 py-4 text-left"
    >
      <div className="flex items-center gap-4 min-w-0">
        {icon}
        <span className="text-[18px] text-slate-700">{title}</span>
      </div>

      <div
        className={`flex h-9 w-20 shrink-0 items-center rounded-full px-1 transition-colors ${
          checked ? 'bg-indigo-400' : 'bg-slate-300'
        }`}
      >
        <div
          className={`flex h-7 w-7 items-center justify-center rounded-full bg-white text-indigo-400 ${
            checked ? 'ml-auto' : ''
          }`}
        >
          {checked ? <Check className="h-4 w-4" /> : null}
        </div>
      </div>
    </button>
  );
}

type SettingsPath =
  | 'root'
  | 'account'
  | 'profile'
  | 'security'
  | 'plan'
  | 'integrations'
  | 'data';

function SubHeader({ title, onBack }: { title: string; onBack: () => void }) {
  return (
    <div className="flex items-center gap-3 py-4">
      <button
        type="button"
        onClick={onBack}
        className="flex h-10 w-10 items-center justify-center rounded-full bg-white/70 shadow-sm"
        aria-label="Wstecz"
      >
        <ChevronLeft className="h-6 w-6 text-slate-700" />
      </button>
      <div className="text-[24px] font-semibold text-slate-800">{title}</div>
    </div>
  );
}

function FormField({
  label,
  value,
  onChange,
  type = 'text',
  placeholder,
  autoComplete,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  type?: string;
  placeholder?: string;
  autoComplete?: string;
}) {
  return (
    <div>
      <label className="mb-1 block text-[13px] font-medium text-slate-500">{label}</label>
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        type={type}
        placeholder={placeholder}
        autoCapitalize={type === 'email' || type === 'password' ? 'off' : undefined}
        autoCorrect="off"
        spellCheck={false}
        autoComplete={autoComplete}
        className="w-full rounded-[14px] border border-slate-200 bg-white px-3 py-2 text-[15px] text-slate-700 outline-none focus:border-indigo-300"
      />
    </div>
  );
}

function AccountScreen({
  onBack,
  onNavigate,
}: {
  onBack: () => void;
  onNavigate: (p: SettingsPath) => void;
}) {
  const [profile] = useState(() => readProfile());
  const [logoutHint, setLogoutHint] = useState('');

  const fullName =
    [profile.firstName, profile.lastName].filter((v) => v.trim()).join(' ').trim() ||
    'Ustaw imię w Profilu';
  const initials = getInitials(profile);

  const rows: {
    key: SettingsPath;
    icon: React.ReactNode;
    title: string;
    desc: string;
  }[] = [
    {
      key: 'profile',
      icon: <UserCircle2 className="h-8 w-8 text-indigo-300" />,
      title: 'Profil',
      desc: 'Imię, email, zdjęcie',
    },
    {
      key: 'security',
      icon: <Shield className="h-8 w-8 text-indigo-300" />,
      title: 'Bezpieczeństwo',
      desc: 'Hasło, 2FA, aktywne sesje',
    },
    {
      key: 'plan',
      icon: <CreditCard className="h-8 w-8 text-indigo-300" />,
      title: 'Plan i płatności',
      desc: 'Free • zarządzaj subskrypcją',
    },
    {
      key: 'integrations',
      icon: <Link2 className="h-8 w-8 text-indigo-300" />,
      title: 'Integracje',
      desc: 'Google Calendar, Drive, Slack',
    },
    {
      key: 'data',
      icon: <Database className="h-8 w-8 text-indigo-300" />,
      title: 'Dane i prywatność',
      desc: 'Eksport, import, usuń konto',
    },
  ];

  return (
    <div className="flex h-full flex-col">
      <SubHeader title="Moje konto" onBack={onBack} />

      <div className="min-h-0 flex-1 overflow-y-auto pr-1 pb-6">
        <div className="rounded-[22px] bg-white/75 p-5 shadow-sm">
          <div className="flex items-center gap-4">
            <div className="flex h-20 w-20 shrink-0 items-center justify-center rounded-full bg-[linear-gradient(180deg,#7196ff_0%,#4f75ff_100%)] text-[26px] font-bold text-white">
              {initials}
            </div>
            <div className="min-w-0 flex-1">
              <div className="truncate text-[18px] font-semibold text-slate-800">{fullName}</div>
              <div className="mt-0.5 truncate text-[14px] text-slate-500">
                {profile.email || 'Brak adresu email'}
              </div>
              <span className="mt-2 inline-block rounded-full bg-indigo-100 px-3 py-0.5 text-[12px] font-semibold text-indigo-600">
                Free
              </span>
            </div>
          </div>
        </div>

        <div className="mt-4 rounded-[22px] bg-white/75 p-3 shadow-sm">
          {rows.map((row, i) => (
            <button
              key={row.key}
              type="button"
              onClick={() => onNavigate(row.key)}
              className={`flex w-full items-center justify-between gap-3 px-3 py-4 text-left ${
                i < rows.length - 1 ? 'border-b border-slate-200' : ''
              }`}
            >
              <div className="flex min-w-0 items-center gap-4">
                {row.icon}
                <div className="min-w-0">
                  <div className="text-[17px] text-slate-700">{row.title}</div>
                  <div className="text-[13px] text-slate-500">{row.desc}</div>
                </div>
              </div>
              <ChevronRight className="h-7 w-7 shrink-0 text-indigo-300" />
            </button>
          ))}
        </div>

        <button
          type="button"
          onClick={() => setLogoutHint('Wkrótce — wymaga backendu z logowaniem.')}
          className="mt-5 flex w-full items-center justify-center gap-2 rounded-[18px] bg-rose-50 px-4 py-3 text-[15px] font-semibold text-rose-600"
        >
          <LogOut className="h-5 w-5" />
          Wyloguj
        </button>
        {logoutHint ? (
          <div className="mt-2 rounded-[14px] bg-white/60 px-4 py-2 text-center text-[13px] text-slate-600">
            {logoutHint}
          </div>
        ) : null}
      </div>
    </div>
  );
}

function ProfileScreen({ onBack }: { onBack: () => void }) {
  const [p, setP] = useState<UserProfile>(() => readProfile());
  const [hint, setHint] = useState('');

  function save() {
    const trimmed: UserProfile = {
      firstName: p.firstName.trim(),
      lastName: p.lastName.trim(),
      email: p.email.trim(),
    };
    writeProfile(trimmed);
    setP(trimmed);
    setHint('Zapisano.');
    window.setTimeout(() => setHint(''), 2000);
  }

  const initials = getInitials(p);

  return (
    <div className="flex h-full flex-col">
      <SubHeader title="Profil" onBack={onBack} />

      <div className="min-h-0 flex-1 overflow-y-auto pr-1 pb-6">
        <div className="flex flex-col items-center">
          <div className="flex h-24 w-24 items-center justify-center rounded-full bg-[linear-gradient(180deg,#7196ff_0%,#4f75ff_100%)] text-[34px] font-bold text-white">
            {initials}
          </div>
          <button
            type="button"
            disabled
            className="mt-3 cursor-not-allowed rounded-full bg-slate-100 px-4 py-2 text-[13px] font-medium text-slate-400"
          >
            Zmień zdjęcie (wkrótce)
          </button>
        </div>

        <div className="mt-5 space-y-3 rounded-[22px] bg-white/75 p-4 shadow-sm">
          <FormField
            label="Imię"
            value={p.firstName}
            onChange={(v) => setP({ ...p, firstName: v })}
            placeholder="Imię"
          />
          <FormField
            label="Nazwisko"
            value={p.lastName}
            onChange={(v) => setP({ ...p, lastName: v })}
            placeholder="Nazwisko"
          />
          <FormField
            label="Email"
            type="email"
            value={p.email}
            onChange={(v) => setP({ ...p, email: v })}
            placeholder="ja@example.com"
          />
        </div>

        <button
          type="button"
          onClick={save}
          className="mt-4 w-full rounded-full bg-[linear-gradient(90deg,#4f75ff,#3b82f6)] px-4 py-3 text-[15px] font-semibold text-white"
        >
          Zapisz
        </button>
        {hint ? (
          <div className="mt-2 text-center text-[13px] text-slate-500">{hint}</div>
        ) : null}
      </div>
    </div>
  );
}

function NotificationsScreen({
  notifications,
  readIds,
  onMarkAsRead,
  onMarkAllRead,
  onDismiss,
  onClearAll,
  onClose,
}: {
  notifications: AppNotification[];
  readIds: string[];
  onMarkAsRead: (id: string) => void;
  onMarkAllRead: () => void;
  onDismiss: (id: string) => void;
  onClearAll: () => void;
  onClose: () => void;
}) {
  const readSet = new Set(readIds);
  const unreadCount = notifications.filter((n) => !readSet.has(n.id)).length;

  const kindMeta: Record<NotificationKind, { label: string; color: string; Icon: React.ElementType }> = {
    reminder: { label: 'Przypomnienie', color: '#F59E0B', Icon: Bell },
    task: { label: 'Zadanie', color: '#4F75FF', Icon: CheckSquare },
    ai: { label: 'Jarvis', color: '#8B5CF6', Icon: Lightbulb },
    integration: { label: 'Integracja', color: '#10B981', Icon: Link2 },
  };

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between gap-3 py-4">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={onClose}
            className="flex h-10 w-10 items-center justify-center rounded-full bg-white/70 shadow-sm"
            aria-label="Zamknij"
          >
            <ChevronLeft className="h-6 w-6 text-slate-700" />
          </button>
          <div className="text-[24px] font-semibold text-slate-800">Powiadomienia</div>
        </div>
        {unreadCount > 0 ? (
          <button
            type="button"
            onClick={onMarkAllRead}
            className="rounded-full bg-white/70 px-3 py-1.5 text-[12px] font-semibold text-indigo-600"
          >
            Oznacz jako przeczytane
          </button>
        ) : null}
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto pr-1 pb-6">
        {notifications.length === 0 ? (
          <div className="rounded-[22px] bg-white/60 p-6 text-center">
            <Bell className="mx-auto h-8 w-8 text-slate-400" />
            <div className="mt-2 text-[14px] font-semibold text-slate-700">Brak powiadomień</div>
            <div className="mt-1 text-[12px] leading-5 text-slate-500">
              Tu zobaczysz przypomnienia o wydarzeniach, nowe zadania i sugestie Jarvisa.
            </div>
          </div>
        ) : (
          <div className="space-y-2">
            {notifications.map((n) => {
              const isUnread = !readSet.has(n.id);
              const meta = kindMeta[n.kind];
              return (
                <div
                  key={n.id}
                  className={`flex items-start gap-3 rounded-[18px] px-4 py-3 shadow-sm transition ${
                    isUnread ? 'bg-white' : 'bg-white/50'
                  }`}
                >
                  <button
                    type="button"
                    onClick={() => isUnread && onMarkAsRead(n.id)}
                    className="flex min-w-0 flex-1 items-start gap-3 text-left"
                  >
                    <div
                      className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full"
                      style={{ backgroundColor: `${meta.color}20` }}
                    >
                      <meta.Icon className="h-5 w-5" color={meta.color} />
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-start gap-2">
                        <div
                          className={`min-w-0 flex-1 text-[14px] ${
                            isUnread ? 'font-semibold text-slate-800' : 'font-medium text-slate-600'
                          }`}
                        >
                          {n.title}
                        </div>
                        {isUnread ? (
                          <div className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-indigo-500" />
                        ) : null}
                      </div>
                      <div className="mt-0.5 text-[13px] leading-5 text-slate-500">{n.body}</div>
                      <div className="mt-1 flex items-center gap-2 text-[11px] text-slate-400">
                        <span
                          className="rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide"
                          style={{ backgroundColor: `${meta.color}18`, color: meta.color }}
                        >
                          {meta.label}
                        </span>
                        <span>•</span>
                        <span>{n.time}</span>
                      </div>
                    </div>
                  </button>
                  <button
                    type="button"
                    onClick={() => onDismiss(n.id)}
                    className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-slate-400 transition hover:bg-slate-100 hover:text-slate-600"
                    aria-label="Usuń powiadomienie"
                  >
                    <X className="h-4 w-4" />
                  </button>
                </div>
              );
            })}

            <button
              type="button"
              onClick={onClearAll}
              className="mt-2 flex w-full items-center justify-center gap-2 rounded-[18px] bg-rose-50 px-4 py-3 text-[13px] font-semibold text-rose-600"
            >
              <Trash2 className="h-4 w-4" />
              Wyczyść wszystkie
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

type Integration = {
  id: string;
  name: string;
  description: string;
  Icon: IconType;
  color: string;
};

function IntegrationsScreen({ onBack }: { onBack: () => void }) {
  const [hint, setHint] = useState('');
  const [hintTone, setHintTone] = useState<'info' | 'success' | 'error'>('info');

  function showHint(m: string, t: 'info' | 'success' | 'error' = 'info') {
    setHint(m);
    setHintTone(t);
  }

  const categories: { title: string; items: Integration[] }[] = [
    {
      title: 'Kalendarze',
      items: [
        {
          id: 'google_calendar',
          name: 'Google Calendar',
          description: 'Dwukierunkowa synchronizacja wydarzeń',
          Icon: SiGooglecalendar,
          color: '#4285F4',
        },
        {
          id: 'apple_calendar',
          name: 'Apple Calendar',
          description: 'Synchronizacja z iCloud',
          Icon: SiApple,
          color: '#111111',
        },
        {
          id: 'outlook',
          name: 'Microsoft Outlook',
          description: 'Kalendarz z Microsoft 365',
          Icon: FaMicrosoft,
          color: '#0078D4',
        },
      ],
    },
    {
      title: 'Pliki i notatki',
      items: [
        {
          id: 'google_drive',
          name: 'Google Drive',
          description: 'Załączniki i pliki do zadań',
          Icon: SiGoogledrive,
          color: '#1FA463',
        },
        {
          id: 'notion',
          name: 'Notion',
          description: 'Importuj strony jako zadania',
          Icon: SiNotion,
          color: '#111111',
        },
      ],
    },
    {
      title: 'Komunikacja',
      items: [
        {
          id: 'slack',
          name: 'Slack',
          description: 'Powiadomienia i szybkie dodawanie zadań',
          Icon: SiSlack,
          color: '#4A154B',
        },
      ],
    },
  ];

  function connect(name: string) {
    showHint(`Wkrótce — połączenie z ${name} przez OAuth wymaga backendu.`, 'info');
  }

  const hintClass =
    hintTone === 'success'
      ? 'bg-emerald-50 text-emerald-700'
      : hintTone === 'error'
      ? 'bg-rose-50 text-rose-600'
      : 'bg-white/70 text-slate-600';

  return (
    <div className="flex h-full flex-col">
      <SubHeader title="Integracje" onBack={onBack} />

      <div className="min-h-0 flex-1 overflow-y-auto pr-1 pb-6">
        <div className="rounded-[22px] bg-white/60 p-4 text-[13px] leading-5 text-slate-600">
          Połącz Jarvisa z aplikacjami, których używasz na co dzień. Uwierzytelnianie przez OAuth — nigdy nie pytamy o Twoje hasła.
        </div>

        {categories.map((cat) => (
          <div key={cat.title}>
            <h3 className="mt-6 mb-2 text-[15px] font-semibold text-slate-700">{cat.title}</h3>
            <div className="rounded-[22px] bg-white/75 p-3 shadow-sm">
              {cat.items.map((it, i) => (
                <div
                  key={it.id}
                  className={`flex items-center gap-3 px-2 py-3 ${
                    i < cat.items.length - 1 ? 'border-b border-slate-200' : ''
                  }`}
                >
                  <div
                    className="flex h-11 w-11 shrink-0 items-center justify-center rounded-[14px]"
                    style={{ backgroundColor: `${it.color}15` }}
                  >
                    <it.Icon size={22} color={it.color} />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <div className="truncate text-[15px] font-semibold text-slate-800">
                        {it.name}
                      </div>
                      <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-slate-500">
                        Niepołączone
                      </span>
                    </div>
                    <div className="truncate text-[12px] text-slate-500">{it.description}</div>
                  </div>
                  <button
                    type="button"
                    onClick={() => connect(it.name)}
                    className="shrink-0 rounded-full bg-[linear-gradient(90deg,#4f75ff,#3b82f6)] px-4 py-1.5 text-[12px] font-semibold text-white"
                  >
                    Połącz
                  </button>
                </div>
              ))}
            </div>
          </div>
        ))}

        {hint ? (
          <div className={`mt-4 rounded-[14px] px-4 py-3 text-[13px] leading-5 ${hintClass}`}>
            {hint}
          </div>
        ) : null}

        <div className="mt-6 rounded-[18px] bg-white/60 p-4 text-center text-[12px] leading-5 text-slate-500">
          Brakuje Twojej integracji? Napisz do nas — rozważymy dodanie.
        </div>
      </div>
    </div>
  );
}

type PlanDef = {
  id: 'free' | 'pro' | 'business';
  name: string;
  price: string;
  period: string;
  highlight?: boolean;
  features: string[];
  cta: string;
};

function BillingScreen({ onBack }: { onBack: () => void }) {
  const [hint, setHint] = useState('');
  const [hintTone, setHintTone] = useState<'info' | 'success' | 'error'>('info');
  const [promo, setPromo] = useState('');

  function showHint(m: string, t: 'info' | 'success' | 'error' = 'info') {
    setHint(m);
    setHintTone(t);
  }

  const currentPlanId: PlanDef['id'] = 'free';

  const plans: PlanDef[] = [
    {
      id: 'free',
      name: 'Free',
      price: '0 zł',
      period: 'na zawsze',
      features: [
        'Podstawowe planowanie dnia',
        'Do 3 projektów',
        'Historia 30 dni',
        'Chat z lokalną Ollamą',
      ],
      cta: 'Obecny plan',
    },
    {
      id: 'pro',
      name: 'Pro',
      price: '29 zł',
      period: '/ mies',
      highlight: true,
      features: [
        'Wszystko z Free',
        'Nielimitowane projekty',
        'AI asystent (Claude)',
        'Integracje z kalendarzami',
        'Historia bez limitu',
        'Priorytetowe wsparcie',
      ],
      cta: 'Wybierz Pro',
    },
    {
      id: 'business',
      name: 'Business',
      price: '79 zł',
      period: '/ mies / użytkownik',
      features: [
        'Wszystko z Pro',
        'Zespoły i role',
        'Udostępnianie projektów',
        'Single Sign-On (SSO)',
        'Raporty i eksport PDF',
        'Dedykowany opiekun',
      ],
      cta: 'Wybierz Business',
    },
  ];

  function selectPlan(p: PlanDef) {
    if (p.id === currentPlanId) return;
    showHint(`Wkrótce — przejście na plan ${p.name} wymaga integracji ze Stripe.`, 'info');
  }

  function redeemPromo() {
    if (!promo.trim()) {
      showHint('Wpisz kod promocyjny.', 'error');
      return;
    }
    showHint('Wkrótce — realizacja kodów promocyjnych wymaga backendu.', 'info');
  }

  const hintClass =
    hintTone === 'success'
      ? 'bg-emerald-50 text-emerald-700'
      : hintTone === 'error'
      ? 'bg-rose-50 text-rose-600'
      : 'bg-white/70 text-slate-600';

  const currentPlan = plans.find((p) => p.id === currentPlanId)!;

  return (
    <div className="flex h-full flex-col">
      <SubHeader title="Plan i płatności" onBack={onBack} />

      <div className="min-h-0 flex-1 overflow-y-auto pr-1 pb-6">
        <div className="rounded-[22px] bg-[linear-gradient(180deg,#eef2ff_0%,#e0e7ff_100%)] p-5 shadow-sm">
          <div className="text-[11px] font-semibold uppercase tracking-wide text-indigo-600">
            Obecny plan
          </div>
          <div className="mt-1 flex items-baseline gap-2">
            <div className="text-[28px] font-bold text-slate-800">{currentPlan.name}</div>
            <div className="text-[13px] text-slate-500">
              {currentPlan.price} {currentPlan.period}
            </div>
          </div>
          {currentPlanId === 'free' ? (
            <div className="mt-2 text-[13px] leading-5 text-slate-600">
              Ulepsz do Pro, żeby odblokować nielimitowane projekty, integracje z kalendarzami i AI asystenta.
            </div>
          ) : null}
        </div>

        <h3 className="mt-6 mb-3 text-[15px] font-semibold text-slate-700">Plany</h3>
        <div className="space-y-3">
          {plans.map((p) => {
            const isCurrent = p.id === currentPlanId;
            const highlight = !!p.highlight && !isCurrent;
            return (
              <div
                key={p.id}
                className={`rounded-[22px] p-5 shadow-sm ${
                  isCurrent
                    ? 'border-2 border-indigo-300 bg-white/75'
                    : highlight
                    ? 'bg-[linear-gradient(180deg,#4f75ff_0%,#3b82f6_100%)] text-white'
                    : 'bg-white/75'
                }`}
              >
                <div className="flex items-baseline justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <div
                      className={`text-[20px] font-bold ${
                        highlight ? 'text-white' : 'text-slate-800'
                      }`}
                    >
                      {p.name}
                    </div>
                    {highlight ? (
                      <span className="rounded-full bg-white/20 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-white">
                        Polecany
                      </span>
                    ) : null}
                    {isCurrent ? (
                      <span className="rounded-full bg-indigo-100 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-indigo-600">
                        Aktywny
                      </span>
                    ) : null}
                  </div>
                  <div
                    className={`text-right text-[17px] font-bold ${
                      highlight ? 'text-white' : 'text-slate-800'
                    }`}
                  >
                    {p.price}
                    <span
                      className={`ml-1 text-[11px] font-normal ${
                        highlight ? 'text-white/80' : 'text-slate-500'
                      }`}
                    >
                      {p.period}
                    </span>
                  </div>
                </div>

                <ul className="mt-3 space-y-1.5">
                  {p.features.map((f, i) => (
                    <li
                      key={i}
                      className={`flex items-start gap-2 text-[13px] leading-5 ${
                        highlight ? 'text-white/90' : 'text-slate-600'
                      }`}
                    >
                      <Check
                        className={`mt-0.5 h-4 w-4 shrink-0 ${
                          highlight ? 'text-white' : 'text-emerald-500'
                        }`}
                      />
                      <span>{f}</span>
                    </li>
                  ))}
                </ul>

                <button
                  type="button"
                  onClick={() => selectPlan(p)}
                  disabled={isCurrent}
                  className={`mt-4 w-full rounded-full px-4 py-3 text-[14px] font-semibold ${
                    isCurrent
                      ? 'cursor-default bg-slate-100 text-slate-500'
                      : highlight
                      ? 'bg-white text-indigo-600'
                      : 'bg-[linear-gradient(90deg,#4f75ff,#3b82f6)] text-white'
                  }`}
                >
                  {p.cta}
                </button>
              </div>
            );
          })}
        </div>

        <div className="mt-6 rounded-[22px] bg-white/60 p-5 text-center">
          <CreditCard className="mx-auto h-8 w-8 text-slate-400" />
          <div className="mt-2 text-[14px] font-semibold text-slate-700">Rozliczenia</div>
          <div className="mt-1 text-[12px] leading-5 text-slate-500">
            Po aktywacji Pro lub Business pojawią się tu metoda płatności, następna płatność i historia faktur.
          </div>
        </div>

        <div className="mt-4 rounded-[18px] bg-white/60 p-4">
          <div className="mb-2 text-[13px] font-semibold text-slate-600">Kod promocyjny</div>
          <div className="flex gap-2">
            <input
              value={promo}
              onChange={(e) => setPromo(e.target.value)}
              placeholder="np. STUDENT2026"
              autoCapitalize="characters"
              autoCorrect="off"
              spellCheck={false}
              className="flex-1 rounded-[12px] border border-slate-200 bg-white px-3 py-2 text-[14px] text-slate-700 outline-none focus:border-indigo-300"
            />
            <button
              type="button"
              onClick={redeemPromo}
              className="rounded-[12px] bg-slate-100 px-4 py-2 text-[13px] font-semibold text-slate-700"
            >
              Zrealizuj
            </button>
          </div>
        </div>

        {hint ? (
          <div className={`mt-3 rounded-[14px] px-4 py-3 text-[13px] leading-5 ${hintClass}`}>
            {hint}
          </div>
        ) : null}
      </div>
    </div>
  );
}

type Session = {
  id: string;
  device: string;
  location: string;
  lastActive: string;
  current: boolean;
};

function SecurityScreen({ onBack }: { onBack: () => void }) {
  const [currentPw, setCurrentPw] = useState('');
  const [newPw, setNewPw] = useState('');
  const [confirmPw, setConfirmPw] = useState('');
  const [hint, setHint] = useState('');
  const [hintTone, setHintTone] = useState<'info' | 'success' | 'error'>('info');

  function showHint(msg: string, tone: 'info' | 'success' | 'error' = 'info') {
    setHint(msg);
    setHintTone(tone);
  }

  function changePassword() {
    if (!currentPw || !newPw || !confirmPw) {
      showHint('Uzupełnij wszystkie pola.', 'error');
      return;
    }
    if (newPw !== confirmPw) {
      showHint('Nowe hasła nie są zgodne.', 'error');
      return;
    }
    if (newPw.length < 8) {
      showHint('Nowe hasło musi mieć co najmniej 8 znaków.', 'error');
      return;
    }
    if (newPw === currentPw) {
      showHint('Nowe hasło musi być inne niż obecne.', 'error');
      return;
    }
    showHint('Wkrótce — zmiana hasła wymaga backendu.', 'info');
  }

  const sessions: Session[] = [
    { id: '1', device: 'Chrome • Windows', location: 'Warszawa, PL', lastActive: 'Teraz', current: true },
    { id: '2', device: 'Safari • iPhone', location: 'Warszawa, PL', lastActive: '2 godziny temu', current: false },
    { id: '3', device: 'Firefox • Windows', location: 'Kraków, PL', lastActive: '3 dni temu', current: false },
  ];

  const hintClass =
    hintTone === 'success'
      ? 'bg-emerald-50 text-emerald-700'
      : hintTone === 'error'
      ? 'bg-rose-50 text-rose-600'
      : 'bg-white/70 text-slate-600';

  return (
    <div className="flex h-full flex-col">
      <SubHeader title="Bezpieczeństwo" onBack={onBack} />

      <div className="min-h-0 flex-1 overflow-y-auto pr-1 pb-6">
        <h3 className="mb-2 flex items-center gap-2 text-[15px] font-semibold text-slate-700">
          <Lock className="h-4 w-4 text-slate-500" />
          Hasło
        </h3>
        <div className="space-y-3 rounded-[22px] bg-white/75 p-4 shadow-sm">
          <FormField
            label="Obecne hasło"
            type="password"
            value={currentPw}
            onChange={setCurrentPw}
            placeholder="••••••••"
            autoComplete="current-password"
          />
          <FormField
            label="Nowe hasło"
            type="password"
            value={newPw}
            onChange={setNewPw}
            placeholder="minimum 8 znaków"
            autoComplete="new-password"
          />
          <FormField
            label="Potwierdź nowe hasło"
            type="password"
            value={confirmPw}
            onChange={setConfirmPw}
            placeholder="powtórz nowe hasło"
            autoComplete="new-password"
          />
          <button
            type="button"
            onClick={changePassword}
            className="w-full rounded-full bg-[linear-gradient(90deg,#4f75ff,#3b82f6)] px-4 py-3 text-[14px] font-semibold text-white"
          >
            Zmień hasło
          </button>
        </div>

        <h3 className="mt-6 mb-2 flex items-center gap-2 text-[15px] font-semibold text-slate-700">
          <KeyRound className="h-4 w-4 text-slate-500" />
          Weryfikacja dwuetapowa
        </h3>
        <div className="rounded-[22px] bg-white/75 p-4 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-amber-100">
              <KeyRound className="h-5 w-5 text-amber-600" />
            </div>
            <div className="min-w-0 flex-1">
              <div className="text-[15px] font-semibold text-slate-800">2FA — Wyłączone</div>
              <div className="text-[13px] leading-5 text-slate-500">
                Kod z aplikacji Authenticator przy logowaniu
              </div>
            </div>
          </div>
          <button
            type="button"
            onClick={() =>
              showHint('Wkrótce — konfiguracja 2FA (TOTP + kody zapasowe) wymaga backendu.', 'info')
            }
            className="mt-3 w-full rounded-full bg-slate-100 px-4 py-3 text-[14px] font-semibold text-slate-700"
          >
            Skonfiguruj 2FA
          </button>
        </div>

        <h3 className="mt-6 mb-2 flex items-center gap-2 text-[15px] font-semibold text-slate-700">
          <Smartphone className="h-4 w-4 text-slate-500" />
          Aktywne sesje
        </h3>
        <div className="rounded-[22px] bg-white/75 p-3 shadow-sm">
          {sessions.map((s, i) => (
            <div
              key={s.id}
              className={`flex items-center gap-3 px-2 py-3 ${
                i < sessions.length - 1 ? 'border-b border-slate-200' : ''
              }`}
            >
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-indigo-100">
                <Smartphone className="h-5 w-5 text-indigo-500" />
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <div className="truncate text-[14px] font-semibold text-slate-800">{s.device}</div>
                  {s.current ? (
                    <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-[11px] font-semibold text-emerald-700">
                      to urządzenie
                    </span>
                  ) : null}
                </div>
                <div className="truncate text-[12px] text-slate-500">
                  {s.location} • {s.lastActive}
                </div>
              </div>
              {!s.current ? (
                <button
                  type="button"
                  onClick={() =>
                    showHint('Wkrótce — wylogowanie pojedynczej sesji wymaga backendu.', 'info')
                  }
                  className="rounded-full px-3 py-1.5 text-[12px] font-semibold text-rose-600"
                >
                  Wyloguj
                </button>
              ) : null}
            </div>
          ))}
        </div>

        <button
          type="button"
          onClick={() =>
            showHint('Wkrótce — wylogowanie ze wszystkich urządzeń wymaga backendu z sesjami.', 'info')
          }
          className="mt-4 flex w-full items-center justify-center gap-2 rounded-[18px] bg-rose-50 px-4 py-3 text-[14px] font-semibold text-rose-600"
        >
          <LogOut className="h-4 w-4" />
          Wyloguj ze wszystkich urządzeń
        </button>

        {hint ? (
          <div className={`mt-3 rounded-[14px] px-4 py-3 text-[13px] leading-5 ${hintClass}`}>
            {hint}
          </div>
        ) : null}
      </div>
    </div>
  );
}

function collectJarvisData(): Record<string, string> {
  const out: Record<string, string> = {};
  try {
    for (let i = 0; i < localStorage.length; i += 1) {
      const k = localStorage.key(i);
      if (k && k.startsWith('jarvis_')) {
        const v = localStorage.getItem(k);
        if (v !== null) out[k] = v;
      }
    }
  } catch {}
  return out;
}

function getLocalStorageStats(): { count: number; size: number } {
  let count = 0;
  let size = 0;
  try {
    for (let i = 0; i < localStorage.length; i += 1) {
      const k = localStorage.key(i);
      if (k && k.startsWith('jarvis_')) {
        count += 1;
        const v = localStorage.getItem(k) || '';
        size += k.length + v.length;
      }
    }
  } catch {}
  return { count, size };
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function DataScreen({ onBack }: { onBack: () => void }) {
  const importInputRef = useRef<HTMLInputElement>(null);
  const [hint, setHint] = useState('');
  const [hintTone, setHintTone] = useState<'info' | 'success' | 'error'>('info');
  const [stats, setStats] = useState(() => getLocalStorageStats());
  const [confirmClear, setConfirmClear] = useState(false);
  const [consents, setConsents] = useState<Consents>(() => readConsents());
  const [advancedOpen, setAdvancedOpen] = useState(false);

  function refreshStats() {
    setStats(getLocalStorageStats());
  }

  function showHint(message: string, tone: 'info' | 'success' | 'error' = 'info') {
    setHint(message);
    setHintTone(tone);
  }

  function updateConsent<K extends keyof Consents>(key: K, value: Consents[K]) {
    const next = { ...consents, [key]: value };
    setConsents(next);
    writeConsents(next);
  }

  function requestDataExport() {
    showHint(
      'Wkrótce — po dodaniu backendu wyślemy link do pobrania Twoich danych na adres email z profilu.',
      'info'
    );
  }

  function deleteAccount() {
    showHint('Wkrótce — trwałe usunięcie konta wymaga backendu z logowaniem.', 'info');
  }

  function exportAll() {
    const data = collectJarvisData();
    const count = Object.keys(data).length;
    if (count === 0) {
      showHint('Brak danych do eksportu.', 'info');
      return;
    }
    const payload = {
      version: 1,
      exported_at: new Date().toISOString(),
      items: data,
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    const today = new Date().toISOString().slice(0, 10);
    a.href = url;
    a.download = `jarvis-backup-${today}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    showHint(`Eksport gotowy: ${count} pozycji.`, 'success');
  }

  function onImportFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const parsed = JSON.parse(String(reader.result));
        const items =
          parsed && typeof parsed === 'object' && parsed.items && typeof parsed.items === 'object'
            ? parsed.items
            : parsed;
        if (!items || typeof items !== 'object') throw new Error('Nieprawidłowy plik kopii zapasowej');
        const keys = Object.keys(items).filter((k) => k.startsWith('jarvis_'));
        if (keys.length === 0) throw new Error('Plik nie zawiera żadnych danych Jarvisa');
        keys.forEach((k) => {
          const v = items[k];
          localStorage.setItem(k, typeof v === 'string' ? v : JSON.stringify(v));
        });
        refreshStats();
        showHint(`Zaimportowano ${keys.length} pozycji. Odśwież aplikację, żeby zobaczyć zmiany.`, 'success');
      } catch (err) {
        const msg = err instanceof Error ? err.message : 'nieznany błąd';
        showHint(`Błąd importu: ${msg}`, 'error');
      }
    };
    reader.onerror = () => showHint('Nie udało się odczytać pliku.', 'error');
    reader.readAsText(file);
    if (importInputRef.current) importInputRef.current.value = '';
  }

  function clearLocal() {
    if (!confirmClear) {
      setConfirmClear(true);
      showHint('Kliknij jeszcze raz, żeby potwierdzić usunięcie lokalnych danych.', 'info');
      window.setTimeout(() => setConfirmClear(false), 4000);
      return;
    }
    const keys: string[] = [];
    try {
      for (let i = 0; i < localStorage.length; i += 1) {
        const k = localStorage.key(i);
        if (k && k.startsWith('jarvis_')) keys.push(k);
      }
      keys.forEach((k) => localStorage.removeItem(k));
    } catch {}
    setConfirmClear(false);
    refreshStats();
    showHint(`Usunięto ${keys.length} pozycji. Odśwież aplikację.`, 'success');
  }

  const hintClass =
    hintTone === 'success'
      ? 'bg-emerald-50 text-emerald-700'
      : hintTone === 'error'
      ? 'bg-rose-50 text-rose-600'
      : 'bg-white/70 text-slate-600';

  return (
    <div className="flex h-full flex-col">
      <SubHeader title="Dane i prywatność" onBack={onBack} />

      <div className="min-h-0 flex-1 overflow-y-auto pr-1 pb-6">
        <h3 className="mb-2 text-[15px] font-semibold text-slate-700">Zgody</h3>
        <div className="rounded-[22px] bg-white/75 p-3 shadow-sm">
          <ToggleRow
            icon={<Mail className="h-7 w-7 text-indigo-300" />}
            title="Newsletter i marketing"
            checked={consents.marketing}
            onChange={(v) => updateConsent('marketing', v)}
          />
          <div className="border-b border-slate-200" />
          <ToggleRow
            icon={<BarChart3 className="h-7 w-7 text-indigo-300" />}
            title="Analityka użycia"
            checked={consents.analytics}
            onChange={(v) => updateConsent('analytics', v)}
          />
          <div className="border-b border-slate-200" />
          <ToggleRow
            icon={<Lightbulb className="h-7 w-7 text-indigo-300" />}
            title="Personalizacja treści"
            checked={consents.personalization}
            onChange={(v) => updateConsent('personalization', v)}
          />
        </div>
        <div className="mt-2 px-2 text-[12px] leading-5 text-slate-500">
          Zgody możesz wycofać w każdej chwili. Szczegóły w Polityce prywatności.
        </div>

        <h3 className="mt-6 mb-2 text-[15px] font-semibold text-slate-700">Twoje dane</h3>
        <div className="space-y-2">
          <button
            type="button"
            onClick={requestDataExport}
            className="flex w-full items-center gap-3 rounded-[18px] bg-white/75 px-4 py-4 text-left shadow-sm"
          >
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-indigo-100">
              <Download className="h-5 w-5 text-indigo-500" />
            </div>
            <div className="min-w-0 flex-1">
              <div className="text-[16px] font-semibold text-slate-800">Pobierz moje dane</div>
              <div className="text-[13px] leading-5 text-slate-500">
                Wyślemy link z archiwum na email z profilu (RODO)
              </div>
            </div>
            <ChevronRight className="h-5 w-5 shrink-0 text-slate-400" />
          </button>

          <button
            type="button"
            onClick={deleteAccount}
            className="flex w-full items-center gap-3 rounded-[18px] bg-white/75 px-4 py-4 text-left shadow-sm"
          >
            <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-rose-100">
              <Trash2 className="h-5 w-5 text-rose-500" />
            </div>
            <div className="min-w-0 flex-1">
              <div className="text-[16px] font-semibold text-rose-600">Usuń konto</div>
              <div className="text-[13px] leading-5 text-slate-500">
                Trwale usuwa Twoje konto i wszystkie dane z serwera
              </div>
            </div>
            <ChevronRight className="h-5 w-5 shrink-0 text-slate-400" />
          </button>
        </div>

        {hint ? (
          <div className={`mt-3 rounded-[14px] px-4 py-3 text-[13px] leading-5 ${hintClass}`}>
            {hint}
          </div>
        ) : null}

        <div className="mt-8">
          <button
            type="button"
            onClick={() => setAdvancedOpen((v) => !v)}
            className="flex w-full items-center justify-between gap-3 rounded-[18px] bg-white/60 px-4 py-3 text-left"
          >
            <span className="text-[14px] font-semibold text-slate-600">Zaawansowane</span>
            {advancedOpen ? (
              <ChevronUp className="h-5 w-5 text-slate-500" />
            ) : (
              <ChevronDown className="h-5 w-5 text-slate-500" />
            )}
          </button>

          {advancedOpen ? (
            <div className="mt-3 space-y-3">
              <div className="rounded-[18px] bg-white/60 p-4">
                <div className="text-[12px] font-medium text-slate-500">Lokalne dane w przeglądarce</div>
                <div className="mt-1 text-[18px] font-semibold text-slate-800">
                  {stats.count} {stats.count === 1 ? 'pozycja' : 'pozycji'} • {formatBytes(stats.size)}
                </div>
                <div className="mt-1 text-[12px] leading-5 text-slate-500">
                  Narzędzia deweloperskie — kopie zapasowe `localStorage`. W docelowej wersji cloud użytkownik korzysta z „Pobierz moje dane" powyżej.
                </div>
              </div>

              <button
                type="button"
                onClick={exportAll}
                className="flex w-full items-center gap-3 rounded-[14px] bg-white/60 px-4 py-3 text-left"
              >
                <Download className="h-4 w-4 text-slate-500" />
                <span className="text-[14px] text-slate-700">Eksportuj lokalne dane do pliku JSON</span>
              </button>

              <button
                type="button"
                onClick={() => importInputRef.current?.click()}
                className="flex w-full items-center gap-3 rounded-[14px] bg-white/60 px-4 py-3 text-left"
              >
                <Upload className="h-4 w-4 text-slate-500" />
                <span className="text-[14px] text-slate-700">Importuj lokalne dane z pliku JSON</span>
              </button>

              <input
                ref={importInputRef}
                type="file"
                accept="application/json,.json"
                onChange={onImportFile}
                className="hidden"
              />

              <div className="rounded-[14px] bg-rose-50/60 p-3">
                <div className="mb-2 flex items-center gap-2 text-[12px] font-semibold text-rose-700">
                  <AlertTriangle className="h-4 w-4" />
                  Strefa destrukcyjna
                </div>
                <button
                  type="button"
                  onClick={clearLocal}
                  className={`flex w-full items-center justify-center gap-2 rounded-[12px] px-3 py-2 text-[13px] font-semibold transition-colors ${
                    confirmClear
                      ? 'bg-rose-600 text-white'
                      : 'border border-rose-200 bg-white text-rose-600'
                  }`}
                >
                  <Trash2 className="h-4 w-4" />
                  {confirmClear ? 'Kliknij ponownie, żeby potwierdzić' : 'Wyczyść lokalne dane'}
                </button>
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}

function DatePickerPopup({
  value,
  valueTime = null,
  onChange,
  onClose,
}: {
  value: string | null;
  valueTime?: string | null;
  onChange: (date: string | null, time: string | null) => void;
  onClose: () => void;
}) {
  const initial = value ? new Date(value) : new Date();
  const [viewYear, setViewYear] = useState(initial.getFullYear());
  const [viewMonth, setViewMonth] = useState(initial.getMonth());
  const [time, setTime] = useState<string>(valueTime ?? '');

  const firstDay = new Date(viewYear, viewMonth, 1);
  const jsWeekday = firstDay.getDay();
  const mondayOffset = jsWeekday === 0 ? 6 : jsWeekday - 1;
  const daysInMonth = new Date(viewYear, viewMonth + 1, 0).getDate();

  const cells: Array<{ day: number | null; key: string }> = [];
  for (let i = 0; i < mondayOffset; i += 1) cells.push({ day: null, key: `empty-${i}` });
  for (let d = 1; d <= daysInMonth; d += 1) cells.push({ day: d, key: `d-${d}` });
  while (cells.length % 7 !== 0) cells.push({ day: null, key: `empty-end-${cells.length}` });

  function goMonth(delta: number) {
    const d = new Date(viewYear, viewMonth + delta, 1);
    setViewYear(d.getFullYear());
    setViewMonth(d.getMonth());
  }

  function commit(date: string | null) {
    const t = time.trim() || null;
    onChange(date, date ? t : null);
    onClose();
  }

  function pickDay(day: number) {
    const key = `${viewYear}-${pad2(viewMonth + 1)}-${pad2(day)}`;
    commit(key);
  }

  function pickQuick(v: string | null) {
    commit(v);
  }

  const today = todayKey();
  const tomorrow = tomorrowKey();
  const endWeek = endOfWeekKey();

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <button
        type="button"
        onClick={onClose}
        className="absolute inset-0 bg-slate-900/40 backdrop-blur-sm"
        aria-label="Zamknij"
      />
      <div className="relative z-10 w-full max-w-[360px] rounded-[24px] bg-white p-4 shadow-[0_20px_60px_rgba(15,23,42,0.25)]">
        <div className="mb-3 flex items-center justify-between">
          <div className="text-[16px] font-semibold text-slate-800">Data i godzina</div>
          <button
            type="button"
            onClick={onClose}
            className="flex h-8 w-8 items-center justify-center rounded-full text-slate-400 hover:bg-slate-100"
            aria-label="Zamknij"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="mb-3 grid grid-cols-2 gap-2">
          <button
            type="button"
            onClick={() => pickQuick(today)}
            className="rounded-[12px] bg-indigo-50 px-3 py-2 text-[13px] font-semibold text-indigo-600"
          >
            Dziś
          </button>
          <button
            type="button"
            onClick={() => pickQuick(tomorrow)}
            className="rounded-[12px] bg-indigo-50 px-3 py-2 text-[13px] font-semibold text-indigo-600"
          >
            Jutro
          </button>
          <button
            type="button"
            onClick={() => pickQuick(endWeek)}
            className="rounded-[12px] bg-indigo-50 px-3 py-2 text-[13px] font-semibold text-indigo-600"
          >
            Koniec tygodnia
          </button>
          <button
            type="button"
            onClick={() => pickQuick(null)}
            className="rounded-[12px] bg-slate-100 px-3 py-2 text-[13px] font-semibold text-slate-600"
          >
            Bez daty
          </button>
        </div>

        <div className="mb-3 flex items-center gap-2">
          <label className="shrink-0 text-[13px] font-semibold text-slate-600">Godzina</label>
          <input
            type="time"
            value={time}
            onChange={(e) => setTime(e.target.value)}
            className="flex-1 rounded-[12px] border border-slate-200 px-3 py-2 text-[14px] outline-none"
          />
          {time ? (
            <button
              type="button"
              onClick={() => setTime('')}
              className="rounded-[12px] bg-slate-100 px-3 py-2 text-[12px] font-semibold text-slate-500"
              title="Wyczyść godzinę"
            >
              Wyczyść
            </button>
          ) : null}
        </div>

        <div className="mb-2 flex items-center justify-between">
          <button
            type="button"
            onClick={() => goMonth(-1)}
            className="flex h-8 w-8 items-center justify-center rounded-full hover:bg-slate-100"
            aria-label="Poprzedni miesiąc"
          >
            <ChevronLeft className="h-4 w-4 text-slate-600" />
          </button>
          <div className="text-[14px] font-semibold text-slate-700">
            {MONTHS_PL[viewMonth]} {viewYear}
          </div>
          <button
            type="button"
            onClick={() => goMonth(1)}
            className="flex h-8 w-8 items-center justify-center rounded-full hover:bg-slate-100"
            aria-label="Następny miesiąc"
          >
            <ChevronRight className="h-4 w-4 text-slate-600" />
          </button>
        </div>

        <div className="mb-1 grid grid-cols-7 gap-1">
          {WEEKDAYS_SHORT.map((label) => (
            <div key={label} className="text-center text-[11px] font-semibold text-slate-400">
              {label}
            </div>
          ))}
        </div>

        <div className="grid grid-cols-7 gap-1">
          {cells.map((cell) => {
            if (!cell.day) return <div key={cell.key} className="h-9" />;
            const cellKey = `${viewYear}-${pad2(viewMonth + 1)}-${pad2(cell.day)}`;
            const isSelected = cellKey === value;
            const isToday = cellKey === today;
            return (
              <button
                key={cell.key}
                type="button"
                onClick={() => pickDay(cell.day!)}
                className={`flex h-9 items-center justify-center rounded-full text-[13px] font-semibold ${
                  isSelected
                    ? 'bg-indigo-500 text-white'
                    : isToday
                    ? 'bg-indigo-100 text-indigo-600'
                    : 'text-slate-700 hover:bg-slate-100'
                }`}
              >
                {cell.day}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function TaskRow({
  item,
  onToggle,
  onPickDate,
  onDelete,
  showCategory = false,
  expanded = false,
  onToggleExpand,
  shoppingPool,
  onShoppingToggle,
  onChecklistAdd,
  onChecklistToggle,
  onChecklistRemove,
}: {
  item: ProjectItem;
  onToggle: () => void;
  onPickDate: () => void;
  onDelete: () => void;
  showCategory?: boolean;
  expanded?: boolean;
  onToggleExpand?: () => void;
  shoppingPool?: ShoppingPoolItem[];
  onShoppingToggle?: (poolId: string) => void;
  onChecklistAdd?: (label: string) => void;
  onChecklistToggle?: (checklistId: string) => void;
  onChecklistRemove?: (checklistId: string) => void;
}) {
  const categoryMeta: Record<ProjectCategory, { label: string; color: string }> = {
    shopping: { label: 'Zakupy', color: '#F59E0B' },
    reading: { label: 'Przeczytać', color: '#8B5CF6' },
    ideas: { label: 'Pomysły', color: '#10B981' },
    to_check: { label: 'Do sprawdzenia', color: '#3B82F6' },
    general: { label: 'Ogólne', color: '#6B7280' },
  };
  const meta = categoryMeta[item.category];
  const dueLabel = formatDueWithTime(item.dueAt, item.time);
  const showMeta = showCategory || !!dueLabel;
  const isShopping = item.category === 'shopping';
  const expandable = !!onToggleExpand;
  const [draftCheck, setDraftCheck] = useState('');

  function commitDraft() {
    const trimmed = draftCheck.trim();
    if (!trimmed || !onChecklistAdd) return;
    onChecklistAdd(trimmed);
    setDraftCheck('');
  }

  return (
    <div className="rounded-[14px] bg-white/75 shadow-sm">
      <div className="flex items-center gap-2 px-3 py-2.5">
        <button
          type="button"
          onClick={onToggleExpand}
          disabled={!expandable}
          className="flex min-w-0 flex-1 items-center gap-2 text-left"
        >
          <div className="min-w-0 flex-1">
            <div
              className={`truncate text-[14px] ${
                item.done ? 'text-slate-400 line-through' : 'text-slate-800'
              }`}
            >
              {item.label}
            </div>
            {showMeta ? (
              <div className="mt-0.5 flex items-center gap-1.5">
                {showCategory ? (
                  <>
                    <div className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: meta.color }} />
                    <span className="text-[11px] text-slate-500">
                      {meta.label}
                      {dueLabel ? ` · ${dueLabel}` : ''}
                    </span>
                  </>
                ) : (
                  <span className="text-[11px] text-slate-500">{dueLabel}</span>
                )}
              </div>
            ) : null}
          </div>
          {expandable ? (
            expanded ? (
              <ChevronUp className="h-4 w-4 shrink-0 text-slate-400" />
            ) : (
              <ChevronDown className="h-4 w-4 shrink-0 text-slate-400" />
            )
          ) : null}
        </button>

        <button
          type="button"
          onClick={onToggle}
          className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full transition-colors ${
            item.done
              ? 'bg-emerald-500 text-white'
              : 'bg-emerald-50 text-emerald-500 hover:bg-emerald-100'
          }`}
          aria-label={item.done ? 'Oznacz jako niezrobione' : 'Oznacz jako zrobione'}
          title={item.done ? 'Cofnij zrobione' : 'Zrobione'}
        >
          <Check className="h-4 w-4" />
        </button>

        <button
          type="button"
          onClick={onPickDate}
          className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-indigo-50 text-indigo-500 hover:bg-indigo-100"
          aria-label="Przenieś na inny dzień"
          title="Przenieś na inny dzień"
        >
          <ChevronRight className="h-4 w-4" />
        </button>

        <button
          type="button"
          onClick={onDelete}
          className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-rose-50 text-rose-500 hover:bg-rose-100"
          aria-label="Usuń"
          title="Usuń"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      {expanded ? (
        <div className="border-t border-slate-100 px-3 py-3">
          {isShopping ? (() => {
            const pool = (shoppingPool ?? []).filter((p) => !p.done);
            if (pool.length === 0) {
              return (
                <div className="text-[12px] text-slate-400">Lista zakupów jest pusta.</div>
              );
            }
            return (
              <ul className="space-y-1.5">
                {pool.map((p) => (
                  <li key={p.id} className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => onShoppingToggle?.(p.id)}
                      className="flex h-5 w-5 shrink-0 items-center justify-center rounded-md border-2 border-emerald-300 bg-white hover:bg-emerald-50"
                      aria-label="Kupione"
                      title="Kupione (usuwa z listy)"
                    />
                    <span className="text-[13px] text-slate-700">{p.label}</span>
                  </li>
                ))}
              </ul>
            );
          })() : (
            <div className="space-y-2">
              {item.checklist.length > 0 ? (
                <ul className="space-y-1.5">
                  {item.checklist.map((c) => (
                    <li key={c.id} className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() => onChecklistToggle?.(c.id)}
                        className={`flex h-5 w-5 shrink-0 items-center justify-center rounded-md border-2 ${
                          c.done
                            ? 'border-emerald-500 bg-emerald-500 text-white'
                            : 'border-slate-300 bg-white text-emerald-500'
                        }`}
                        aria-label={c.done ? 'Cofnij zrobione' : 'Zrobione'}
                      >
                        {c.done ? <Check className="h-3 w-3" /> : null}
                      </button>
                      <span
                        className={`flex-1 text-[13px] ${
                          c.done ? 'text-slate-400 line-through' : 'text-slate-700'
                        }`}
                      >
                        {c.label}
                      </span>
                      <button
                        type="button"
                        onClick={() => onChecklistRemove?.(c.id)}
                        className="text-slate-300 hover:text-rose-400"
                        aria-label="Usuń pozycję"
                        title="Usuń pozycję"
                      >
                        <X className="h-3.5 w-3.5" />
                      </button>
                    </li>
                  ))}
                </ul>
              ) : (
                <div className="text-[12px] text-slate-400">Brak pozycji w checkliście.</div>
              )}

              {onChecklistAdd ? (
                <div className="flex items-center gap-2 pt-1">
                  <input
                    value={draftCheck}
                    onChange={(e) => setDraftCheck(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        e.preventDefault();
                        commitDraft();
                      }
                    }}
                    className="flex-1 rounded-2xl border border-slate-200 px-3 py-1.5 text-[13px] outline-none"
                    placeholder="Dodaj pozycję..."
                  />
                  <button
                    type="button"
                    onClick={commitDraft}
                    className="rounded-full bg-indigo-50 px-3 py-1.5 text-[12px] font-semibold text-indigo-600"
                  >
                    +
                  </button>
                </div>
              ) : null}
            </div>
          )}
        </div>
      ) : null}
    </div>
  );
}

function InboxTasksScreen({
  projectItems,
  setProjectItems,
  shoppingPool,
  setShoppingPool,
  onBack,
}: {
  projectItems: ProjectItem[];
  setProjectItems: React.Dispatch<React.SetStateAction<ProjectItem[]>>;
  shoppingPool: ShoppingPoolItem[];
  setShoppingPool: React.Dispatch<React.SetStateAction<ShoppingPoolItem[]>>;
  onBack: () => void;
}) {
  const [pickingId, setPickingId] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [newItem, setNewItem] = useState('');

  const today = todayKey();
  const inbox = projectItems.filter((i) => !i.dueAt || i.dueAt === today);

  function toggleDone(id: string) {
    setProjectItems((prev) =>
      prev.map((i) => (i.id === id ? { ...i, done: !i.done } : i))
    );
  }

  function setDueAt(id: string, nextDate: string | null, nextTime: string | null) {
    setProjectItems((prev) =>
      prev.map((i) =>
        i.id === id ? { ...i, dueAt: nextDate, time: nextTime } : i
      )
    );
  }

  function removeItem(id: string) {
    setProjectItems((prev) => prev.filter((i) => i.id !== id));
  }

  function addChecklist(taskId: string, label: string) {
    setProjectItems((prev) =>
      prev.map((i) =>
        i.id === taskId
          ? {
              ...i,
              checklist: [
                ...i.checklist,
                { id: `chk-${Date.now()}`, label, done: false },
              ],
            }
          : i
      )
    );
  }

  function toggleChecklist(taskId: string, chkId: string) {
    setProjectItems((prev) =>
      prev.map((i) =>
        i.id === taskId
          ? {
              ...i,
              checklist: i.checklist.map((c) =>
                c.id === chkId ? { ...c, done: !c.done } : c
              ),
            }
          : i
      )
    );
  }

  function removeChecklist(taskId: string, chkId: string) {
    setProjectItems((prev) =>
      prev.map((i) =>
        i.id === taskId
          ? { ...i, checklist: i.checklist.filter((c) => c.id !== chkId) }
          : i
      )
    );
  }

  function toggleShopping(poolId: string) {
    setShoppingPool((prev) => prev.filter((p) => p.id !== poolId));
  }

  function addItem() {
    const trimmed = newItem.trim();
    if (!trimmed) return;
    setProjectItems((prev) => [
      ...prev,
      {
        id: `project-${Date.now()}`,
        label: trimmed,
        category: extractProjectCategoryFromChat(trimmed),
        done: false,
        source: 'manual',
        dueAt: null,
        time: null,
        checklist: [],
      },
    ]);
    setNewItem('');
  }

  const picking = inbox.find((i) => i.id === pickingId) || null;

  return (
    <div className="flex h-full flex-col">
      <SubHeader title="Do zrobienia" onBack={onBack} />

      <div className="mb-3 rounded-[18px] bg-white/75 p-3 shadow-sm">
        <div className="flex items-center gap-2">
          <input
            value={newItem}
            onChange={(e) => setNewItem(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                e.preventDefault();
                addItem();
              }
            }}
            className="flex-1 rounded-2xl border border-slate-200 px-4 py-2.5 text-[14px] outline-none"
            placeholder="Nowe zadanie..."
          />
          <button
            type="button"
            onClick={addItem}
            className="rounded-full bg-[linear-gradient(90deg,#4f75ff,#3b82f6)] px-4 py-2.5 text-[13px] font-semibold text-white"
          >
            Dodaj
          </button>
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto pr-1 pb-6">
        <div className="mb-3 text-[13px] leading-5 text-slate-500">
          Zadania na dziś i bez daty. Strzałka — przenieś na inny dzień. Ptaszek — zrobione. Krzyżyk — usuń.
        </div>

        {inbox.length === 0 ? (
          <div className="rounded-[22px] bg-white/60 p-6 text-center">
            <ListTodo className="mx-auto h-8 w-8 text-slate-400" />
            <div className="mt-2 text-[14px] font-semibold text-slate-700">Skrzynka pusta</div>
            <div className="mt-1 text-[12px] leading-5 text-slate-500">
              Wszystko jest zaplanowane. Nowe zadania bez daty pojawią się tutaj.
            </div>
          </div>
        ) : (
          <div className="space-y-2">
            {inbox.map((item) => (
              <TaskRow
                key={item.id}
                item={item}
                onToggle={() => toggleDone(item.id)}
                onPickDate={() => setPickingId(item.id)}
                onDelete={() => removeItem(item.id)}
                showCategory
                expanded={expandedId === item.id}
                onToggleExpand={() =>
                  setExpandedId((cur) => (cur === item.id ? null : item.id))
                }
                shoppingPool={shoppingPool}
                onShoppingToggle={toggleShopping}
                onChecklistAdd={(label) => addChecklist(item.id, label)}
                onChecklistToggle={(chkId) => toggleChecklist(item.id, chkId)}
                onChecklistRemove={(chkId) => removeChecklist(item.id, chkId)}
              />
            ))}
          </div>
        )}
      </div>

      {picking ? (
        <DatePickerPopup
          value={picking.dueAt}
          valueTime={picking.time}
          onChange={(d, t) => setDueAt(picking.id, d, t)}
          onClose={() => setPickingId(null)}
        />
      ) : null}
    </div>
  );
}

function SevenDaysScreen({
  events,
  projectItems,
  setProjectItems,
  shoppingPool,
  setShoppingPool,
  onBack,
}: {
  events: CalendarEvent[];
  projectItems: ProjectItem[];
  setProjectItems: React.Dispatch<React.SetStateAction<ProjectItem[]>>;
  shoppingPool: ShoppingPoolItem[];
  setShoppingPool: React.Dispatch<React.SetStateAction<ShoppingPoolItem[]>>;
  onBack: () => void;
}) {
  const [pickingId, setPickingId] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const days: { key: string; date: Date; label: string }[] = [];
  for (let i = 0; i < 7; i += 1) {
    const d = new Date(today);
    d.setDate(today.getDate() + i);
    const key = toDateKey(d);
    let label: string;
    if (i === 0) label = 'Dziś';
    else if (i === 1) label = 'Jutro';
    else label = `${WEEKDAYS_SHORT[(d.getDay() + 6) % 7]}, ${d.getDate()} ${MONTHS_PL[d.getMonth()].toLowerCase()}`;
    days.push({ key, date: d, label });
  }

  function toggleDone(id: string) {
    setProjectItems((prev) =>
      prev.map((i) => (i.id === id ? { ...i, done: !i.done } : i))
    );
  }

  function setDueAt(id: string, nextDate: string | null, nextTime: string | null) {
    setProjectItems((prev) =>
      prev.map((i) =>
        i.id === id ? { ...i, dueAt: nextDate, time: nextTime } : i
      )
    );
  }

  function removeItem(id: string) {
    setProjectItems((prev) => prev.filter((i) => i.id !== id));
  }

  function addChecklist(taskId: string, label: string) {
    setProjectItems((prev) =>
      prev.map((i) =>
        i.id === taskId
          ? {
              ...i,
              checklist: [
                ...i.checklist,
                { id: `chk-${Date.now()}`, label, done: false },
              ],
            }
          : i
      )
    );
  }

  function toggleChecklist(taskId: string, chkId: string) {
    setProjectItems((prev) =>
      prev.map((i) =>
        i.id === taskId
          ? {
              ...i,
              checklist: i.checklist.map((c) =>
                c.id === chkId ? { ...c, done: !c.done } : c
              ),
            }
          : i
      )
    );
  }

  function removeChecklist(taskId: string, chkId: string) {
    setProjectItems((prev) =>
      prev.map((i) =>
        i.id === taskId
          ? { ...i, checklist: i.checklist.filter((c) => c.id !== chkId) }
          : i
      )
    );
  }

  function toggleShopping(poolId: string) {
    setShoppingPool((prev) => prev.filter((p) => p.id !== poolId));
  }

  const picking = projectItems.find((i) => i.id === pickingId) || null;

  return (
    <div className="flex h-full flex-col">
      <SubHeader title="Ten tydzień" onBack={onBack} />

      <div className="min-h-0 flex-1 overflow-y-auto pr-1 pb-6">
        <div className="mb-3 text-[13px] leading-5 text-slate-500">
          Wydarzenia i zadania na najbliższe 7 dni.
        </div>

        <div className="space-y-4">
          {days.map((day) => {
            const dayEvents = events.filter((e) => e.date === day.key);
            const dayTasks = projectItems.filter((t) => t.dueAt === day.key);
            const isEmpty = dayEvents.length === 0 && dayTasks.length === 0;

            return (
              <div key={day.key}>
                <div className="mb-2 flex items-center justify-between">
                  <div className="text-[15px] font-bold text-slate-800">{day.label}</div>
                  {!isEmpty ? (
                    <div className="text-[12px] text-slate-400">
                      {dayEvents.length + dayTasks.length}{' '}
                      {dayEvents.length + dayTasks.length === 1 ? 'pozycja' : 'pozycji'}
                    </div>
                  ) : null}
                </div>

                {isEmpty ? (
                  <div className="rounded-[14px] bg-white/40 px-3 py-2 text-[12px] text-slate-400">
                    Nic zaplanowanego
                  </div>
                ) : (
                  <div className="space-y-2">
                    {dayEvents
                      .slice()
                      .sort((a, b) => (a.time || '').localeCompare(b.time || ''))
                      .map((e) => (
                        <div
                          key={e.id}
                          className="flex items-center gap-3 rounded-[14px] bg-white/75 px-3 py-2.5 shadow-sm"
                        >
                          <div className={`h-2 w-2 shrink-0 rounded-full ${e.dotClass}`} />
                          <div className="shrink-0 text-[13px] font-bold text-slate-700">
                            {e.time || '—'}
                          </div>
                          <div className="min-w-0 flex-1 truncate text-[14px] text-slate-800">
                            {e.title}
                          </div>
                          <span
                            className={`shrink-0 rounded-full px-2 py-0.5 text-[10px] font-semibold ${e.badgeClass}`}
                          >
                            {e.badge}
                          </span>
                        </div>
                      ))}
                    {dayTasks.map((item) => (
                      <TaskRow
                        key={item.id}
                        item={item}
                        onToggle={() => toggleDone(item.id)}
                        onPickDate={() => setPickingId(item.id)}
                        onDelete={() => removeItem(item.id)}
                        showCategory
                        expanded={expandedId === item.id}
                        onToggleExpand={() =>
                          setExpandedId((cur) => (cur === item.id ? null : item.id))
                        }
                        shoppingPool={shoppingPool}
                        onShoppingToggle={toggleShopping}
                        onChecklistAdd={(label) => addChecklist(item.id, label)}
                        onChecklistToggle={(chkId) => toggleChecklist(item.id, chkId)}
                        onChecklistRemove={(chkId) => removeChecklist(item.id, chkId)}
                      />
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      {picking ? (
        <DatePickerPopup
          value={picking.dueAt}
          valueTime={picking.time}
          onChange={(d, t) => setDueAt(picking.id, d, t)}
          onClose={() => setPickingId(null)}
        />
      ) : null}
    </div>
  );
}

function SettingsScreen({
  path,
  setPath,
}: {
  path: SettingsPath;
  setPath: (p: SettingsPath) => void;
}) {
  const [ollamaUrl, setOllamaUrl] = useState(() => readOllamaUrl());
  const [ollamaModel, setOllamaModel] = useState(() => readOllamaModel());
  const [status, setStatus] = useState('Nie sprawdzono połączenia.');
  const [testing, setTesting] = useState(false);
  const [permStatus, setPermStatus] = useState<string>('');

  const [notif, setNotif] = useState(() => {
    if (typeof Notification !== 'undefined' && Notification.permission === 'granted') return true;
    try {
      return localStorage.getItem(PERM_NOTIFICATIONS_KEY) === '1';
    } catch {
      return false;
    }
  });
  const [mic, setMic] = useState(() => {
    try {
      return localStorage.getItem(PERM_MIC_KEY) === '1';
    } catch {
      return false;
    }
  });
  const [loc, setLoc] = useState(() => {
    try {
      return localStorage.getItem(PERM_LOCATION_KEY) === '1';
    } catch {
      return false;
    }
  });

  function saveOllama() {
    const url = cleanUrl(ollamaUrl);
    const model = ollamaModel.trim() || DEFAULT_OLLAMA_MODEL;
    try {
      localStorage.setItem(OLLAMA_URL_KEY, url);
      localStorage.setItem(OLLAMA_MODEL_KEY, model);
    } catch {}
    setOllamaUrl(url);
    setOllamaModel(model);
    setStatus('Zapisano.');
  }

  async function testConnection() {
    const url = cleanUrl(ollamaUrl);
    if (!url) {
      setStatus('Podaj adres Ollamy.');
      return;
    }
    setTesting(true);
    setStatus('Sprawdzam połączenie...');
    try {
      try {
        localStorage.setItem(OLLAMA_URL_KEY, url);
      } catch {}
      setOllamaUrl(url);
      const res = await fetch(`${url}/api/tags`, { headers: { Accept: 'application/json' } });
      if (!res.ok) {
        setStatus(`Błąd połączenia: HTTP ${res.status}`);
        return;
      }
      const data = await res.json();
      const models = Array.isArray(data?.models) ? data.models : [];
      const first = models[0]?.name || models[0]?.model || null;
      setStatus(first ? `Połączenie OK. Wykryty model: ${first}` : 'Połączenie OK. Ollama odpowiada.');
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'nieznany błąd';
      setStatus(`Brak połączenia: ${msg}`);
    } finally {
      setTesting(false);
    }
  }

  function isInsecureLan() {
    if (typeof window === 'undefined') return false;
    if (window.isSecureContext) return false;
    const h = window.location.hostname;
    return h !== 'localhost' && h !== '127.0.0.1' && h !== '::1';
  }

  async function toggleNotifications(next: boolean) {
    if (!next) {
      setNotif(false);
      setPermStatus('Powiadomienia wyłączone.');
      try {
        localStorage.setItem(PERM_NOTIFICATIONS_KEY, '0');
      } catch {}
      return;
    }
    if (typeof Notification === 'undefined') {
      setPermStatus('Powiadomienia nie są wspierane w tej przeglądarce.');
      return;
    }
    if (isInsecureLan()) {
      setPermStatus(
        'Powiadomienia wymagają HTTPS lub localhost. Na telefonie przez Wi-Fi nie zadziałają — zadziała po spakowaniu w Capacitor.'
      );
      return;
    }
    if (Notification.permission === 'denied') {
      setPermStatus(
        'Powiadomienia są zablokowane w ustawieniach przeglądarki dla tej strony. Odblokuj je w pasku adresu (ikona kłódki → Powiadomienia → Zezwól) i spróbuj ponownie.'
      );
      return;
    }
    try {
      const perm = await Notification.requestPermission();
      const granted = perm === 'granted';
      setNotif(granted);
      setPermStatus(
        granted
          ? 'Powiadomienia włączone.'
          : perm === 'denied'
          ? 'Odmówiono zgody. Odblokuj w ustawieniach strony w przeglądarce.'
          : 'Zgoda nie została przyznana.'
      );
      try {
        localStorage.setItem(PERM_NOTIFICATIONS_KEY, granted ? '1' : '0');
      } catch {}
    } catch (e) {
      const msg = e instanceof Error ? e.message : 'nieznany błąd';
      setPermStatus(`Błąd powiadomień: ${msg}`);
    }
  }

  async function toggleMic(next: boolean) {
    if (!next) {
      setMic(false);
      setPermStatus('Mikrofon wyłączony.');
      try {
        localStorage.setItem(PERM_MIC_KEY, '0');
      } catch {}
      return;
    }
    if (isInsecureLan()) {
      setPermStatus('Mikrofon wymaga HTTPS lub localhost.');
      return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      stream.getTracks().forEach((t) => t.stop());
      setMic(true);
      setPermStatus('Mikrofon włączony.');
      try {
        localStorage.setItem(PERM_MIC_KEY, '1');
      } catch {}
    } catch (e) {
      setMic(false);
      const msg = e instanceof Error ? e.message : 'odmowa';
      setPermStatus(`Odmowa dostępu do mikrofonu: ${msg}`);
      try {
        localStorage.setItem(PERM_MIC_KEY, '0');
      } catch {}
    }
  }

  function toggleLocation(next: boolean) {
    if (!next) {
      setLoc(false);
      setPermStatus('Lokalizacja wyłączona.');
      try {
        localStorage.setItem(PERM_LOCATION_KEY, '0');
      } catch {}
      return;
    }
    if (!('geolocation' in navigator)) {
      setPermStatus('Lokalizacja nie jest wspierana w tej przeglądarce.');
      return;
    }
    if (isInsecureLan()) {
      setPermStatus('Lokalizacja wymaga HTTPS lub localhost.');
      return;
    }
    navigator.geolocation.getCurrentPosition(
      () => {
        setLoc(true);
        setPermStatus('Lokalizacja włączona.');
        try {
          localStorage.setItem(PERM_LOCATION_KEY, '1');
        } catch {}
      },
      (err) => {
        setLoc(false);
        setPermStatus(`Odmowa dostępu do lokalizacji: ${err.message}`);
        try {
          localStorage.setItem(PERM_LOCATION_KEY, '0');
        } catch {}
      }
    );
  }

  if (path === 'account') {
    return <AccountScreen onBack={() => setPath('root')} onNavigate={setPath} />;
  }
  if (path === 'profile') {
    return <ProfileScreen onBack={() => setPath('account')} />;
  }
  if (path === 'security') {
    return <SecurityScreen onBack={() => setPath('account')} />;
  }
  if (path === 'plan') {
    return <BillingScreen onBack={() => setPath('account')} />;
  }
  if (path === 'integrations') {
    return <IntegrationsScreen onBack={() => setPath('account')} />;
  }
  if (path === 'data') {
    return <DataScreen onBack={() => setPath('account')} />;
  }

  return (
    <div className="flex h-full flex-col">
      <Header title="Ustawienia" subtitle={copy.version} icon={<Cog className="h-10 w-10 text-indigo-300" />} />

      <div className="min-h-0 flex-1 overflow-y-auto pr-1 pb-6">
        <div className="space-y-5">
          <div>
            <h3 className="mb-3 text-[20px] font-semibold text-slate-800">Konto</h3>

            <div className="rounded-[22px] bg-white/75 p-3 shadow-sm">
              <button
                type="button"
                onClick={() => setPath('account')}
                className="flex w-full items-center justify-between gap-3 px-3 py-4 text-left"
              >
                <div className="flex items-center gap-4">
                  <UserCircle2 className="h-8 w-8 text-indigo-300" />
                  <span className="text-[18px] text-slate-700">Moje konto</span>
                </div>
                <ChevronRight className="h-7 w-7 text-indigo-300" />
              </button>
            </div>

            <div className="mt-4 rounded-[22px] bg-white/75 p-5 shadow-sm">
              <div className="flex items-start gap-4">
                <div
                  className="flex h-20 w-20 shrink-0 items-center justify-center rounded-[18px]"
                  style={{ backgroundColor: '#11111115' }}
                >
                  <SiOllama size={40} color="#111111" />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="text-[18px] font-semibold text-slate-800">Ollama</div>
                  <div className="mt-1 text-[14px] leading-5 text-slate-500">{status}</div>
                </div>
              </div>

              <div className="mt-4 space-y-3">
                <div>
                  <label className="mb-1 block text-[13px] font-medium text-slate-500">Adres Ollamy</label>
                  <input
                    value={ollamaUrl}
                    onChange={(e) => setOllamaUrl(e.target.value)}
                    placeholder={DEFAULT_OLLAMA_URL}
                    className="w-full rounded-[14px] border border-slate-200 bg-white px-3 py-2 text-[15px] text-slate-700 outline-none focus:border-indigo-300"
                    autoCapitalize="off"
                    autoCorrect="off"
                    spellCheck={false}
                  />
                </div>
                <div>
                  <label className="mb-1 block text-[13px] font-medium text-slate-500">Model</label>
                  <input
                    value={ollamaModel}
                    onChange={(e) => setOllamaModel(e.target.value)}
                    placeholder={DEFAULT_OLLAMA_MODEL}
                    className="w-full rounded-[14px] border border-slate-200 bg-white px-3 py-2 text-[15px] text-slate-700 outline-none focus:border-indigo-300"
                    autoCapitalize="off"
                    autoCorrect="off"
                    spellCheck={false}
                  />
                </div>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={saveOllama}
                    className="flex-1 rounded-full bg-slate-100 px-4 py-2.5 text-[14px] font-semibold text-slate-700"
                  >
                    Zapisz
                  </button>
                  <button
                    type="button"
                    onClick={testConnection}
                    disabled={testing}
                    className="flex-1 rounded-full bg-[linear-gradient(90deg,#4f75ff,#3b82f6)] px-4 py-2.5 text-[14px] font-semibold text-white disabled:opacity-60"
                  >
                    {testing ? 'Sprawdzam...' : 'Sprawdź połączenie'}
                  </button>
                </div>
              </div>
            </div>
          </div>

          <div>
            <h3 className="mb-3 text-[20px] font-semibold text-slate-800">Pozwolenia</h3>

            <div className="rounded-[22px] bg-white/75 p-3 shadow-sm">
              <ToggleRow
                icon={<Bell className="h-7 w-7 text-indigo-300" />}
                title="Powiadomienia"
                checked={notif}
                onChange={toggleNotifications}
              />
              <div className="border-b border-slate-200" />
              <ToggleRow
                icon={<Mic className="h-7 w-7 text-indigo-300" />}
                title="Dostęp do mikrofonu"
                checked={mic}
                onChange={toggleMic}
              />
              <div className="border-b border-slate-200" />
              <ToggleRow
                icon={<MapPin className="h-7 w-7 text-indigo-300" />}
                title="Dostęp do lokalizacji"
                checked={loc}
                onChange={toggleLocation}
              />
            </div>

            {permStatus ? (
              <div className="mt-3 rounded-[14px] bg-white/60 px-4 py-3 text-[13px] leading-5 text-slate-600">
                {permStatus}
              </div>
            ) : null}
          </div>

          <div className="h-12 rounded-[22px] bg-white/40" />
        </div>
      </div>
    </div>
  );
}

export default function App() {
  const today = new Date();
  const initialWeekStart = startOfWeek(today);

  const defaultEvents: CalendarEvent[] = [
    {
      id: '1',
      date: toDateKey(addDays(initialWeekStart, 0)),
      time: '09:00',
      title: 'Joga',
      location: 'Fitness Club',
      badge: '45 min',
      dotClass: 'bg-violet-500',
      badgeClass: 'bg-violet-500/10 text-violet-600',
      note: 'Zabrać matę i butelkę wody.',
      checklist: [
        { id: '1-1', label: 'Strój sportowy', done: true },
        { id: '1-2', label: 'Mata', done: false },
      ],
      linkedShoppingItemIds: [],
      shoppingItems: [],
    },
    {
      id: '2',
      date: toDateKey(addDays(initialWeekStart, 1)),
      time: '10:30',
      title: 'Spotkanie z zespołem',
      location: 'Biuro + Online (4 osoby)',
      badge: 'Zespół',
      dotClass: 'bg-blue-500',
      badgeClass: 'bg-blue-500/10 text-blue-600',
      note: 'Omówić plan sprintu i priorytety tygodnia.',
      checklist: [
        { id: '2-1', label: 'Agenda spotkania', done: true },
        { id: '2-2', label: 'Podsumowanie sprintu', done: false },
      ],
      linkedShoppingItemIds: [],
      shoppingItems: [],
    },
    {
      id: '3',
      date: toDateKey(addDays(initialWeekStart, 2)),
      time: '12:00',
      title: 'Lunch z Anną',
      location: 'Restauracja „Zdrowa Kuchnia”',
      badge: '90 min',
      dotClass: 'bg-emerald-500',
      badgeClass: 'bg-emerald-500/10 text-emerald-600',
      note: 'Rezerwacja na nazwisko Wysocka.',
      checklist: [],
      linkedShoppingItemIds: [],
      shoppingItems: [],
    },
    {
      id: '4',
      date: toDateKey(addDays(initialWeekStart, 3)),
      time: '14:00',
      title: 'Przegląd projektu',
      location: 'Przygotować prezentację',
      badge: 'Praca',
      dotClass: 'bg-orange-500',
      badgeClass: 'bg-orange-500/10 text-orange-600',
      note: 'Sprawdzić status backendu i frontendowego kalendarza.',
      checklist: [
        { id: '4-1', label: 'Slajdy', done: false },
        { id: '4-2', label: 'Demo', done: false },
      ],
      linkedShoppingItemIds: [],
      shoppingItems: [],
    },
    {
      id: '5',
      date: toDateKey(addDays(initialWeekStart, 3)),
      time: '16:30',
      title: 'Zakupy w Biedronce',
      location: 'Biedronka osiedlowa',
      badge: 'Zakupy',
      dotClass: 'bg-rose-500',
      badgeClass: 'bg-rose-500/10 text-rose-600',
      note: 'Sprawdź, co już jest w domu.',
      linkedShoppingItemIds: ['pool-1', 'pool-2'],
      shoppingItems: [],
    },
    {
      id: '6',
      date: toDateKey(addDays(initialWeekStart, 5)),
      time: '18:00',
      title: 'Trening siłowy',
      location: 'Siłownia Power Gym',
      badge: '75 min',
      dotClass: 'bg-slate-500',
      badgeClass: 'bg-slate-500/10 text-slate-600',
      note: 'Dzień nóg + rozciąganie.',
      checklist: [{ id: '6-1', label: 'Karnet', done: true }],
      linkedShoppingItemIds: [],
      shoppingItems: [],
    },
  ];

  const defaultShoppingPool: ShoppingPoolItem[] = [
    { id: 'pool-1', label: 'Pasta do zębów', done: false, linkedEventIds: ['5'] },
    { id: 'pool-2', label: 'Szampon', done: false, linkedEventIds: ['5'] },
    { id: 'pool-3', label: 'Mleko', done: false, linkedEventIds: [] },
    { id: 'pool-4', label: 'Makaron', done: false, linkedEventIds: [] },
  ];

  const defaultProjectItems: ProjectItem[] = [
    { id: 'project-1', label: 'Umówić spotkanie z zespołem', category: 'general', done: false, source: 'manual', dueAt: null, time: null, checklist: [] },
    { id: 'project-2', label: 'Muszę przeczytać książkę "Tysiąc mil podwodnej żeglugi"', category: 'reading', done: false, source: 'manual', dueAt: null, time: null, checklist: [] },
    { id: 'project-3', label: 'Mam pomysł na tracker', category: 'ideas', done: false, source: 'manual', dueAt: null, time: null, checklist: [] },
    { id: 'project-4', label: 'Sprawdzić dobrą aplikację do CRM', category: 'to_check', done: false, source: 'manual', dueAt: null, time: null, checklist: [] },
    { id: 'project-5', label: 'Kupić prezent na urodziny Ani', category: 'shopping', done: false, source: 'manual', dueAt: null, time: null, checklist: [] },
  ];

  const [activeTab, setActiveTab] = useState<TabId>('home');
  const [shoppingPool, setShoppingPool] = useState<ShoppingPoolItem[]>(() => {
    try {
      const raw = window.localStorage.getItem(STORAGE_KEY);
      if (!raw) return defaultShoppingPool;
      const parsed = JSON.parse(raw);
      return parsed.shoppingPool ?? defaultShoppingPool;
    } catch {
      return defaultShoppingPool;
    }
  });

  const [events, setEvents] = useState<CalendarEvent[]>(() => {
    try {
      const raw = window.localStorage.getItem(STORAGE_KEY);
      if (!raw) return defaultEvents;
      const parsed = JSON.parse(raw);
      return parsed.events ?? defaultEvents;
    } catch {
      return defaultEvents;
    }
  });

  const [projectItems, setProjectItems] = useState<ProjectItem[]>(() => {
    try {
      const raw = window.localStorage.getItem(STORAGE_KEY);
      if (!raw) return defaultProjectItems;
      const parsed = JSON.parse(raw);
      const stored: unknown = parsed.projectItems;
      if (!Array.isArray(stored)) return defaultProjectItems;
      return stored.map((item: any) => ({
        id: String(item?.id ?? `project-${Math.random().toString(36).slice(2)}`),
        label: String(item?.label ?? ''),
        category: item?.category ?? 'general',
        done: !!item?.done,
        source: item?.source ?? 'manual',
        dueAt: typeof item?.dueAt === 'string' ? item.dueAt : null,
        time: typeof item?.time === 'string' ? item.time : null,
        checklist: Array.isArray(item?.checklist)
          ? item.checklist
              .filter((c: any) => c && typeof c.label === 'string')
              .map((c: any) => ({
                id: String(c.id ?? `chk-${Math.random().toString(36).slice(2)}`),
                label: String(c.label),
                done: !!c.done,
              }))
          : [],
      }));
    } catch {
      return defaultProjectItems;
    }
  });

  const [chatMessages, setChatMessages] = useState<ChatMessage[]>(() => {
    try {
      const raw = window.localStorage.getItem(STORAGE_KEY);
      if (!raw) return [];
      const parsed = JSON.parse(raw);
      return parsed.chatMessages ?? [];
    } catch {
      return [];
    }
  });

  useEffect(() => {
    try {
      window.localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({
          shoppingPool,
          events,
          projectItems,
          chatMessages,
        })
      );
    } catch {
      // ignore local storage errors
    }
  }, [shoppingPool, events, projectItems, chatMessages]);

  function handleShoppingDetected(itemLabel: string) {
    setShoppingPool((prev) => {
      const exists = prev.some((item) => item.label.toLowerCase() === itemLabel.toLowerCase());
      if (exists) return prev;
      return [
        ...prev,
        {
          id: `pool-${Date.now()}`,
          label: itemLabel,
          done: false,
          linkedEventIds: [],
        },
      ];
    });
  }

  function handleProjectDetected(text: string) {
    const trimmed = text.trim();
    if (!trimmed) return;

    const category = extractProjectCategoryFromChat(trimmed);

    setProjectItems((prev) => {
      const exists = prev.some((item) => item.label.toLowerCase() === trimmed.toLowerCase());
      if (exists) return prev;

      return [
        ...prev,
        {
          id: `project-${Date.now()}`,
          label: trimmed,
          category,
          done: false,
          source: 'chat',
          dueAt: null,
          time: null,
          checklist: [],
        },
      ];
    });
  }

  const [settingsPath, setSettingsPath] = useState<SettingsPath>('root');
  const [showNotifications, setShowNotifications] = useState(false);
  const [homeDetail, setHomeDetail] = useState<HomeDetailView>(null);
  const [readIds, setReadIds] = useState<string[]>(() => readIdList(NOTIFICATIONS_READ_KEY));
  const [dismissedIds, setDismissedIds] = useState<string[]>(() =>
    readIdList(NOTIFICATIONS_DISMISSED_KEY)
  );

  const visibleNotifications = useMemo(
    () => MOCK_NOTIFICATIONS.filter((n) => !dismissedIds.includes(n.id)),
    [dismissedIds]
  );

  const unreadCount = useMemo(
    () => visibleNotifications.filter((n) => !readIds.includes(n.id)).length,
    [visibleNotifications, readIds]
  );

  function markAsRead(id: string) {
    setReadIds((prev) => {
      if (prev.includes(id)) return prev;
      const next = [...prev, id];
      writeIdList(NOTIFICATIONS_READ_KEY, next);
      return next;
    });
  }

  function markAllRead() {
    const allIds = MOCK_NOTIFICATIONS.map((n) => n.id);
    setReadIds(allIds);
    writeIdList(NOTIFICATIONS_READ_KEY, allIds);
  }

  function dismissNotification(id: string) {
    setDismissedIds((prev) => {
      if (prev.includes(id)) return prev;
      const next = [...prev, id];
      writeIdList(NOTIFICATIONS_DISMISSED_KEY, next);
      return next;
    });
  }

  function clearAllNotifications() {
    const allIds = MOCK_NOTIFICATIONS.map((n) => n.id);
    setDismissedIds(allIds);
    writeIdList(NOTIFICATIONS_DISMISSED_KEY, allIds);
  }

  function goToTab(tab: TabId) {
    setActiveTab(tab);
    if (tab === 'settings') setSettingsPath('root');
    setShowNotifications(false);
    setHomeDetail(null);
  }

  const navValue: NavContextType = {
    goToAccount: () => {
      setActiveTab('settings');
      setSettingsPath('account');
      setShowNotifications(false);
      setHomeDetail(null);
    },
    openNotifications: () => setShowNotifications(true),
    unreadCount,
  };

  let screen: React.ReactNode;

  if (showNotifications) {
    screen = (
      <NotificationsScreen
        notifications={visibleNotifications}
        readIds={readIds}
        onMarkAsRead={markAsRead}
        onMarkAllRead={markAllRead}
        onDismiss={dismissNotification}
        onClearAll={clearAllNotifications}
        onClose={() => setShowNotifications(false)}
      />
    );
  } else if (homeDetail === 'inbox-tasks') {
    screen = (
      <InboxTasksScreen
        projectItems={projectItems}
        setProjectItems={setProjectItems}
        shoppingPool={shoppingPool}
        setShoppingPool={setShoppingPool}
        onBack={() => setHomeDetail(null)}
      />
    );
  } else if (homeDetail === 'seven-days') {
    screen = (
      <SevenDaysScreen
        events={events}
        projectItems={projectItems}
        setProjectItems={setProjectItems}
        shoppingPool={shoppingPool}
        setShoppingPool={setShoppingPool}
        onBack={() => setHomeDetail(null)}
      />
    );
  } else {
    switch (activeTab) {
      case 'chat':
        screen = (
          <ChatScreen
            onShoppingDetected={handleShoppingDetected}
            onProjectDetected={handleProjectDetected}
            chatMessages={chatMessages}
            setChatMessages={setChatMessages}
          />
        );
        break;
      case 'plan':
        screen = <PlanScreen />;
        break;
      case 'calendar':
        screen = (
          <CalendarScreen
            shoppingPool={shoppingPool}
            setShoppingPool={setShoppingPool}
            events={events}
            setEvents={setEvents}
          />
        );
        break;
      case 'projects':
        screen = (
          <ProjectsScreen
            projectItems={projectItems}
            setProjectItems={setProjectItems}
            shoppingPool={shoppingPool}
            setShoppingPool={setShoppingPool}
          />
        );
        break;
      case 'settings':
        screen = <SettingsScreen path={settingsPath} setPath={setSettingsPath} />;
        break;
      case 'home':
      default:
        screen = (
          <HomeScreen
            setActiveTab={setActiveTab}
            projectItems={projectItems}
            events={events}
            onOpenInbox={() => setHomeDetail('inbox-tasks')}
            onOpenWeek={() => setHomeDetail('seven-days')}
          />
        );
        break;
    }
  }

  return (
    <NavContext.Provider value={navValue}>
      <PhoneShell activeTab={activeTab} setActiveTab={goToTab}>
        {screen}
      </PhoneShell>
    </NavContext.Provider>
  );
}



