import React, { useEffect, useMemo, useRef, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  KeyboardAvoidingView,
  Platform,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Switch,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import AsyncStorage from "@react-native-async-storage/async-storage";

const Notifications: any = (() => {
  try { return require("expo-notifications"); } catch { return null; }
})();

const SpeechLib: any = (() => {
  try { return require("expo-speech-recognition"); } catch { return null; }
})();

const SpeechModule: any = SpeechLib?.ExpoSpeechRecognitionModule || SpeechLib?.default || SpeechLib || null;

type TabKey = "chat" | "plan" | "inbox" | "brain" | "settings" | "home";
type VoiceTarget = "chat" | "inbox";
type ChatMessage = { role: "assistant" | "user"; text: string; meta?: string; error?: boolean };
type TimelineItem = {
  id: string;
  kind: string;
  title: string;
  start: string;
  end: string;
  category?: string | null;
  task_id?: number | null;
  deletable?: boolean;
  checklist_count?: number;
};
type InboxItem = { id: number; text: string; kind: string };
type ShoppingReview = { eventText: string; items: Array<InboxItem & { checked: boolean }> };
type PendingShoppingDraft = { eventText: string; selectedItemIds: number[]; selectedLabels: string[] };
type ChecklistItem = { index: number; text: string; done: boolean };
type TaskDetail = { task_id: number; title: string; due_at: string; category: string; checklist: ChecklistItem[] };

const STORAGE_BACKEND_URL = "jarvis_backend_url_v92";
const STORAGE_NOTIFY = "jarvis_notify_enabled_v92";
const STORAGE_VOICE_AUTOSEND = "jarvis_voice_autosend_v92";
const DEFAULT_BACKEND_URL = "http://192.168.8.118:8011";

if (Notifications?.setNotificationHandler) {
  Notifications.setNotificationHandler({
    handleNotification: async () => ({ shouldShowAlert: true, shouldPlaySound: false, shouldSetBadge: false }),
  });
}

function cleanUrl(url: string) { return url.trim().replace(/\/+$/, ""); }
function tryJson(text: string) { try { return JSON.parse(text); } catch { return text; } }
function extractText(payload: any): string {
  if (!payload) return "Brak odpowiedzi.";
  const values = [payload.message, payload.reply, payload.response, payload.answer, payload.content, payload.text];
  for (const v of values) if (typeof v === "string" && v.trim()) return v.trim();
  return typeof payload === "string" ? payload : "Odpowiedź w nieoczekiwanym formacie.";
}
function prettyTime(value: any) {
  if (!value) return "—";
  if (typeof value !== "string") return String(value);
  const m = value.match(/(\d{2}:\d{2})/);
  return m ? m[1] : value;
}
function parseTranscriptFromEvent(event: any): string {
  if (!event) return "";
  if (typeof event?.transcript === "string") return event.transcript;
  if (typeof event?.result === "string") return event.result;
  if (typeof event?.value === "string") return event.value;
  const first = event?.results?.[0];
  if (typeof first?.transcript === "string") return first.transcript;
  if (typeof first === "string") return first;
  return "";
}
function summarizeDay(items: TimelineItem[], label: string): string {
  if (!items?.length) return `${label}: brak pozycji.`;
  return `${label}: ${items.length} pozycji. Najbliżej: ${prettyTime(items[0]?.start)} ${items[0]?.title}.`;
}
function extractAdditionalShoppingItems(text: string) {
  const raw = (text || "").trim();
  if (!raw) return [];
  const lower = raw.toLowerCase().trim();
  if (["nie", "nic", "nic więcej", "nic wiecej", "to wszystko", "gotowe", "ok", "okej"].includes(lower)) return [];
  let cleaned = raw
    .replace(/^(tak[,! ]*)?/i, "")
    .replace(/^(możesz|mozesz)\s+/i, "")
    .replace(/^(jeszcze\s+)?dodaj\s+/i, "")
    .replace(/^(dopis[zsz]\s+)?/i, "")
    .trim();
  return cleaned.split(/,|;|\s+i\s+/i).map((x) => x.trim()).filter(Boolean);
}
function isShoppingFinalizeMessage(text: string) {
  const lower = (text || "").trim().toLowerCase();
  if (!lower || lower.endsWith("?")) return false;
  if (extractAdditionalShoppingItems(text).length > 0) return true;
  return ["nie", "nic", "nic więcej", "nic wiecej", "to wszystko", "gotowe", "ok", "okej"].includes(lower);
}

export default function App() {
  const [tab, setTab] = useState<TabKey>("chat");
  const [backendUrl, setBackendUrl] = useState(DEFAULT_BACKEND_URL);
  const [backendDraft, setBackendDraft] = useState(DEFAULT_BACKEND_URL);
  const [chatInput, setChatInput] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([{ role: "assistant", text: "Jarvis v9.2 gotowy. Chat jest centrum sterowania, Inbox trzyma backlog, a zakupy można dopisywać zarówno do listy zakupów, jak i do konkretnego zadania zakupów.", meta: "chat-first • zakupy • czyszczenie planu" }]);
  const [inboxInput, setInboxInput] = useState("");
  const [inboxLoading, setInboxLoading] = useState(false);
  const [inboxStatus, setInboxStatus] = useState("");
  const [shoppingItems, setShoppingItems] = useState<InboxItem[]>([]);
  const [unscheduledItems, setUnscheduledItems] = useState<InboxItem[]>([]);
  const [todayItems, setTodayItems] = useState<TimelineItem[]>([]);
  const [tomorrowItems, setTomorrowItems] = useState<TimelineItem[]>([]);
  const [todayDate, setTodayDate] = useState("");
  const [tomorrowDate, setTomorrowDate] = useState("");
  const [planLoading, setPlanLoading] = useState(false);
  const [showTomorrow, setShowTomorrow] = useState(true);
  const [plannerText, setPlannerText] = useState("Planner jeszcze nie został uruchomiony.");
  const [healthStatus, setHealthStatus] = useState("Nie sprawdzano backendu.");
  const [ollamaStatus, setOllamaStatus] = useState("Nie sprawdzano Ollamy.");
  const [notifyEnabled, setNotifyEnabled] = useState(true);
  const [voiceAutoSend, setVoiceAutoSend] = useState(true);
  const [voiceListening, setVoiceListening] = useState(false);
  const [voiceTarget, setVoiceTarget] = useState<VoiceTarget>("chat");
  const [voiceStatus, setVoiceStatus] = useState("Voice gotowy.");
  const [shoppingReview, setShoppingReview] = useState<ShoppingReview | null>(null);
  const [pendingShoppingDraft, setPendingShoppingDraft] = useState<PendingShoppingDraft | null>(null);
  const [expandedTaskId, setExpandedTaskId] = useState<number | null>(null);
  const [expandedTask, setExpandedTask] = useState<TaskDetail | null>(null);
  const [taskDetailLoading, setTaskDetailLoading] = useState(false);
  const [taskChecklistInput, setTaskChecklistInput] = useState("");
  const transcriptRef = useRef("");
  const subscriptionsRef = useRef<any[]>([]);
  const scrollRef = useRef<ScrollView | null>(null);

  const speechAvailable = useMemo(() => !!SpeechModule, []);
  const currentItems = showTomorrow ? tomorrowItems : todayItems;
  const currentDate = showTomorrow ? tomorrowDate : todayDate;

  useEffect(() => {
    (async () => {
      try {
        const [savedUrl, savedNotify, savedAuto] = await Promise.all([
          AsyncStorage.getItem(STORAGE_BACKEND_URL),
          AsyncStorage.getItem(STORAGE_NOTIFY),
          AsyncStorage.getItem(STORAGE_VOICE_AUTOSEND),
        ]);
        if (savedUrl) { setBackendUrl(cleanUrl(savedUrl)); setBackendDraft(cleanUrl(savedUrl)); }
        if (savedNotify != null) setNotifyEnabled(savedNotify === "true");
        if (savedAuto != null) setVoiceAutoSend(savedAuto === "true");
      } catch {}
      await Promise.all([loadPlan(), loadInbox()]);
    })();
    return () => cleanupSpeechListeners();
  }, []);

  useEffect(() => {
    setTimeout(() => scrollRef.current?.scrollToEnd?.({ animated: true }), 50);
  }, [chatMessages, shoppingReview]);

  function cleanupSpeechListeners() {
    subscriptionsRef.current.forEach((sub) => { try { sub?.remove?.(); } catch {} });
    subscriptionsRef.current = [];
  }

  async function saveSettings(nextNotify = notifyEnabled, nextAuto = voiceAutoSend) {
    try {
      await Promise.all([
        AsyncStorage.setItem(STORAGE_NOTIFY, String(nextNotify)),
        AsyncStorage.setItem(STORAGE_VOICE_AUTOSEND, String(nextAuto)),
      ]);
    } catch {}
  }

  async function apiGet(path: string) {
    const response = await fetch(`${cleanUrl(backendUrl)}${path}`);
    const raw = await response.text();
    const parsed = tryJson(raw);
    if (!response.ok) throw new Error(typeof parsed === "string" ? parsed : `HTTP ${response.status}`);
    return parsed;
  }
  async function apiPost(path: string, body: any) {
    const response = await fetch(`${cleanUrl(backendUrl)}${path}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    const raw = await response.text();
    const parsed = tryJson(raw);
    if (!response.ok) throw new Error(typeof parsed === "string" ? parsed : `HTTP ${response.status}`);
    return parsed;
  }
  async function apiDelete(path: string) {
    const response = await fetch(`${cleanUrl(backendUrl)}${path}`, { method: "DELETE" });
    const raw = await response.text();
    const parsed = tryJson(raw);
    if (!response.ok) throw new Error(typeof parsed === "string" ? parsed : `HTTP ${response.status}`);
    return parsed;
  }

  async function saveBackend() {
    const normalized = cleanUrl(backendDraft);
    if (!normalized) return Alert.alert("Błąd", "Backend URL nie może być pusty.");
    setBackendUrl(normalized);
    try { await AsyncStorage.setItem(STORAGE_BACKEND_URL, normalized); } catch {}
    setHealthStatus("Backend zapisany.");
  }
  async function testBackend() {
    setHealthStatus("Sprawdzam...");
    try { const data = await apiGet("/mobile/health"); setHealthStatus(`OK: ${extractText(data)}`); }
    catch (e: any) { setHealthStatus(`Błąd backendu: ${e?.message || "nieznany błąd"}`); }
  }
  async function testOllama() {
    setOllamaStatus("Testuję...");
    try { const data = await apiPost("/mobile/ai/chat", { message: "Napisz dokładnie: TEST OLLAMA DZIALA" }); setOllamaStatus(`Odpowiedź AI: ${extractText(data)}`); }
    catch (e: any) { setOllamaStatus(`Błąd AI/Ollamy: ${e?.message || "nieznany błąd"}`); }
  }

  async function loadPlan() {
    setPlanLoading(true);
    try {
      const [today, tomorrow] = await Promise.all([apiGet("/mobile/today"), apiGet("/mobile/tomorrow")]);
      setTodayItems(Array.isArray(today?.timeline) ? today.timeline : []);
      setTomorrowItems(Array.isArray(tomorrow?.timeline) ? tomorrow.timeline : []);
      setTodayDate(today?.date || "");
      setTomorrowDate(tomorrow?.date || "");
    } catch {
      Alert.alert("Plan", "Nie udało się pobrać planu.");
    } finally { setPlanLoading(false); }
  }

  async function loadInbox() {
    try {
      const data = await apiGet("/mobile/inbox/list");
      setShoppingItems(Array.isArray(data?.shopping) ? data.shopping : []);
      setUnscheduledItems(Array.isArray(data?.unscheduled) ? data.unscheduled : []);
    } catch (e: any) {
      setInboxStatus(`Błąd Inboxa: ${e?.message || "nieznany błąd"}`);
    }
  }

  async function loadTaskDetail(taskId: number) {
    setTaskDetailLoading(true);
    try {
      const data = await apiGet(`/mobile/plan/task/${taskId}`);
      setExpandedTask(data?.task || null);
      setExpandedTaskId(taskId);
    } catch (e: any) {
      Alert.alert("Zadanie", e?.message || "Nie udało się pobrać szczegółów zadania.");
    } finally { setTaskDetailLoading(false); }
  }

  async function runPlanner() {
    const base = currentItems;
    if (!base.length) return setPlannerText("Brak pozycji do zaplanowania. Dodaj coś do Inboxa lub Planu.");
    const titles = base.slice(0, 8).map((x) => `${prettyTime(x.start)} — ${x.title}`);
    setPlannerText([`Top priorytet: ${base[0].title}`, "", ...titles].join("\n"));
  }

  function conversationTail() { return chatMessages.slice(-8).map((m) => ({ role: m.role, content: m.text })); }

  async function runChat(textOverride?: string) {
    const text = (textOverride ?? chatInput).trim();
    if (!text || chatLoading) return;
    setChatMessages((prev) => [...prev, { role: "user", text, meta: pendingShoppingDraft ? "shopping-extra" : "chat-first" }]);
    setChatInput("");
    setChatLoading(true);
    try {
      if (pendingShoppingDraft && isShoppingFinalizeMessage(text)) {
        const data = await apiPost("/mobile/shopping/confirm", { event_text: pendingShoppingDraft.eventText, selected_item_ids: pendingShoppingDraft.selectedItemIds, extra_items: extractAdditionalShoppingItems(text) });
        setChatMessages((prev) => [...prev, { role: "assistant", text: extractText(data), meta: "shopping-confirmed" }]);
        setPendingShoppingDraft(null);
        setShoppingReview(null);
        await Promise.all([loadPlan(), loadInbox()]);
      } else {
        setShoppingReview(null);
        setPendingShoppingDraft(null);
        const data = await apiPost("/mobile/chat", { message: text, conversation_tail: conversationTail() });
        const actions = Array.isArray(data?.actions) ? data.actions : [];
        const reviewAction = actions.find((a: any) => a?.type === "shopping_review");
        if (reviewAction) {
          setShoppingReview({
            eventText: String(reviewAction?.event_text || text),
            items: Array.isArray(reviewAction?.items) ? reviewAction.items.map((item: any) => ({ ...item, checked: true })) : [],
          });
        }
        setChatMessages((prev) => [...prev, { role: "assistant", text: extractText(data), meta: data?.intent || "jarvis" }]);
        if (data?.changed) {
          await Promise.all([loadPlan(), loadInbox()]);
          try { await Notifications?.scheduleNotificationAsync?.({ content: { title: "Jarvis", body: extractText(data) }, trigger: null }); } catch {}
        }
      }
    } catch (e: any) {
      setChatMessages((prev) => [...prev, { role: "assistant", text: `Błąd: ${e?.message || "nie udało się połączyć."}`, meta: "error", error: true }]);
    } finally { setChatLoading(false); }
  }

  async function addInbox(textOverride?: string) {
    const text = (textOverride ?? inboxInput).trim();
    if (!text || inboxLoading) return;
    setInboxLoading(true);
    setInboxStatus("Dodaję...");
    try {
      const data = await apiPost("/mobile/inbox", { text });
      setInboxInput("");
      setInboxStatus(extractText(data));
      await loadInbox();
    } catch (e: any) {
      setInboxStatus(`Błąd Inboxa: ${e?.message || "nieznany błąd"}`);
    } finally { setInboxLoading(false); }
  }

  async function submitShoppingReview() {
    if (!shoppingReview) return;
    const selectedItems = shoppingReview.items.filter((x) => x.checked);
    setShoppingReview(null);
    setPendingShoppingDraft({ eventText: shoppingReview.eventText, selectedItemIds: selectedItems.map((x) => x.id), selectedLabels: selectedItems.map((x) => x.text) });
    const preview = selectedItems.length ? `Mam już zaznaczone: ${selectedItems.map((x) => x.text).join(", ")}.` : "Na razie nie zaznaczyłaś żadnej pozycji z listy.";
    setChatMessages((prev) => [...prev, { role: "assistant", text: `${preview} Czy chcesz dodać coś jeszcze? Powiedz lub napisz np. „tak, dodaj mleko, chleb i pietruszkę” albo „gotowe”.`, meta: "shopping-extra-question" }]);
  }

  async function deleteInboxItem(itemId: number) {
    try {
      const data = await apiDelete(`/mobile/inbox/item/${itemId}`);
      setInboxStatus(extractText(data));
      await loadInbox();
    } catch (e: any) {
      Alert.alert("Inbox", e?.message || "Nie udało się usunąć pozycji.");
    }
  }

  async function deleteTask(taskId: number) {
    try {
      const data = await apiDelete(`/mobile/plan/task/${taskId}`);
      if (expandedTaskId === taskId) { setExpandedTaskId(null); setExpandedTask(null); }
      await loadPlan();
      Alert.alert("Plan", extractText(data));
    } catch (e: any) { Alert.alert("Błąd", e?.message || "Nie udało się usunąć zadania."); }
  }
  function confirmDeleteTask(taskId: number, title: string) {
    Alert.alert("Usuń zadanie", `Usunąć zadanie „${title}”?`, [
      { text: "Anuluj", style: "cancel" },
      { text: "Usuń", style: "destructive", onPress: () => deleteTask(taskId) },
    ]);
  }
  function confirmClearDay() {
    if (!currentDate) return;
    Alert.alert("Wyczyść dzień", "Czy na pewno chcesz usunąć wszystkie zadania z tego dnia?", [
      { text: "Anuluj", style: "cancel" },
      { text: "Usuń", style: "destructive", onPress: async () => {
        try { const data = await apiDelete(`/mobile/plan/day/${currentDate}`); await loadPlan(); Alert.alert("Plan", extractText(data)); }
        catch (e: any) { Alert.alert("Błąd", e?.message || "Nie udało się wyczyścić dnia."); }
      } },
    ]);
  }

  async function addTaskChecklistItem() {
    if (!expandedTaskId || !taskChecklistInput.trim()) return;
    try {
      const data = await apiPost(`/mobile/plan/task/${expandedTaskId}/checklist/add`, { text: taskChecklistInput.trim() });
      setTaskChecklistInput("");
      await Promise.all([loadTaskDetail(expandedTaskId), loadPlan()]);
      Alert.alert("Zakupy", extractText(data));
    } catch (e: any) { Alert.alert("Zakupy", e?.message || "Nie udało się dodać pozycji."); }
  }

  async function removeTaskChecklistItem(index: number) {
    if (!expandedTaskId) return;
    try {
      const data = await apiDelete(`/mobile/plan/task/${expandedTaskId}/checklist/item?index=${index}`);
      await Promise.all([loadTaskDetail(expandedTaskId), loadPlan()]);
      Alert.alert("Zakupy", extractText(data));
    } catch (e: any) { Alert.alert("Zakupy", e?.message || "Nie udało się usunąć pozycji."); }
  }

  function applyTranscript(text: string, target: VoiceTarget) {
    if (!text.trim()) return;
    if (target === "chat") {
      setChatInput(text.trim());
      if (voiceAutoSend) { setVoiceStatus("Przetwarzam..."); setTimeout(() => runChat(text.trim()), 100); }
      else setVoiceStatus("Gotowe.");
    } else {
      setInboxInput(text.trim());
      if (voiceAutoSend) { setVoiceStatus("Przetwarzam..."); setTimeout(() => addInbox(text.trim()), 100); }
      else setVoiceStatus("Gotowe.");
    }
  }

  async function startVoice(target: VoiceTarget) {
    if (!SpeechModule) return Alert.alert("Voice", "Brak expo-speech-recognition w tym buildzie. Uruchom development build po npx expo run:android.");
    setVoiceTarget(target);
    setVoiceStatus("Proszę o dostęp do mikrofonu...");
    transcriptRef.current = "";
    cleanupSpeechListeners();
    try {
      if (SpeechModule?.requestPermissionsAsync) {
        const perm = await SpeechModule.requestPermissionsAsync();
        const granted = perm === true || perm?.granted === true || perm?.status === "granted";
        if (!granted) return setVoiceStatus("Brak zgody na mikrofon.");
      }
      if (SpeechModule?.addListener) {
        subscriptionsRef.current.push(SpeechModule.addListener("result", (event: any) => {
          const transcript = parseTranscriptFromEvent(event);
          if (transcript) { transcriptRef.current = transcript; setVoiceStatus(`Słucham... ${transcript}`); }
        }));
        subscriptionsRef.current.push(SpeechModule.addListener("error", (event: any) => {
          setVoiceStatus(`Voice error: ${event?.message || event?.error || "Błąd voice."}`); setVoiceListening(false);
        }));
        subscriptionsRef.current.push(SpeechModule.addListener("end", () => {
          setVoiceListening(false);
          applyTranscript(transcriptRef.current, target);
        }));
      }
      setVoiceListening(true);
      setVoiceStatus("Słucham...");
      if (SpeechModule?.start) await SpeechModule.start({ lang: "pl-PL", interimResults: true, maxAlternatives: 1, continuous: false });
      else if (SpeechModule?.startAsync) await SpeechModule.startAsync({ lang: "pl-PL" });
    } catch (e: any) {
      setVoiceListening(false);
      setVoiceStatus(`Nie udało się uruchomić voice: ${e?.message || "nieznany błąd"}`);
    }
  }

  async function stopVoice() {
    try {
      if (SpeechModule?.stop) await SpeechModule.stop();
      else if (SpeechModule?.stopAsync) await SpeechModule.stopAsync();
    } catch {}
    setVoiceListening(false);
    applyTranscript(transcriptRef.current, voiceTarget);
  }

  const renderTaskRow = (item: TimelineItem, idx: number) => {
    const isExpanded = expandedTaskId === item.task_id;
    const isShopping = item.category === "zakupy" || item.title.toLowerCase().includes("zakupy");
    return (
      <View key={idx} style={styles.timelineCardWrap}>
        <TouchableOpacity
          activeOpacity={isShopping && item.task_id ? 0.7 : 1}
          onPress={() => {
            if (isShopping && item.task_id) {
              if (isExpanded) { setExpandedTaskId(null); setExpandedTask(null); }
              else loadTaskDetail(item.task_id);
            }
          }}
          style={styles.timelineRow}
        >
          <Text style={styles.timelineTime}>{prettyTime(item.start)}</Text>
          <View style={styles.timelineDot} />
          <View style={{ flex: 1 }}>
            <Text style={styles.timelineTitle}>{item.title}</Text>
            <Text style={styles.timelineMeta}>{item.category || item.kind}{item.checklist_count ? ` • lista ${item.checklist_count}` : ""}{isShopping ? " • kliknij, by rozwinąć" : ""}</Text>
          </View>
          {item.deletable && item.task_id ? (
            <TouchableOpacity style={styles.deletePill} onPress={() => confirmDeleteTask(item.task_id!, item.title)}>
              <Text style={styles.deletePillText}>X</Text>
            </TouchableOpacity>
          ) : null}
        </TouchableOpacity>
        {isExpanded && expandedTask ? (
          <View style={styles.innerPanel}>
            {taskDetailLoading ? <ActivityIndicator color="#A7C4FF" /> : null}
            {expandedTask.checklist.length ? expandedTask.checklist.map((row) => (
              <View key={row.index} style={styles.listRow}>
                <Text style={styles.listBullet}>•</Text>
                <Text style={styles.listText}>{row.text}</Text>
                <TouchableOpacity style={styles.listDeleteBtn} onPress={() => removeTaskChecklistItem(row.index)}>
                  <Text style={styles.listDeleteBtnText}>X</Text>
                </TouchableOpacity>
              </View>
            )) : <Text style={styles.small}>To zadanie nie ma jeszcze listy pozycji.</Text>}
            <TextInput
              style={styles.inputSingle}
              value={taskChecklistInput}
              onChangeText={setTaskChecklistInput}
              placeholder="Dodaj produkt do tego zadania"
              placeholderTextColor="#7E93B9"
            />
            <View style={styles.actionRow}>
              <TouchableOpacity style={styles.primaryBtnSmall} onPress={addTaskChecklistItem}><Text style={styles.primaryBtnText}>Dodaj produkt</Text></TouchableOpacity>
            </View>
          </View>
        ) : null}
      </View>
    );
  };

  return (
    <SafeAreaView style={styles.safe}>
      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === "ios" ? "padding" : undefined}>
        <View style={styles.header}>
          <View>
            <Text style={styles.brand}>Jarvis Mobile v9</Text>
            <Text style={styles.subtitle}>Chat-first + Shopping flow + Plan cleanup</Text>
          </View>
          <View style={styles.badge}><Text style={styles.badgeText}>stable</Text></View>
        </View>

        <View style={styles.content}>
          {tab === "home" && (
            <ScrollView contentContainerStyle={styles.screen}>
              <View style={styles.card}><Text style={styles.screenTitle}>Home</Text><Text style={styles.body}>{summarizeDay(todayItems, "Dziś")}</Text><Text style={[styles.body, { marginTop: 10 }]}>{summarizeDay(tomorrowItems, "Jutro")}</Text></View>
            </ScrollView>
          )}

          {tab === "chat" && (
            <View style={styles.flexScreen}>
              <View style={styles.screenHeader}>
                <Text style={styles.screenTitle}>Chat</Text>
                <Text style={styles.screenLead}>Każda komenda głosowa trafia najpierw do chatu. Jarvis pokazuje, co zrozumiał, a potem zapisuje do planu lub Inboxa.</Text>
              </View>
              <View style={styles.chatFrame}>
                <ScrollView ref={scrollRef} style={styles.chatScroll} contentContainerStyle={styles.chatScrollContent} showsVerticalScrollIndicator persistentScrollbar indicatorStyle="white" keyboardShouldPersistTaps="handled">
                  {chatMessages.map((m, i) => (
                    <View key={`${i}-${m.role}`} style={[styles.bubble, m.role === "user" ? styles.userBubble : styles.assistantBubble, m.error ? styles.errorBubble : null]}>
                      <Text style={styles.bubbleRole}>{m.role === "user" ? "Ty" : "Jarvis"}</Text>
                      <Text style={styles.bubbleText}>{m.text}</Text>
                      {m.meta ? <Text style={styles.bubbleMeta}>{m.meta}</Text> : null}
                    </View>
                  ))}

                  {shoppingReview && (
                    <View style={[styles.bubble, styles.assistantBubble, { alignSelf: "stretch", maxWidth: "100%" }]}> 
                      <Text style={styles.bubbleRole}>Jarvis</Text>
                      <Text style={styles.bubbleText}>Zaznacz, co dodać do zadania:</Text>
                      {shoppingReview.items.map((item, idx) => (
                        <TouchableOpacity key={item.id} style={styles.checkRow} onPress={() => setShoppingReview((prev) => !prev ? prev : ({ ...prev, items: prev.items.map((row, i) => i === idx ? { ...row, checked: !row.checked } : row) }))}>
                          <Text style={styles.checkBox}>{item.checked ? "☑" : "☐"}</Text>
                          <Text style={styles.checkText}>{item.text}</Text>
                        </TouchableOpacity>
                      ))}
                      <View style={styles.actionRow}><TouchableOpacity style={styles.primaryBtnSmall} onPress={submitShoppingReview}><Text style={styles.primaryBtnText}>Dalej</Text></TouchableOpacity></View>
                    </View>
                  )}

                  {chatLoading && <View style={[styles.bubble, styles.assistantBubble]}><Text style={styles.bubbleRole}>Jarvis</Text><View style={styles.loadingRow}><ActivityIndicator color="#A7C4FF" /><Text style={styles.loadingText}>Jarvis myśli...</Text></View></View>}
                </ScrollView>
              </View>
              <View style={styles.inputDock}>
                <TextInput style={styles.input} value={chatInput} onChangeText={setChatInput} placeholder="Napisz albo powiedz do Jarvisa..." placeholderTextColor="#7E93B9" multiline textAlignVertical="top" autoCapitalize="sentences" />
                <View style={styles.actionRow}>
                  <TouchableOpacity style={styles.primaryBtnSmall} onPress={() => runChat()}><Text style={styles.primaryBtnText}>Wyślij</Text></TouchableOpacity>
                  <TouchableOpacity style={[styles.secondaryBtnSmall, voiceListening && voiceTarget === "chat" ? styles.stopBtn : null]} onPress={() => voiceListening && voiceTarget === "chat" ? stopVoice() : startVoice("chat")}><Text style={styles.secondaryBtnText}>{voiceListening && voiceTarget === "chat" ? "■ Stop" : "🎤 Voice"}</Text></TouchableOpacity>
                </View>
                <Text style={styles.helper}>{speechAvailable ? voiceStatus : "Voice module nie znaleziony w tym buildzie."}</Text>
              </View>
            </View>
          )}

          {tab === "plan" && (
            <ScrollView contentContainerStyle={styles.screen}>
              <View style={styles.card}>
                <Text style={styles.screenTitle}>Plan</Text>
                <Text style={styles.screenLead}>Kliknij zadanie zakupów, żeby zobaczyć listę i edytować ją na miejscu.</Text>
                <View style={styles.segmentWrap}>
                  <TouchableOpacity style={[styles.segmentBtn, !showTomorrow && styles.segmentBtnActive]} onPress={() => setShowTomorrow(false)}><Text style={[styles.segmentText, !showTomorrow && styles.segmentTextActive]}>Dziś</Text></TouchableOpacity>
                  <TouchableOpacity style={[styles.segmentBtn, showTomorrow && styles.segmentBtnActive]} onPress={() => setShowTomorrow(true)}><Text style={[styles.segmentText, showTomorrow && styles.segmentTextActive]}>Jutro</Text></TouchableOpacity>
                </View>
                <View style={styles.actionRow}>
                  <TouchableOpacity style={styles.primaryBtn} onPress={loadPlan}><Text style={styles.primaryBtnText}>{planLoading ? "Ładuję..." : "Odśwież"}</Text></TouchableOpacity>
                  <TouchableOpacity style={styles.secondaryBtn} onPress={runPlanner}><Text style={styles.secondaryBtnText}>AI planner</Text></TouchableOpacity>
                </View>
                <TouchableOpacity style={styles.secondaryBtn} onPress={confirmClearDay}><Text style={styles.secondaryBtnText}>Wyczyść dzień</Text></TouchableOpacity>
              </View>
              <View style={styles.card}>
                <Text style={styles.sectionTitle}>{showTomorrow ? "Jutro" : "Dziś"}</Text>
                {currentItems.length ? currentItems.map(renderTaskRow) : <Text style={styles.body}>Brak pozycji do pokazania.</Text>}
              </View>
              <View style={styles.card}><Text style={styles.sectionTitle}>Planner dnia</Text><Text style={styles.body}>{plannerText}</Text></View>
            </ScrollView>
          )}

          {tab === "inbox" && (
            <ScrollView contentContainerStyle={styles.screen}>
              <View style={styles.card}>
                <Text style={styles.screenTitle}>Inbox</Text>
                <Text style={styles.screenLead}>Tu trafiają rzeczy bez terminu. „dodaj do listy zakupów masło” zapisze produkt na później. „dodaj do zadania zakupów masło” dopisze go do najbliższych zakupów.</Text>
                <TextInput style={styles.input} value={inboxInput} onChangeText={setInboxInput} placeholder="Np. kup pastę do zębów albo muszę ogarnąć przegląd auta" placeholderTextColor="#7E93B9" multiline />
                <View style={styles.actionRow}>
                  <TouchableOpacity style={styles.primaryBtnSmall} onPress={() => addInbox()}><Text style={styles.primaryBtnText}>{inboxLoading ? "Dodaję..." : "Dodaj"}</Text></TouchableOpacity>
                  <TouchableOpacity style={[styles.secondaryBtnSmall, voiceListening && voiceTarget === "inbox" ? styles.stopBtn : null]} onPress={() => voiceListening && voiceTarget === "inbox" ? stopVoice() : startVoice("inbox")}><Text style={styles.secondaryBtnText}>{voiceListening && voiceTarget === "inbox" ? "■ Stop" : "🎤 Voice"}</Text></TouchableOpacity>
                  <TouchableOpacity style={styles.secondaryBtnSmall} onPress={loadInbox}><Text style={styles.secondaryBtnText}>Odśwież</Text></TouchableOpacity>
                </View>
                <Text style={styles.helper}>{inboxStatus || voiceStatus}</Text>
              </View>

              <View style={styles.card}>
                <Text style={styles.sectionTitle}>Lista zakupów</Text>
                {shoppingItems.length ? shoppingItems.map((item) => (
                  <View key={item.id} style={styles.listRow}><Text style={styles.listBullet}>•</Text><Text style={styles.listText}>{item.text}</Text><TouchableOpacity style={styles.listDeleteBtn} onPress={() => deleteInboxItem(item.id)}><Text style={styles.listDeleteBtnText}>X</Text></TouchableOpacity></View>
                )) : <Text style={styles.body}>Brak pozycji zakupowych.</Text>}
              </View>

              <View style={styles.card}>
                <Text style={styles.sectionTitle}>Do zaplanowania</Text>
                {unscheduledItems.length ? unscheduledItems.map((item) => (
                  <View key={item.id} style={styles.listRow}><Text style={styles.listBullet}>•</Text><Text style={styles.listText}>{item.text}</Text><TouchableOpacity style={styles.listDeleteBtn} onPress={() => deleteInboxItem(item.id)}><Text style={styles.listDeleteBtnText}>X</Text></TouchableOpacity></View>
                )) : <Text style={styles.body}>Brak luźnych pozycji.</Text>}
              </View>
            </ScrollView>
          )}

          {tab === "brain" && (
            <ScrollView contentContainerStyle={styles.screen}><View style={styles.card}><Text style={styles.screenTitle}>Brain</Text><Text style={styles.body}>Tu możesz testować priorytety i pamięć po stronie backendu.</Text></View></ScrollView>
          )}

          {tab === "settings" && (
            <ScrollView contentContainerStyle={styles.screen}>
              <View style={styles.card}>
                <Text style={styles.screenTitle}>Ustawienia</Text>
                <Text style={styles.label}>Backend URL</Text>
                <TextInput style={styles.inputSingle} value={backendDraft} onChangeText={setBackendDraft} placeholder={DEFAULT_BACKEND_URL} placeholderTextColor="#7E93B9" />
                <View style={styles.actionRow}><TouchableOpacity style={styles.primaryBtn} onPress={saveBackend}><Text style={styles.primaryBtnText}>Zapisz</Text></TouchableOpacity><TouchableOpacity style={styles.secondaryBtn} onPress={testBackend}><Text style={styles.secondaryBtnText}>Test backendu</Text></TouchableOpacity></View>
                <Text style={styles.helper}>{healthStatus}</Text>
              </View>
              <View style={styles.card}><Text style={styles.sectionTitle}>Test Ollamy</Text><TouchableOpacity style={styles.primaryBtn} onPress={testOllama}><Text style={styles.primaryBtnText}>Test Ollamy</Text></TouchableOpacity><Text style={styles.helper}>{ollamaStatus}</Text></View>
              <View style={styles.card}>
                <View style={styles.toggleRow}><View style={{ flex: 1 }}><Text style={styles.sectionTitle}>Lokalne powiadomienia</Text><Text style={styles.small}>Po zmianach Jarvis może wysłać krótkie powiadomienie.</Text></View><Switch value={notifyEnabled} onValueChange={(v) => { setNotifyEnabled(v); saveSettings(v, voiceAutoSend); }} /></View>
                <View style={styles.toggleRow}><View style={{ flex: 1 }}><Text style={styles.sectionTitle}>Voice auto-send</Text><Text style={styles.small}>Po rozpoznaniu od razu wysyła tekst.</Text></View><Switch value={voiceAutoSend} onValueChange={(v) => { setVoiceAutoSend(v); saveSettings(notifyEnabled, v); }} /></View>
              </View>
            </ScrollView>
          )}
        </View>

        <View style={styles.tabBar}>
          {[["home", "Home"], ["chat", "Chat"], ["plan", "Plan"], ["brain", "Brain"], ["inbox", "Inbox"], ["settings", "Ustaw."]].map(([key, label]) => (
            <TouchableOpacity key={key} style={[styles.tabBtn, tab === key && styles.tabBtnActive]} onPress={() => setTab(key as TabKey)}><Text style={[styles.tabText, tab === key && styles.tabTextActive]}>{label}</Text></TouchableOpacity>
          ))}
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: "#07182D" },
  header: { backgroundColor: "#0F1A2E", borderBottomWidth: 1, borderBottomColor: "#20314A", paddingHorizontal: 18, paddingTop: 16, paddingBottom: 14, flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
  brand: { color: "#F5F8FF", fontSize: 22, fontWeight: "800" },
  subtitle: { color: "#8CA1C9", marginTop: 4, fontSize: 13 },
  badge: { borderWidth: 1.5, borderColor: "#2F68FF", borderRadius: 999, paddingHorizontal: 14, paddingVertical: 8, backgroundColor: "#13213D" },
  badgeText: { color: "#FFF", fontWeight: "800" },
  content: { flex: 1, minHeight: 0 },
  flexScreen: { flex: 1, minHeight: 0 },
  screen: { padding: 16, paddingBottom: 24 },
  screenHeader: { paddingHorizontal: 16, paddingTop: 16, paddingBottom: 10 },
  screenTitle: { color: "#F5F8FF", fontSize: 20, fontWeight: "800" },
  screenLead: { color: "#93A7CC", fontSize: 15, marginTop: 8, lineHeight: 22 },
  card: { backgroundColor: "#16243E", borderRadius: 24, borderWidth: 1, borderColor: "#263B5F", padding: 16, marginBottom: 16 },
  sectionTitle: { color: "#FFF", fontSize: 17, fontWeight: "800", marginBottom: 6 },
  body: { color: "#DCE6FA", fontSize: 15, lineHeight: 23 },
  small: { color: "#9CB1D3", fontSize: 13, lineHeight: 19 },
  chatFrame: { flex: 1, minHeight: 0, paddingHorizontal: 16 },
  chatScroll: { flex: 1, minHeight: 0, backgroundColor: "#081D33", borderRadius: 22, borderWidth: 1, borderColor: "#0D335A" },
  chatScrollContent: { padding: 12, paddingBottom: 20 },
  bubble: { maxWidth: "86%", borderRadius: 20, paddingHorizontal: 14, paddingVertical: 12, marginBottom: 12 },
  assistantBubble: { alignSelf: "flex-start", backgroundColor: "#273A59" },
  userBubble: { alignSelf: "flex-end", backgroundColor: "#2F68FF" },
  errorBubble: { borderWidth: 1, borderColor: "#FF7B7B" },
  bubbleRole: { color: "#DFE8FA", fontWeight: "800", marginBottom: 6 },
  bubbleText: { color: "#FFF", fontSize: 16, lineHeight: 24 },
  bubbleMeta: { color: "#A8B8D5", fontSize: 12, marginTop: 8 },
  inputDock: { borderTopWidth: 1, borderTopColor: "#223654", backgroundColor: "#0F1A2E", paddingHorizontal: 16, paddingTop: 12, paddingBottom: 12 },
  input: { minHeight: 90, backgroundColor: "#182742", borderRadius: 18, paddingHorizontal: 16, paddingVertical: 14, color: "#FFF", fontSize: 16 },
  inputSingle: { minHeight: 48, backgroundColor: "#182742", borderRadius: 16, paddingHorizontal: 14, paddingVertical: 12, color: "#FFF", fontSize: 15, marginTop: 8 },
  actionRow: { flexDirection: "row", gap: 12, marginTop: 14, flexWrap: "wrap" },
  primaryBtn: { backgroundColor: "#2F68FF", borderRadius: 18, paddingHorizontal: 22, paddingVertical: 16 },
  secondaryBtn: { backgroundColor: "#13284A", borderRadius: 18, paddingHorizontal: 22, paddingVertical: 16, borderWidth: 1, borderColor: "#325B95" },
  primaryBtnSmall: { backgroundColor: "#2F68FF", borderRadius: 18, paddingHorizontal: 24, paddingVertical: 16 },
  secondaryBtnSmall: { backgroundColor: "#13284A", borderRadius: 18, paddingHorizontal: 24, paddingVertical: 16, borderWidth: 1, borderColor: "#325B95" },
  stopBtn: { backgroundColor: "#5A2030", borderColor: "#9E4054" },
  primaryBtnText: { color: "#FFF", fontWeight: "800", fontSize: 15 },
  secondaryBtnText: { color: "#E4ECFF", fontWeight: "800", fontSize: 15 },
  helper: { color: "#9CB1D3", marginTop: 14, fontSize: 14, lineHeight: 21 },
  loadingRow: { flexDirection: "row", alignItems: "center", gap: 10 },
  loadingText: { color: "#DCE6FA", fontSize: 15 },
  segmentWrap: { flexDirection: "row", backgroundColor: "#0B1A33", borderRadius: 22, padding: 4, borderWidth: 1, borderColor: "#28416B", marginTop: 14 },
  segmentBtn: { flex: 1, alignItems: "center", justifyContent: "center", paddingVertical: 14, borderRadius: 18 },
  segmentBtnActive: { backgroundColor: "#2F68FF" },
  segmentText: { color: "#9CB1D3", fontWeight: "800", fontSize: 16 },
  segmentTextActive: { color: "#FFF" },
  timelineCardWrap: { marginBottom: 8 },
  timelineRow: { flexDirection: "row", alignItems: "center", paddingVertical: 10 },
  timelineTime: { width: 66, color: "#FFF", fontSize: 18, fontWeight: "800" },
  timelineDot: { width: 20, height: 20, borderRadius: 10, backgroundColor: "#4196FF", marginRight: 14 },
  timelineTitle: { color: "#FFF", fontSize: 17, fontWeight: "800" },
  timelineMeta: { color: "#9CB1D3", fontSize: 15, marginTop: 6 },
  innerPanel: { marginLeft: 100, marginTop: 8, backgroundColor: "#10223D", borderRadius: 16, padding: 12, borderWidth: 1, borderColor: "#2A446A" },
  deletePill: { borderWidth: 1, borderColor: "#6F8DBD", borderRadius: 999, width: 42, height: 42, alignItems: "center", justifyContent: "center" },
  deletePillText: { color: "#FFF", fontWeight: "800", fontSize: 18 },
  checkRow: { flexDirection: "row", alignItems: "center", marginTop: 10 },
  checkBox: { color: "#FFF", fontSize: 30, width: 38 },
  checkText: { color: "#FFF", fontSize: 16, flex: 1 },
  listRow: { flexDirection: "row", alignItems: "center", paddingVertical: 8 },
  listBullet: { color: "#57A4FF", fontSize: 24, marginRight: 8, lineHeight: 24 },
  listText: { color: "#E4ECFF", fontSize: 16, flex: 1, lineHeight: 24 },
  listDeleteBtn: { borderWidth: 1, borderColor: "#5A77A5", borderRadius: 999, width: 34, height: 34, alignItems: "center", justifyContent: "center", marginLeft: 10 },
  listDeleteBtnText: { color: "#FFF", fontWeight: "800" },
  label: { color: "#A9BDD9", marginTop: 10, marginBottom: 2, fontSize: 13, fontWeight: "700" },
  toggleRow: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", marginBottom: 18 },
  tabBar: { flexDirection: "row", gap: 12, paddingHorizontal: 16, paddingBottom: 18, paddingTop: 12, backgroundColor: "#0F1A2E", borderTopWidth: 1, borderTopColor: "#20314A" },
  tabBtn: { flex: 1, borderRadius: 20, borderWidth: 1, borderColor: "#223A61", alignItems: "center", justifyContent: "center", paddingVertical: 16, backgroundColor: "#0F1A2E" },
  tabBtnActive: { backgroundColor: "#2F68FF", borderColor: "#2F68FF" },
  tabText: { color: "#DDE7FB", fontWeight: "800", fontSize: 14 },
  tabTextActive: { color: "#FFF" },
});
