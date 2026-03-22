import React, { useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import AsyncStorage from "@react-native-async-storage/async-storage";

type TabKey = "home" | "chat" | "plan" | "calendar" | "inbox" | "settings";

const STORAGE_OLLAMA_URL = "jarvis_ollama_url_v972";
const DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434";

type ChatMessage = {
  role: "assistant" | "user";
  text: string;
};

type CalendarTask = {
  id: string;
  title: string;
  date: string;
  time?: string;
  type?: "task" | "shopping";
};

const WEEKDAYS = ["Pn", "Wt", "Śr", "Cz", "Pt", "Sb", "Nd"];
const MONTHS_PL = [
  "Styczeń", "Luty", "Marzec", "Kwiecień", "Maj", "Czerwiec",
  "Lipiec", "Sierpień", "Wrzesień", "Październik", "Listopad", "Grudzień",
];

function cleanUrl(url: string) {
  return url.trim().replace(/\/+$/, "");
}

function pad2(value: number) {
  return String(value).padStart(2, "0");
}

function toDateKey(date: Date) {
  return `${date.getFullYear()}-${pad2(date.getMonth() + 1)}-${pad2(date.getDate())}`;
}

function formatDateLabel(dateKey: string) {
  const [year, month, day] = dateKey.split("-").map(Number);
  return `${day} ${MONTHS_PL[month - 1]} ${year}`;
}

function getMonthGrid(year: number, monthIndex: number) {
  const firstDay = new Date(year, monthIndex, 1);
  const jsWeekday = firstDay.getDay();
  const mondayFirstOffset = (jsWeekday + 6) % 7;
  const daysInMonth = new Date(year, monthIndex + 1, 0).getDate();

  const cells: Array<{ day: number | null; key: string }> = [];
  for (let i = 0; i < mondayFirstOffset; i += 1) cells.push({ day: null, key: `empty-start-${i}` });
  for (let day = 1; day <= daysInMonth; day += 1) cells.push({ day, key: `day-${day}` });
  while (cells.length % 7 !== 0) cells.push({ day: null, key: `empty-end-${cells.length}` });
  return cells;
}

function chunkWeeks<T>(arr: T[], size: number) {
  const out: T[][] = [];
  for (let i = 0; i < arr.length; i += size) out.push(arr.slice(i, i + size));
  return out;
}

export default function App() {
  const [tab, setTab] = useState<TabKey>("home");
  const [chatInput, setChatInput] = useState("");
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([
    { role: "assistant", text: "Cześć. Tu Jarvis. Chat jest głównym centrum komunikacji, a Voice został zachowany." },
    { role: "assistant", text: "Możesz dodać zadanie, zakupy albo zapytać o plan dnia." },
  ]);

  const today = useMemo(() => new Date(), []);
  const [monthDate, setMonthDate] = useState(new Date(today.getFullYear(), today.getMonth(), 1));
  const [selectedDate, setSelectedDate] = useState(toDateKey(today));

  const [calendarTasks] = useState<CalendarTask[]>([
    { id: "1", title: "Sprawdzić plan dnia", date: toDateKey(today), time: "09:00", type: "task" },
    { id: "2", title: "Siłownia", date: toDateKey(new Date(today.getFullYear(), today.getMonth(), today.getDate() + 1)), time: "18:00", type: "task" },
    { id: "3", title: "Zakupy", date: toDateKey(new Date(today.getFullYear(), today.getMonth(), today.getDate() + 1)), time: "19:00", type: "shopping" },
    { id: "4", title: "Dentysta", date: toDateKey(new Date(today.getFullYear(), today.getMonth(), today.getDate() + 3)), time: "10:30", type: "task" },
  ]);

  const [shoppingItems] = useState<string[]>(["kupić pastę do zębów", "ogarnąć dziekanat"]);
  const [unscheduledItems] = useState<string[]>(["muszę ogarnąć przegląd auta", "muszę ogarnąć auto"]);

  const [ollamaUrl, setOllamaUrl] = useState(DEFAULT_OLLAMA_URL);
  const [ollamaStatus, setOllamaStatus] = useState("Nie sprawdzono połączenia.");
  const [testingOllama, setTestingOllama] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const saved = await AsyncStorage.getItem(STORAGE_OLLAMA_URL);
        if (saved?.trim()) setOllamaUrl(saved.trim());
      } catch {}
    })();
  }, []);

  async function saveOllamaUrl(nextUrl?: string) {
    const value = cleanUrl(nextUrl ?? ollamaUrl);
    setOllamaUrl(value);
    try {
      await AsyncStorage.setItem(STORAGE_OLLAMA_URL, value);
    } catch {}
  }

  async function testOllamaConnection() {
    const url = cleanUrl(ollamaUrl);
    if (!url) {
      setOllamaStatus("Podaj adres Ollamy.");
      return;
    }
    setTestingOllama(true);
    setOllamaStatus("Sprawdzam połączenie...");
    try {
      await saveOllamaUrl(url);
      const response = await fetch(`${url}/api/tags`, { method: "GET", headers: { Accept: "application/json" } });
      if (!response.ok) {
        setOllamaStatus(`Błąd połączenia: HTTP ${response.status}`);
        return;
      }
      const data = await response.json();
      const models = Array.isArray(data?.models) ? data.models : [];
      const first = models[0]?.name || models[0]?.model || null;
      setOllamaStatus(first ? `Połączenie OK. Wykryty model: ${first}` : "Połączenie OK. Ollama odpowiada.");
    } catch (e: any) {
      setOllamaStatus(`Brak połączenia: ${e?.message || "nieznany błąd"}`);
    } finally {
      setTestingOllama(false);
    }
  }

  function sendChat() {
    const text = chatInput.trim();
    if (!text) return;
    setChatMessages((prev) => [
      ...prev,
      { role: "user", text },
      { role: "assistant", text: "Wiadomość zapisana. Widok Chatu został uproszczony i ma bardziej komunikatorowy układ." },
    ]);
    setChatInput("");
  }

  function onVoicePress() {
    setChatMessages((prev) => [...prev, { role: "assistant", text: "🎤 Voice aktywny." }]);
  }

  const tasksByDate = useMemo(() => {
    const map: Record<string, CalendarTask[]> = {};
    for (const task of calendarTasks) {
      if (!map[task.date]) map[task.date] = [];
      map[task.date].push(task);
    }
    Object.keys(map).forEach((key) => map[key].sort((a, b) => (a.time || "").localeCompare(b.time || "")));
    return map;
  }, [calendarTasks]);

  const monthGrid = useMemo(() => getMonthGrid(monthDate.getFullYear(), monthDate.getMonth()), [monthDate]);
  const weeks = useMemo(() => chunkWeeks(monthGrid, 7), [monthGrid]);
  const selectedTasks = tasksByDate[selectedDate] || [];

  function goMonth(delta: number) {
    setMonthDate(new Date(monthDate.getFullYear(), monthDate.getMonth() + delta, 1));
  }

  function renderDayMeta(dateKey: string) {
    const tasks = tasksByDate[dateKey] || [];
    if (tasks.length === 0) return <View style={styles.metaSpacer} />;
    const shoppingCount = tasks.filter((t) => t.type === "shopping").length;
    const taskCount = tasks.length - shoppingCount;
    return (
      <View style={styles.metaRow}>
        {taskCount > 0 && <View style={styles.metaDotTask} />}
        {shoppingCount > 0 && <View style={styles.metaDotShopping} />}
      </View>
    );
  }

  const homeShortcuts = [
    { key: "chat", label: "Otwórz Chat", desc: "Rozmowa i voice" },
    { key: "plan", label: "Plan dnia", desc: "Najbliższe zadania" },
    { key: "calendar", label: "Kalendarz", desc: "Daty i terminy" },
    { key: "inbox", label: "Inbox", desc: "Rzeczy bez terminu" },
  ] as const;

  return (
    <SafeAreaView style={styles.safe}>
      <View style={styles.topBar}>
        <TouchableOpacity style={styles.topBack}>
          <Text style={styles.topBackText}>←</Text>
        </TouchableOpacity>

        <View style={styles.topTitleWrap}>
          <Text style={styles.appTitle}>Jarvis Mobile v9.7.2</Text>
          <Text style={styles.subtitle}>Home z podsumowaniem + Chat jak komunikator</Text>
        </View>

        <TouchableOpacity style={styles.topMenu}>
          <Text style={styles.topMenuText}>⋮</Text>
        </TouchableOpacity>
      </View>

      <ScrollView contentContainerStyle={styles.content}>
        {tab === "home" && (
          <View style={styles.screenCard}>
            <Text style={styles.sectionTitle}>Home</Text>
            <Text style={styles.helpText}>Szybki przegląd aplikacji i prosty start bez szukania funkcji po zakładkach.</Text>

            <View style={styles.homeSummary}>
              <View style={styles.metricCard}>
                <Text style={styles.metricValue}>{calendarTasks.length}</Text>
                <Text style={styles.metricLabel}>zadań</Text>
              </View>
              <View style={styles.metricCard}>
                <Text style={styles.metricValue}>{shoppingItems.length}</Text>
                <Text style={styles.metricLabel}>zakupy</Text>
              </View>
              <View style={styles.metricCard}>
                <Text style={styles.metricValue}>{unscheduledItems.length}</Text>
                <Text style={styles.metricLabel}>inbox</Text>
              </View>
            </View>

            <View style={styles.homePanel}>
              <Text style={styles.homePanelTitle}>Dzisiaj</Text>
              <Text style={styles.homePanelText}>Najbliższe zadanie: 09:00 — Sprawdzić plan dnia</Text>
              <Text style={styles.homePanelText}>Najwygodniej pracować przez Chat i Voice.</Text>
            </View>

            <View style={styles.homeShortcuts}>
              {homeShortcuts.map((item) => (
                <TouchableOpacity key={item.key} style={styles.shortcutCard} onPress={() => setTab(item.key as TabKey)}>
                  <Text style={styles.shortcutTitle}>{item.label}</Text>
                  <Text style={styles.shortcutText}>{item.desc}</Text>
                </TouchableOpacity>
              ))}
            </View>
          </View>
        )}

        {tab === "chat" && (
          <View style={styles.chatScreen}>
            <TouchableOpacity style={styles.chatModeBar} activeOpacity={0.9}>
              <View>
                <Text style={styles.chatModeTitle}>Chat</Text>
                <Text style={styles.chatModeMeta}>v9.7.2 • GPT / Ollama • kliknij, by zmienić tryb</Text>
              </View>
              <Text style={styles.chatModeArrow}>⌄</Text>
            </TouchableOpacity>

            <ScrollView style={styles.chatStream} contentContainerStyle={styles.chatStreamContent}>
              {chatMessages.map((msg, idx) => (
                <View key={idx} style={[styles.messageRow, msg.role === "user" ? styles.messageRowUser : styles.messageRowAssistant]}>
                  <View style={[styles.bubble, msg.role === "user" ? styles.userBubble : styles.assistantBubble]}>
                    <Text style={styles.bubbleText}>{msg.text}</Text>
                  </View>
                </View>
              ))}
            </ScrollView>

            <View style={styles.chatComposer}>
              <TextInput
                style={styles.chatInput}
                placeholder="Napisz do Jarvisa..."
                placeholderTextColor="#94a3b8"
                value={chatInput}
                onChangeText={setChatInput}
                multiline
              />
              <View style={styles.composerActions}>
                <TouchableOpacity style={styles.plusButton}>
                  <Text style={styles.plusButtonText}>＋</Text>
                </TouchableOpacity>
                <TouchableOpacity style={styles.sendTextButton} onPress={sendChat}>
                  <Text style={styles.sendTextButtonText}>Wyślij</Text>
                </TouchableOpacity>
                <TouchableOpacity style={styles.voiceCircle} onPress={onVoicePress}>
                  <Text style={styles.voiceCircleText}>🎤</Text>
                </TouchableOpacity>
              </View>
            </View>
          </View>
        )}

        {tab === "plan" && (
          <View style={styles.screenCard}>
            <Text style={styles.sectionTitle}>Plan</Text>
            {calendarTasks.map((item) => (
              <View key={item.id} style={styles.listItem}>
                <Text style={styles.listText}>{item.date} {item.time ? `${item.time} — ` : ""}{item.title}</Text>
              </View>
            ))}
          </View>
        )}

        {tab === "calendar" && (
          <View style={styles.calendarScreen}>
            <Text style={styles.calendarTopTitle}>Kalendarz</Text>

            <View style={styles.monthHeader}>
              <TouchableOpacity style={styles.monthArrowButton} onPress={() => goMonth(-1)}>
                <Text style={styles.monthArrowText}>‹</Text>
              </TouchableOpacity>
              <Text style={styles.monthTitle}>{MONTHS_PL[monthDate.getMonth()]} {monthDate.getFullYear()}</Text>
              <TouchableOpacity style={styles.monthArrowButton} onPress={() => goMonth(1)}>
                <Text style={styles.monthArrowText}>›</Text>
              </TouchableOpacity>
            </View>

            <View style={styles.weekdaysRow}>
              {WEEKDAYS.map((label) => <Text key={label} style={styles.weekdayText}>{label}</Text>)}
            </View>

            <View style={styles.calendarGrid}>
              {weeks.map((week, index) => (
                <View key={`week-${index}`} style={styles.weekRow}>
                  {week.map((cell) => {
                    if (!cell.day) return <View key={cell.key} style={[styles.dayCard, styles.dayCardEmpty]} />;
                    const dateKey = `${monthDate.getFullYear()}-${String(monthDate.getMonth() + 1).padStart(2, "0")}-${String(cell.day).padStart(2, "0")}`;
                    const isSelected = selectedDate === dateKey;
                    const isToday = toDateKey(today) === dateKey;
                    return (
                      <TouchableOpacity key={cell.key} style={[styles.dayCard, isSelected && styles.dayCardSelected, isToday && styles.dayCardToday]} onPress={() => setSelectedDate(dateKey)}>
                        <Text style={[styles.dayCardText, isSelected && styles.dayCardTextSelected]}>{cell.day}</Text>
                        {renderDayMeta(dateKey)}
                      </TouchableOpacity>
                    );
                  })}
                </View>
              ))}
            </View>

            <View style={styles.dayPanel}>
              <Text style={styles.dayPanelTitle}>{formatDateLabel(selectedDate)}</Text>
              {selectedTasks.length === 0 ? (
                <Text style={styles.dayPanelEmpty}>Brak zadań na ten dzień.</Text>
              ) : (
                <View style={styles.dayTaskList}>
                  {selectedTasks.map((task) => (
                    <View key={task.id} style={styles.dayTaskRow}>
                      <View style={task.type === "shopping" ? styles.dayTaskMarkerShopping : styles.dayTaskMarkerTask} />
                      <Text style={styles.dayTaskText}>{task.time ? `${task.time} — ` : ""}{task.title}</Text>
                    </View>
                  ))}
                </View>
              )}
            </View>
          </View>
        )}

        {tab === "inbox" && (
          <View style={styles.screenCard}>
            <Text style={styles.sectionTitle}>Inbox</Text>

            <View style={styles.inboxCard}>
              <Text style={styles.statusTitle}>Lista zakupów</Text>
              {shoppingItems.map((item, index) => (
                <View key={index} style={styles.inboxRow}>
                  <Text style={styles.inboxText}>• {item}</Text>
                  <TouchableOpacity style={styles.inlineDelete}>
                    <Text style={styles.inlineDeleteText}>×</Text>
                  </TouchableOpacity>
                </View>
              ))}
            </View>

            <View style={styles.inboxCard}>
              <Text style={styles.statusTitle}>Do zaplanowania</Text>
              {unscheduledItems.map((item, index) => (
                <View key={index} style={styles.inboxRow}>
                  <Text style={styles.inboxText}>• {item}</Text>
                  <TouchableOpacity style={styles.inlineDelete}>
                    <Text style={styles.inlineDeleteText}>×</Text>
                  </TouchableOpacity>
                </View>
              ))}
            </View>
          </View>
        )}

        {tab === "settings" && (
          <View style={styles.screenCard}>
            <Text style={styles.sectionTitle}>Ustawienia</Text>
            <Text style={styles.label}>Adres Ollamy</Text>
            <TextInput
              style={styles.settingsInput}
              placeholder="http://127.0.0.1:11434"
              placeholderTextColor="#94a3b8"
              value={ollamaUrl}
              onChangeText={setOllamaUrl}
              autoCapitalize="none"
              autoCorrect={false}
            />

            <View style={styles.settingsButtons}>
              <TouchableOpacity style={styles.secondaryButton} onPress={() => saveOllamaUrl()}>
                <Text style={styles.secondaryButtonText}>Zapisz adres</Text>
              </TouchableOpacity>

              <TouchableOpacity style={styles.primaryButton} onPress={testOllamaConnection} disabled={testingOllama}>
                {testingOllama ? <ActivityIndicator color="#ffffff" /> : <Text style={styles.primaryButtonText}>Sprawdź połączenie</Text>}
              </TouchableOpacity>
            </View>

            <View style={styles.statusBox}>
              <Text style={styles.statusTitle}>Status Ollamy</Text>
              <Text style={styles.statusText}>{ollamaStatus}</Text>
            </View>

            <TouchableOpacity style={styles.ghostButton} onPress={() => Alert.alert("Podpowiedź", "Dla telefonu najczęściej trzeba wpisać adres IP komputera w sieci lokalnej, np. http://192.168.x.x:11434.")}>
              <Text style={styles.ghostButtonText}>Jakiego adresu użyć?</Text>
            </TouchableOpacity>
          </View>
        )}
      </ScrollView>

      <View style={styles.tabbar}>
        {[
          ["home", "Home"],
          ["chat", "Chat"],
          ["plan", "Plan"],
          ["calendar", "Kal."],
          ["inbox", "Inbox"],
          ["settings", "Ustaw."],
        ].map(([key, label]) => {
          const active = tab === key;
          return (
            <TouchableOpacity key={key} style={[styles.tabButton, active && styles.tabButtonActive]} onPress={() => setTab(key as TabKey)}>
              <Text style={[styles.tabText, active && styles.tabTextActive]}>{label}</Text>
            </TouchableOpacity>
          );
        })}
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: "#03172f" },

  topBar: {
    paddingTop: 14,
    paddingBottom: 14,
    paddingHorizontal: 16,
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
    borderBottomWidth: 1,
    borderBottomColor: "#17335d",
    backgroundColor: "#03172f",
  },
  topBack: {
    width: 42,
    height: 42,
    borderRadius: 21,
    alignItems: "center",
    justifyContent: "center",
  },
  topBackText: { color: "#ffffff", fontSize: 24, fontWeight: "700" },
  topTitleWrap: { flex: 1 },
  appTitle: { color: "#ffffff", fontSize: 24, fontWeight: "800" },
  subtitle: { color: "#8ea3c7", fontSize: 14, marginTop: 4 },
  topMenu: {
    width: 42,
    height: 42,
    borderRadius: 21,
    alignItems: "center",
    justifyContent: "center",
  },
  topMenuText: { color: "#ffffff", fontSize: 24, fontWeight: "700" },

  content: { padding: 16, paddingBottom: 120 },

  screenCard: {
    backgroundColor: "#14284c",
    borderWidth: 1,
    borderColor: "#27446f",
    borderRadius: 24,
    padding: 20,
    gap: 14,
  },

  sectionTitle: { color: "#ffffff", fontSize: 18, fontWeight: "800" },
  helpText: { color: "#b7c4df", fontSize: 16, lineHeight: 24 },

  homeSummary: { flexDirection: "row", gap: 10 },
  metricCard: {
    flex: 1,
    backgroundColor: "#0f2342",
    borderWidth: 1,
    borderColor: "#27446f",
    borderRadius: 18,
    paddingVertical: 16,
    alignItems: "center",
  },
  metricValue: { color: "#ffffff", fontSize: 24, fontWeight: "800" },
  metricLabel: { color: "#8ea3c7", fontSize: 13, marginTop: 4 },
  homePanel: {
    backgroundColor: "#1b3158",
    borderWidth: 1,
    borderColor: "#345588",
    borderRadius: 18,
    padding: 16,
    gap: 8,
  },
  homePanelTitle: { color: "#ffffff", fontSize: 16, fontWeight: "800" },
  homePanelText: { color: "#b7c4df", fontSize: 15, lineHeight: 22 },
  homeShortcuts: { gap: 10 },
  shortcutCard: {
    backgroundColor: "#0f2342",
    borderWidth: 1,
    borderColor: "#27446f",
    borderRadius: 18,
    padding: 16,
  },
  shortcutTitle: { color: "#ffffff", fontSize: 16, fontWeight: "800", marginBottom: 4 },
  shortcutText: { color: "#8ea3c7", fontSize: 14 },

  chatScreen: {
    gap: 12,
  },
  chatModeBar: {
    paddingHorizontal: 4,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  chatModeTitle: { color: "#ffffff", fontSize: 18, fontWeight: "800" },
  chatModeMeta: { color: "#8ea3c7", fontSize: 13, marginTop: 2 },
  chatModeArrow: { color: "#8ea3c7", fontSize: 20, fontWeight: "700" },

  chatStream: {
    minHeight: 520,
    maxHeight: 620,
  },
  chatStreamContent: {
    paddingTop: 6,
    paddingBottom: 12,
    gap: 14,
  },
  messageRow: { width: "100%" },
  messageRowUser: { alignItems: "flex-end" },
  messageRowAssistant: { alignItems: "flex-start" },
  bubble: {
    maxWidth: "92%",
    paddingHorizontal: 16,
    paddingVertical: 14,
    borderRadius: 24,
  },
  userBubble: { backgroundColor: "#3c6df0" },
  assistantBubble: { backgroundColor: "#314972" },
  bubbleText: { color: "#ffffff", fontSize: 17, lineHeight: 27 },

  chatComposer: {
    backgroundColor: "#0f2342",
    borderWidth: 1,
    borderColor: "#27446f",
    borderRadius: 28,
    paddingHorizontal: 14,
    paddingTop: 12,
    paddingBottom: 12,
    gap: 12,
  },
  chatInput: {
    minHeight: 72,
    maxHeight: 140,
    color: "#ffffff",
    fontSize: 18,
    textAlignVertical: "top",
    paddingHorizontal: 4,
    paddingVertical: 0,
  },
  composerActions: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
  },
  plusButton: {
    width: 42,
    height: 42,
    borderRadius: 21,
    borderWidth: 1,
    borderColor: "#345588",
    alignItems: "center",
    justifyContent: "center",
  },
  plusButtonText: { color: "#ffffff", fontSize: 24, fontWeight: "500" },
  sendTextButton: {
    flex: 1,
    minHeight: 46,
    borderRadius: 23,
    backgroundColor: "#17335d",
    alignItems: "center",
    justifyContent: "center",
  },
  sendTextButtonText: { color: "#ffffff", fontSize: 16, fontWeight: "700" },
  voiceCircle: {
    width: 52,
    height: 52,
    borderRadius: 26,
    backgroundColor: "#050b16",
    alignItems: "center",
    justifyContent: "center",
  },
  voiceCircleText: { color: "#ffffff", fontSize: 22 },

  listItem: {
    backgroundColor: "#1b3158",
    borderWidth: 1,
    borderColor: "#345588",
    borderRadius: 18,
    padding: 16,
  },
  listText: { color: "#ffffff", fontSize: 16, lineHeight: 22 },

  calendarScreen: {
    backgroundColor: "#14284c",
    borderWidth: 1,
    borderColor: "#27446f",
    borderRadius: 24,
    padding: 20,
    gap: 12,
  },
  calendarTopTitle: { color: "#ffffff", fontSize: 18, fontWeight: "800", marginBottom: 4 },
  monthHeader: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: 2,
  },
  monthArrowButton: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: "#1b3158",
    borderWidth: 1,
    borderColor: "#2c4a76",
    alignItems: "center",
    justifyContent: "center",
  },
  monthArrowText: { color: "#ffffff", fontSize: 22, fontWeight: "800", lineHeight: 24 },
  monthTitle: { color: "#ffffff", fontSize: 20, fontWeight: "800" },
  weekdaysRow: { flexDirection: "row", justifyContent: "space-between", marginTop: 6, marginBottom: 2 },
  weekdayText: { flex: 1, textAlign: "center", color: "#8ea3c7", fontSize: 12, fontWeight: "700" },
  calendarGrid: { gap: 8 },
  weekRow: { flexDirection: "row", gap: 8 },
  dayCard: {
    flex: 1,
    aspectRatio: 1,
    borderRadius: 12,
    backgroundColor: "#1b3158",
    borderWidth: 1,
    borderColor: "#223c66",
    alignItems: "center",
    justifyContent: "space-between",
    paddingTop: 10,
    paddingBottom: 8,
    overflow: "hidden",
  },
  dayCardEmpty: { backgroundColor: "transparent", borderWidth: 0 },
  dayCardSelected: { backgroundColor: "#3c6df0", borderColor: "#3c6df0" },
  dayCardToday: { borderColor: "#7db1ff" },
  dayCardText: { color: "#ffffff", fontSize: 13, fontWeight: "800" },
  dayCardTextSelected: { color: "#ffffff" },
  metaRow: { minHeight: 8, flexDirection: "row", gap: 4, alignItems: "center", justifyContent: "center" },
  metaSpacer: { minHeight: 8 },
  metaDotTask: { width: 7, height: 7, borderRadius: 3.5, backgroundColor: "#22c55e" },
  metaDotShopping: { width: 7, height: 7, borderRadius: 3.5, backgroundColor: "#facc15" },
  dayPanel: {
    backgroundColor: "#1b3158",
    borderRadius: 14,
    padding: 14,
    borderWidth: 1,
    borderColor: "#2f507f",
    marginTop: 10,
  },
  dayPanelTitle: { color: "#ffffff", fontSize: 18, fontWeight: "800", marginBottom: 10 },
  dayPanelEmpty: { color: "#b7c4df", fontSize: 15 },
  dayTaskList: { gap: 8 },
  dayTaskRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    backgroundColor: "#14284c",
    borderRadius: 12,
    paddingHorizontal: 12,
    paddingVertical: 10,
  },
  dayTaskMarkerTask: { width: 8, height: 8, borderRadius: 4, backgroundColor: "#22c55e" },
  dayTaskMarkerShopping: { width: 8, height: 8, borderRadius: 4, backgroundColor: "#facc15" },
  dayTaskText: { color: "#ffffff", fontSize: 15, flex: 1 },

  inboxCard: {
    backgroundColor: "#0f2342",
    borderWidth: 1,
    borderColor: "#27446f",
    borderRadius: 22,
    padding: 18,
    gap: 14,
  },
  inboxRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
  },
  inboxText: {
    flex: 1,
    color: "#ffffff",
    fontSize: 16,
    lineHeight: 24,
  },
  inlineDelete: {
    width: 28,
    height: 28,
    borderRadius: 14,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#31151a",
  },
  inlineDeleteText: { color: "#ef4444", fontSize: 18, fontWeight: "800", lineHeight: 20 },

  label: { color: "#ffffff", fontSize: 16, fontWeight: "700" },
  settingsInput: {
    minHeight: 88,
    borderRadius: 22,
    backgroundColor: "#1b3158",
    color: "#ffffff",
    paddingHorizontal: 18,
    paddingVertical: 16,
    textAlignVertical: "top",
    fontSize: 18,
  },
  settingsButtons: { flexDirection: "row", gap: 14 },
  primaryButton: {
    flex: 1,
    backgroundColor: "#3c6df0",
    borderRadius: 22,
    alignItems: "center",
    justifyContent: "center",
    minHeight: 56,
    paddingHorizontal: 16,
  },
  secondaryButton: {
    flex: 1,
    backgroundColor: "#17335d",
    borderRadius: 22,
    borderWidth: 1,
    borderColor: "#345588",
    alignItems: "center",
    justifyContent: "center",
    minHeight: 56,
    paddingHorizontal: 16,
  },
  primaryButtonText: { color: "#ffffff", fontWeight: "800", fontSize: 16, textAlign: "center" },
  secondaryButtonText: { color: "#ffffff", fontWeight: "800", fontSize: 16, textAlign: "center" },
  ghostButton: {
    borderRadius: 18,
    borderWidth: 1,
    borderColor: "#345588",
    paddingHorizontal: 14,
    paddingVertical: 12,
    alignSelf: "flex-start",
  },
  ghostButtonText: { color: "#b7c4df", fontWeight: "700", fontSize: 14 },
  statusBox: {
    backgroundColor: "#1b3158",
    borderRadius: 18,
    padding: 16,
    borderWidth: 1,
    borderColor: "#345588",
  },
  statusTitle: { color: "#ffffff", fontWeight: "800", fontSize: 16, marginBottom: 6 },
  statusText: { color: "#b7c4df", fontSize: 15, lineHeight: 22 },

  tabbar: {
    flexDirection: "row",
    gap: 8,
    paddingHorizontal: 12,
    paddingVertical: 14,
    borderTopWidth: 1,
    borderTopColor: "#17335d",
    backgroundColor: "#03172f",
  },
  tabButton: {
    flex: 1,
    minHeight: 62,
    borderRadius: 18,
    borderWidth: 1,
    borderColor: "#27446f",
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: "#0b2243",
    paddingHorizontal: 4,
  },
  tabButtonActive: { backgroundColor: "#3c6df0", borderColor: "#3c6df0" },
  tabText: { color: "#ffffff", fontSize: 13, fontWeight: "800", textAlign: "center" },
  tabTextActive: { color: "#ffffff" },
});
