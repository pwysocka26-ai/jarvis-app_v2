import React, { useEffect, useMemo, useRef, useState } from 'react';
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
  Inbox,
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
  SlidersHorizontal,
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
} from 'lucide-react';

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

const OLLAMA_MODEL = 'llama3.2';

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
          <h1 className="text-[34px] font-semibold leading-none tracking-[-0.05em] text-slate-800">
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
        {showBell ? (
          <div className="relative">
            <Bell className="h-8 w-8 text-slate-700" />
            <div className="absolute -right-1 -top-2 flex h-7 w-7 items-center justify-center rounded-full bg-pink-400 text-sm font-semibold text-white">
              3
            </div>
          </div>
        ) : null}

        {showProfile ? (
          <div className="h-14 w-14 overflow-hidden rounded-full border-2 border-indigo-200 shadow-sm">
            <img
              src="https://i.pravatar.cc/100?img=12"
              alt="Profil"
              className="h-full w-full object-cover"
            />
          </div>
        ) : null}
      </div>
    </header>
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

      <div className="text-[26px] font-semibold leading-none tracking-[-0.05em] text-slate-800">
        {value}
      </div>
      <div className="mt-2 text-[12px] text-slate-500">{subtitle}</div>
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

function HomeScreen({ setActiveTab }: { setActiveTab: (tab: TabId) => void }) {
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

          <div className="min-w-0 flex-1 pr-1">
            <h2 className="text-[24px] font-semibold leading-tight tracking-[-0.05em] text-slate-800">
              {copy.welcome} {copy.wave}
            </h2>
            <p className="mt-1 text-[14px] leading-5 text-slate-600">
              {copy.todayLine1}
              <span className="font-semibold text-slate-800">{copy.tasks10}</span>
              {copy.todayLine2}
              <span className="font-semibold text-slate-800">{copy.meeting1}</span>
              {copy.todayLine3}
              <span className="font-semibold text-slate-800">{copy.todayLine4}</span>.
            </p>
          </div>
        </div>
      </section>

      <section className="mb-3 grid grid-cols-2 gap-4">
        <DashboardCard
          icon={<CheckSquare className="h-5 w-5 text-orange-400" />}
          title={copy.cardToday}
          value="10"
          subtitle={copy.tasksLabel}
          bg="bg-[linear-gradient(135deg,#f7efe9_0%,#f4efed_100%)]"
          onClick={() => setActiveTab('plan')}
        />
        <DashboardCard
          icon={<Calendar className="h-5 w-5 text-violet-400" />}
          title={copy.cardTodo}
          value="5"
          subtitle={copy.tasksLabel}
          bg="bg-[linear-gradient(135deg,#f0eefb_0%,#f2f0fb_100%)]"
          onClick={() => setActiveTab('plan')}
        />
        <DashboardCard
          icon={<CalendarDays className="h-5 w-5 text-cyan-400" />}
          title={copy.cardWeek}
          value="3"
          subtitle={copy.tasksLabel}
          bg="bg-[linear-gradient(135deg,#ecf5f5_0%,#edf2f2_100%)]"
          onClick={() => setActiveTab('calendar')}
        />
        <DashboardCard
          icon={<Inbox className="h-5 w-5 text-violet-400" />}
          title={copy.cardProjects}
          value="15"
          subtitle={copy.tasksLabel}
          bg="bg-[linear-gradient(135deg,#f0eefb_0%,#f2f0fb_100%)]"
          onClick={() => setActiveTab('projects')}
        />
      </section>

      <section className="mb-2">
        <div className="mb-2 flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <Settings className="h-7 w-7 text-violet-400" />
            <h3 className="text-[18px] font-semibold tracking-[-0.03em] text-slate-800">
              {copy.upcoming}
            </h3>
          </div>

          <button
            className="flex shrink-0 items-center gap-1 text-[14px] font-medium text-indigo-400"
            onClick={() => setActiveTab('plan')}
            type="button"
          >
            {copy.seeAll}
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>

        <div className="rounded-[22px] bg-white/75 p-3 shadow-sm">
          <button
            className="flex w-full items-center justify-between gap-3 border-b border-slate-200 pb-3 text-left"
            onClick={() => setActiveTab('plan')}
            type="button"
          >
            <div className="flex min-w-0 items-center gap-3">
              <div className="h-4 w-4 shrink-0 rounded-full bg-violet-400" />
              <div className="shrink-0 text-[15px] font-semibold text-slate-800">11:00</div>
              <div className="truncate text-[15px] text-slate-700">{copy.event1}</div>
            </div>

            <div className="shrink-0 rounded-2xl bg-violet-100 px-3 py-1.5 text-[13px] font-medium text-violet-500">
              {copy.meetingTag}
            </div>
          </button>

          <button
            className="flex w-full items-center justify-between gap-3 pt-3 text-left"
            onClick={() => setActiveTab('plan')}
            type="button"
          >
            <div className="flex min-w-0 items-center gap-3">
              <div className="h-4 w-4 shrink-0 rounded-full bg-orange-300" />
              <div className="shrink-0 text-[15px] font-semibold text-slate-800">15:30</div>
              <div className="truncate text-[15px] text-slate-700">{copy.event2}</div>
            </div>

            <div className="shrink-0 rounded-2xl bg-orange-100 px-3 py-1.5 text-[13px] font-medium text-orange-400">
              {copy.taskTag}
            </div>
          </button>
        </div>
      </section>

      <div className="mt-auto flex justify-end pb-2 pr-2">
        <button className="z-20 flex h-14 w-14 items-center justify-center rounded-full bg-[linear-gradient(180deg,#7196ff_0%,#4f75ff_100%)] text-white shadow-[0_18px_30px_rgba(77,116,255,0.28)] transition hover:scale-105" type="button">
          <Plus className="h-7 w-7" />
        </button>
      </div>
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

function ChatScreen() {
  const inputRef = useRef<HTMLInputElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [message, setMessage] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isSending]);

  async function sendMessage() {
    const trimmed = message.trim();
    if (!trimmed || isSending) return;

    const userMessage: ChatMessage = {
      id: `u-${Date.now()}`,
      role: 'user',
      text: trimmed,
    };

    const nextMessages = [...messages, userMessage];
    setMessages(nextMessages);
    setMessage('');
    setIsSending(true);

    try {
      const response = await fetch('http://127.0.0.1:11434/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model: OLLAMA_MODEL,
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
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();
      const assistantText =
        data?.message?.content?.trim() ||
        'Nie udało się pobrać odpowiedzi z Ollamy.';

      setMessages((prev) => [
        ...prev,
        {
          id: `a-${Date.now()}`,
          role: 'assistant',
          text: assistantText,
        },
      ]);
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        {
          id: `e-${Date.now()}`,
          role: 'assistant',
          text: 'Nie mogę połączyć się z Ollamą. Upewnij się, że Ollama działa lokalnie i masz model ' + OLLAMA_MODEL + '.',
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
        showProfile={false}
        showBell={false}
        extraLeft={<ChevronLeft className="mt-1 h-10 w-10 text-indigo-500" />}
        extraRight={
          <div className="rounded-full border border-indigo-200 p-3">
            <MoreVertical className="h-8 w-8 text-indigo-400" />
          </div>
        }
      />

      <div className="-mx-5 min-h-0 flex-1 bg-[linear-gradient(180deg,#edf1f9_0%,#ebedf5_100%)] px-5 py-5">
        <div className="flex h-full flex-col">
          <div className="min-h-0 flex-1 overflow-y-auto rounded-[30px] bg-transparent">
            {messages.length === 0 ? (
              <div className="flex h-full items-center justify-center px-8 text-center text-[16px] text-slate-400">
                Napisz pierwszą wiadomość do Jarvisa.
              </div>
            ) : (
              <div className="space-y-4 pb-4">
                {messages.map((msg) => (
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

function CalendarScreen() {
  const today = useMemo(() => new Date(), []);
  const initialWeekStart = useMemo(() => startOfWeek(today), [today]);

  const initialEvents = useMemo<CalendarEvent[]>(
    () => [
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
        checklist: [],
        linkedShoppingItemIds: ['pool-1', 'pool-2'],
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
      },
    ],
    [initialWeekStart]
  );

  const initialShoppingPool: ShoppingPoolItem[] = [
    { id: 'pool-1', label: 'Pasta do zębów', done: false, linkedEventIds: ['5'] },
    { id: 'pool-2', label: 'Szampon', done: false, linkedEventIds: ['5'] },
    { id: 'pool-3', label: 'Mleko', done: false, linkedEventIds: [] },
    { id: 'pool-4', label: 'Makaron', done: false, linkedEventIds: [] },
  ];

  const [events, setEvents] = useState<CalendarEvent[]>(initialEvents);
  const [shoppingPool, setShoppingPool] = useState<ShoppingPoolItem[]>(initialShoppingPool);
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

    const event: CalendarEvent = {
      id: `event-${Date.now()}`,
      title: trimmedTitle,
      date: effectiveSelectedDate,
      time: newEventTime || '10:00',
      location: newEventLocation.trim() || 'Brak miejsca',
      badge: isShoppingEventTitle(trimmedTitle) ? 'Zakupy' : 'Nowe',
      dotClass: isShoppingEventTitle(trimmedTitle) ? 'bg-rose-500' : 'bg-indigo-500',
      badgeClass: isShoppingEventTitle(trimmedTitle)
        ? 'bg-rose-500/10 text-rose-600'
        : 'bg-indigo-500/10 text-indigo-600',
      note: newEventNote.trim(),
      checklist: buildChecklistItems(newEventChecklist),
      linkedShoppingItemIds: [],
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

  function addShoppingPoolItem() {
    const trimmed = newShoppingPoolItem.trim();
    if (!trimmed) return;
    setShoppingPool((prev) => [
      ...prev,
      { id: `pool-${Date.now()}`, label: trimmed, done: false, linkedEventIds: [] },
    ]);
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

  function toggleShoppingItemDone(itemId: string) {
    setShoppingPool((prev) =>
      prev.map((item) => (item.id === itemId ? { ...item, done: !item.done } : item))
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
        extraRight={<Mail className="h-8 w-8 text-indigo-300" />}
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
              const suggestedPoolItems = shoppingPool.filter(
                (item) => !(event.linkedShoppingItemIds || []).includes(item.id)
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

                        <div>
                          <div className="mb-2 text-[13px] font-semibold uppercase tracking-wide text-slate-400">
                            Checklista
                          </div>
                          <div className="space-y-2">
                            {event.checklist && event.checklist.length > 0 ? (
                              event.checklist.map((item) => (
                                <button
                                  key={item.id}
                                  type="button"
                                  onClick={() => toggleChecklistItem(event.id, item.id)}
                                  className="flex items-center gap-3 text-[15px] text-slate-700"
                                >
                                  {item.done ? (
                                    <Check className="h-4 w-4 text-indigo-500" />
                                  ) : (
                                    <Square className="h-4 w-4 text-slate-400" />
                                  )}
                                  <span className={item.done ? 'line-through text-slate-400' : ''}>
                                    {item.label}
                                  </span>
                                </button>
                              ))
                            ) : (
                              <div className="text-[15px] text-slate-500">Brak checklisty.</div>
                            )}
                          </div>
                        </div>

                        {isShopping ? (
                          <div>
                            <div className="mb-2 text-[13px] font-semibold uppercase tracking-wide text-slate-400">
                              Lista zakupów dla tego wydarzenia
                            </div>

                            <div className="space-y-2">
                              {linkedPoolItems.length > 0 ? (
                                linkedPoolItems.map((item) => (
                                  <button
                                    key={item.id}
                                    type="button"
                                    onClick={() => toggleShoppingItemDone(item.id)}
                                    className="flex items-center gap-3 text-[15px] text-slate-700"
                                  >
                                    {item.done ? (
                                      <Check className="h-4 w-4 text-indigo-500" />
                                    ) : (
                                      <Square className="h-4 w-4 text-slate-400" />
                                    )}
                                    <span className={item.done ? 'line-through text-slate-400' : ''}>
                                      {item.label}
                                    </span>
                                  </button>
                                ))
                              ) : (
                                <div className="text-[15px] text-slate-500">Brak przypiętych produktów.</div>
                              )}
                            </div>

                            <div className="mt-4">
                              <div className="mb-2 text-[13px] font-semibold uppercase tracking-wide text-slate-400">
                                Sugerowane z luźnej listy zakupów
                              </div>

                              <div className="space-y-2">
                                {suggestedPoolItems.length > 0 ? (
                                  suggestedPoolItems.map((item) => (
                                    <div key={item.id} className="flex items-center justify-between gap-3 rounded-2xl bg-slate-50 px-3 py-2">
                                      <span className="text-[14px] text-slate-700">{item.label}</span>
                                      <button
                                        type="button"
                                        onClick={() => attachShoppingItemToEvent(event.id, item.id)}
                                        className="rounded-full bg-indigo-100 px-3 py-1 text-[13px] font-medium text-indigo-600"
                                      >
                                        Dodaj
                                      </button>
                                    </div>
                                  ))
                                ) : (
                                  <div className="text-[15px] text-slate-500">Brak dodatkowych sugestii.</div>
                                )}
                              </div>
                            </div>

                            <div className="mt-4">
                              <div className="mb-2 text-[13px] font-semibold uppercase tracking-wide text-slate-400">
                                Dodaj luźno do projektu
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
                                  onClick={addShoppingPoolItem}
                                  className="rounded-full bg-[linear-gradient(90deg,#4f75ff,#3b82f6)] px-4 py-2.5 text-[14px] text-white"
                                >
                                  Dodaj
                                </button>
                              </div>
                            </div>
                          </div>
                        ) : null}
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

              <label className="block">
                <div className="mb-1 text-[13px] font-medium text-slate-500">Checklista</div>
                <textarea
                  value={newEventChecklist}
                  onChange={(e) => setNewEventChecklist(e.target.value)}
                  className="min-h-[90px] w-full rounded-2xl border border-slate-200 px-4 py-3 text-[15px] outline-none"
                  placeholder="Jedna pozycja w linii&#10;Np. Kupić bilet&#10;Sprawdzić agendę"
                />
              </label>
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

function ProjectsScreen() {
  const groups = useMemo(
    () => [
      {
        title: 'Ogólne',
        count: '5',
        icon: <Box className="h-7 w-7 text-indigo-400" />,
        items: [
          'Umówić spotkanie z zespołem',
          'Jak poprawić stronę główną?',
          'Przestać raport kwartalny',
          'Kupić prezent na urodziny Ani',
          'Znaleźć dobrą aplikację do CRM',
        ],
      },
      {
        title: 'Lista zakupów',
        count: '3',
        icon: <ShoppingCart className="h-7 w-7 text-indigo-400" />,
        items: ['Mleko i pieczywo', 'Makaron i warzywa na obiad'],
      },
      {
        title: 'Pomysły',
        count: '6',
        icon: <Lightbulb className="h-7 w-7 text-indigo-400" />,
        items: ['Pomysły na opis nowego projektu', 'Nowy artykuł na bloga o produktywności'],
      },
      {
        title: 'Przeczytać',
        count: '4',
        icon: <BookOpen className="h-7 w-7 text-indigo-400" />,
        items: [],
      },
    ],
    []
  );

  return (
    <div className="flex h-full flex-col">
      <Header title="Projekty" subtitle={copy.version} icon={<Package className="h-10 w-10 text-indigo-300" />} />
      <SearchBar />

      <div className="min-h-0 flex-1 space-y-4 overflow-y-auto pr-1">
        {groups.map((group, groupIndex) => (
          <div key={group.title}>
            <div className="mb-3 flex items-center justify-between">
              <div className="flex items-center gap-3">
                {group.icon}
                <h3 className="text-[20px] font-semibold text-slate-800">{group.title}</h3>
              </div>

              <div className="flex items-center gap-3">
                <div className="rounded-xl bg-indigo-100 px-3 py-1 text-[16px] font-medium text-indigo-400">
                  {group.count}
                </div>
                <ChevronDown className="h-6 w-6 text-indigo-400" />
              </div>
            </div>

            <div className="rounded-[22px] bg-white/75 p-3 shadow-sm">
              {group.items.length === 0 ? (
                <div className="h-20 rounded-[18px] bg-white/40" />
              ) : (
                group.items.map((item, itemIndex) => (
                  <div
                    key={item}
                    className={`flex items-center justify-between gap-3 px-3 py-3 ${
                      itemIndex !== group.items.length - 1 ? 'border-b border-slate-200' : ''
                    }`}
                  >
                    <div className="flex min-w-0 items-center gap-3">
                      <div className={`h-7 w-7 rounded-md border-2 ${groupIndex === 0 && itemIndex === 0 ? 'border-indigo-300 bg-indigo-50' : 'border-slate-300'}`}>
                        {groupIndex === 0 && itemIndex === 0 ? (
                          <Check className="m-0.5 h-5 w-5 text-indigo-400" />
                        ) : null}
                      </div>
                      <span className="truncate text-[17px] text-slate-700">{item}</span>
                    </div>

                    {groupIndex === 0 ? (
                      <div className="rounded-xl bg-indigo-50 px-3 py-1 text-[16px] font-medium text-indigo-400">
                        {[5, 3, 6, 4, 2][itemIndex]}
                      </div>
                    ) : null}
                  </div>
                ))
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function ToggleRow({
  icon,
  title,
}: {
  icon: React.ReactNode;
  title: string;
}) {
  return (
    <div className="flex items-center justify-between px-3 py-4">
      <div className="flex items-center gap-4 min-w-0">
        {icon}
        <span className="text-[18px] text-slate-700">{title}</span>
      </div>

      <div className="flex h-9 w-20 shrink-0 items-center rounded-full bg-indigo-400 px-1">
        <div className="ml-auto flex h-7 w-7 items-center justify-center rounded-full bg-white text-indigo-300">
          <Check className="h-4 w-4" />
        </div>
      </div>
    </div>
  );
}

function SettingsScreen() {
  return (
    <div className="flex h-full flex-col">
      <Header title="Ustawienia" subtitle={copy.version} icon={<Cog className="h-10 w-10 text-indigo-300" />} />
      <SearchBar />

      <div className="min-h-0 flex-1 overflow-y-auto pr-1 pb-6">
        <div className="space-y-5">
          <div>
            <h3 className="mb-3 text-[20px] font-semibold text-slate-800">Konto</h3>

            <div className="rounded-[22px] bg-white/75 p-3 shadow-sm">
              {[
                { icon: <UserCircle2 className="h-8 w-8 text-indigo-300" />, title: 'Moje konto' },
                { icon: <SlidersHorizontal className="h-8 w-8 text-indigo-300" />, title: 'Preferencje' },
              ].map((item) => (
                <div key={item.title} className="flex items-center justify-between border-b border-slate-200 px-3 py-4 last:border-b-0">
                  <div className="flex items-center gap-4">
                    {item.icon}
                    <span className="text-[18px] text-slate-700">{item.title}</span>
                  </div>
                  <ChevronRight className="h-7 w-7 text-indigo-300" />
                </div>
              ))}
            </div>

            <div className="mt-4 rounded-[22px] bg-white/75 p-5 shadow-sm">
              <div className="flex items-start justify-between gap-4">
                <div className="flex gap-4">
                  <div className="flex h-20 w-20 items-center justify-center rounded-[18px] bg-indigo-100 text-[34px]">
                    🦙
                  </div>
                  <div>
                    <div className="text-[18px] font-semibold text-slate-800">Ollama</div>
                    <div className="mt-2 max-w-[250px] text-[16px] leading-7 text-slate-500">
                      Sprawdź status Ollamy i skonfiguruj środowisko sztucznej inteligencji
                    </div>
                  </div>
                </div>
                <ChevronRight className="h-7 w-7 shrink-0 text-indigo-300" />
              </div>
            </div>
          </div>

          <div>
            <h3 className="mb-3 text-[20px] font-semibold text-slate-800">Pozwolenia</h3>

            <div className="rounded-[22px] bg-white/75 p-3 shadow-sm">
              <ToggleRow icon={<Bell className="h-7 w-7 text-indigo-300" />} title="Powiadomienia" />
              <div className="border-b border-slate-200" />
              <ToggleRow icon={<Mic className="h-7 w-7 text-indigo-300" />} title="Dostęp do mikrofonu" />
              <div className="border-b border-slate-200" />
              <ToggleRow icon={<MapPin className="h-7 w-7 text-indigo-300" />} title="Dostęp do lokalizacji" />
            </div>
          </div>

          <div className="h-12 rounded-[22px] bg-white/40" />
        </div>
      </div>
    </div>
  );
}

export default function App() {
  const [activeTab, setActiveTab] = useState<TabId>('home');

  let screen: React.ReactNode;

  switch (activeTab) {
    case 'chat':
      screen = <ChatScreen />;
      break;
    case 'plan':
      screen = <PlanScreen />;
      break;
    case 'calendar':
      screen = <CalendarScreen />;
      break;
    case 'projects':
      screen = <ProjectsScreen />;
      break;
    case 'settings':
      screen = <SettingsScreen />;
      break;
    case 'home':
    default:
      screen = <HomeScreen setActiveTab={setActiveTab} />;
      break;
  }

  return (
    <PhoneShell activeTab={activeTab} setActiveTab={setActiveTab}>
      {screen}
    </PhoneShell>
  );
}
