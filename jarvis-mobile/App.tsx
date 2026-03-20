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
  try {
    return require("expo-notifications");
  } catch {
    return null;
  }
})();

const SpeechLib: any = (() => {
  try {
    return require("expo-speech-recognition");
  } catch {
    return null;
  }
})();

const SpeechModule: any =
  SpeechLib?.ExpoSpeechRecognitionModule || SpeechLib?.default || SpeechLib || null;

if (Notifications?.setNotificationHandler) {
  Notifications.setNotificationHandler({
    handleNotification: async () => ({
      shouldShowAlert: true,
      shouldPlaySound: false,
      shouldSetBadge: false,
    }),
  });
}

type TabKey = "home" | "chat" | "plan" | "brain" | "inbox" | "settings";
type VoiceTarget = "chat" | "inbox";
type ChatMessage = {
  role: "assistant" | "user";
  text: string;
  meta?: string;
  error?: boolean;
};
type TimelineItem = {
  id: string;
  kind: string;
  title: string;
  start: string;
  end: string;
  category?: string | null;
  task_id?: number | null;
  deletable?: boolean;
};
type InboxItem = { id: number; text: string; kind: string };
type ShoppingReview = {
  eventText: string;
  items: Array<InboxItem & { checked: boolean }>;
};

const STORAGE_BACKEND_URL = "jarvis_backend_url_v9";
const STORAGE_NOTIFY = "jarvis_notify_enabled_v9";
const STORAGE_VOICE_AUTOSEND = "jarvis_voice_autosend_v9";
const DEFAULT_BACKEND_URL = "http://192.168.8.118:8011";

function cleanUrl(url: string) {
  return url.trim().replace(/\/+$/, "");
}

function tryJson(text: string) {
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

function extractText(payload: any): string {
  if (!payload) return "Brak odpowiedzi.";
  const candidates = [
    payload.reply,
    payload.response,
    payload.answer,
    payload.message,
    payload.content,
    payload.text,
    payload?.data?.reply,
    payload?.data?.response,
  ];
  for (const c of candidates) {
    if (typeof c === "string" && c.trim()) return c.trim();
  }
  if (typeof payload === "string" && payload.trim()) return payload.trim();
  return "Odpowiedź w nieoczekiwanym formacie.";
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

function splitExtraItems(text: string) {
  return text
    .split(/[,\n;]/)
    .map((x) => x.trim())
    .filter(Boolean);
}

export default function App() {
  const [tab, setTab] = useState<TabKey>("chat");
  const [backendUrl, setBackendUrl] = useState(DEFAULT_BACKEND_URL);
  const [backendDraft, setBackendDraft] = useState(DEFAULT_BACKEND_URL);

  const [chatInput, setChatInput] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([
    {
      role: "assistant",
      text: "Jarvis v9 gotowy. Chat jest głównym oknem komunikacji, Inbox trzyma rzeczy bez terminu, a plan pokazuje tylko to, co zostało osadzone w czasie.",
      meta: "voice → chat → klasyfikacja → plan / inbox / pytanie",
    },
  ]);

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
  const [showTomorrow, setShowTomorrow] = useState(false);

  const [priorities, setPriorities] = useState<any[]>([]);
  const [brainLoading, setBrainLoading] = useState(false);
  const [memoryText, setMemoryText] = useState("Brak pamięci do pokazania.");
  const [plannerText, setPlannerText] = useState("Planner jeszcze nie został uruchomiony.");

  const [healthStatus, setHealthStatus] = useState("Nie sprawdzano backendu.");
  const [ollamaStatus, setOllamaStatus] = useState("Nie sprawdzano Ollamy.");
  const [notifyEnabled, setNotifyEnabled] = useState(true);
  const [voiceAutoSend, setVoiceAutoSend] = useState(true);

  const [voiceListening, setVoiceListening] = useState(false);
  const [voiceTarget, setVoiceTarget] = useState<VoiceTarget>("chat");
  const [voiceStatus, setVoiceStatus] = useState("Voice gotowy.");
  const [shoppingReview, setShoppingReview] = useState<ShoppingReview | null>(null);
  const [extraShoppingText, setExtraShoppingText] = useState("");
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
        if (savedUrl?.trim()) {
          setBackendUrl(savedUrl);
          setBackendDraft(savedUrl);
        }
        if (savedNotify !== null) setNotifyEnabled(savedNotify === "true");
        if (savedAuto !== null) setVoiceAutoSend(savedAuto === "true");
      } catch {}

      try {
        await Notifications?.requestPermissionsAsync?.();
      } catch {}
    })();
  }, []);

  useEffect(() => {
    const t = setTimeout(() => {
      scrollRef.current?.scrollToEnd({ animated: true });
    }, 80);
    return () => clearTimeout(t);
  }, [chatMessages, shoppingReview]);

  useEffect(() => {
    loadPlan();
    loadInbox();
    loadBrain();
    return () => cleanupSpeechListeners();
  }, [backendUrl]);

  function cleanupSpeechListeners() {
    subscriptionsRef.current.forEach((sub) => {
      try {
        sub?.remove?.();
      } catch {}
    });
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
    if (!response.ok) {
      throw new Error(typeof parsed === "string" ? parsed : `HTTP ${response.status}`);
    }
    return parsed;
  }

  async function apiPost(path: string, body: any) {
    const response = await fetch(`${cleanUrl(backendUrl)}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const raw = await response.text();
    const parsed = tryJson(raw);
    if (!response.ok) {
      throw new Error(typeof parsed === "string" ? parsed : `HTTP ${response.status}`);
    }
    return parsed;
  }

  async function apiDelete(path: string) {
    const response = await fetch(`${cleanUrl(backendUrl)}${path}`, { method: "DELETE" });
    const raw = await response.text();
    const parsed = tryJson(raw);
    if (!response.ok) {
      throw new Error(typeof parsed === "string" ? parsed : `HTTP ${response.status}`);
    }
    return parsed;
  }

  async function saveBackend() {
    const normalized = cleanUrl(backendDraft);
    if (!normalized) {
      Alert.alert("Błąd", "Backend URL nie może być pusty.");
      return;
    }
    setBackendUrl(normalized);
    try {
      await AsyncStorage.setItem(STORAGE_BACKEND_URL, normalized);
    } catch {}
    setHealthStatus("Backend zapisany.");
  }

  async function testBackend() {
    setHealthStatus("Sprawdzam...");
    try {
      const data = await apiGet("/mobile/health");
      setHealthStatus(`OK: ${extractText(data)}`);
    } catch (e: any) {
      setHealthStatus(`Błąd backendu: ${e?.message || "nieznany błąd"}`);
    }
  }

  async function testOllama() {
    setOllamaStatus("Testuję...");
    try {
      const data = await apiPost("/mobile/ai/chat", {
        message: "Napisz dokładnie: TEST OLLAMA DZIALA",
      });
      setOllamaStatus(`Odpowiedź AI: ${extractText(data)}`);
    } catch (e: any) {
      setOllamaStatus(`Błąd AI/Ollamy: ${e?.message || "nieznany błąd"}`);
    }
  }

  async function loadPlan() {
    setPlanLoading(true);
    try {
      const [today, tomorrow] = await Promise.allSettled([
        apiGet("/mobile/today"),
        apiGet("/mobile/tomorrow"),
      ]);
      if (today.status === "fulfilled") {
        setTodayItems(Array.isArray(today.value?.timeline) ? today.value.timeline : []);
        setTodayDate(today.value?.date || "");
      }
      if (tomorrow.status === "fulfilled") {
        setTomorrowItems(Array.isArray(tomorrow.value?.timeline) ? tomorrow.value.timeline : []);
        setTomorrowDate(tomorrow.value?.date || "");
      }
    } catch {
      Alert.alert("Plan", "Nie udało się pobrać planu.");
    } finally {
      setPlanLoading(false);
    }
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

  async function loadBrain() {
    setBrainLoading(true);
    try {
      const [prio, memory] = await Promise.allSettled([
        apiGet("/mobile/priorities/tomorrow"),
        apiGet("/mobile/memory"),
      ]);
      if (prio.status === "fulfilled") {
        setPriorities(Array.isArray(prio.value?.priorities) ? prio.value.priorities : []);
      }
      if (memory.status === "fulfilled") {
        setMemoryText(extractText(memory.value));
      }
    } finally {
      setBrainLoading(false);
    }
  }

  async function runPlanner() {
    const base = showTomorrow ? tomorrowItems : todayItems;
    if (!base.length) {
      setPlannerText("Brak pozycji do zaplanowania. Dodaj coś do Inboxa lub Planu.");
      return;
    }
    const top = priorities[0]?.title || priorities[0]?.name || priorities[0]?.text || "brak";
    setPlannerText(
      [
        `Top priorytet: ${top}`,
        "",
        ...base.slice(0, 8).map((x) => `${prettyTime(x?.start)} — ${x?.title || "pozycja"}`),
      ].join("\n")
    );
  }

  function conversationTail() {
    return chatMessages.slice(-8).map((m) => ({ role: m.role, content: m.text }));
  }

  async function runChat(textOverride?: string) {
    const text = (textOverride ?? chatInput).trim();
    if (!text || chatLoading) return;

    setChatMessages((prev) => [...prev, { role: "user", text, meta: "chat-first" }]);
    setChatInput("");
    setChatLoading(true);
    setShoppingReview(null);
    setExtraShoppingText("");

    try {
      const data = await apiPost("/mobile/chat", {
        message: text,
        conversation_tail: conversationTail(),
      });
      const actions = Array.isArray(data?.actions) ? data.actions : [];
      const reviewAction = actions.find((a: any) => a?.type === "shopping_review");
      if (reviewAction) {
        setShoppingReview({
          eventText: String(reviewAction?.event_text || text),
          items: Array.isArray(reviewAction?.items)
            ? reviewAction.items.map((item: any) => ({ ...item, checked: true }))
            : [],
        });
      }
      setChatMessages((prev) => [
        ...prev,
        { role: "assistant", text: extractText(data), meta: data?.intent || "jarvis" },
      ]);
      if (data?.changed) {
        await Promise.all([loadPlan(), loadInbox(), loadBrain()]);
      }
      if (notifyEnabled && data?.changed) {
        try {
          await Notifications?.scheduleNotificationAsync?.({
            content: { title: "Jarvis", body: extractText(data) },
            trigger: null,
          });
        } catch {}
      }
    } catch (e: any) {
      setChatMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          text: `Błąd: ${e?.message || "nie udało się połączyć."}`,
          meta: "error",
          error: true,
        },
      ]);
    } finally {
      setChatLoading(false);
    }
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
    } finally {
      setInboxLoading(false);
    }
  }

  async function submitShoppingReview() {
    if (!shoppingReview) return;
    setChatLoading(true);
    try {
      const data = await apiPost("/mobile/shopping/confirm", {
        event_text: shoppingReview.eventText,
        selected_item_ids: shoppingReview.items.filter((x) => x.checked).map((x) => x.id),
        extra_items: splitExtraItems(extraShoppingText),
      });
      setChatMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          text: extractText(data),
          meta: "shopping-confirmed",
        },
      ]);
      setShoppingReview(null);
      setExtraShoppingText("");
      await Promise.all([loadPlan(), loadInbox(), loadBrain()]);
    } catch (e: any) {
      setChatMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          text: `Błąd tworzenia zakupów: ${e?.message || "nie udało się zapisać."}`,
          meta: "error",
          error: true,
        },
      ]);
    } finally {
      setChatLoading(false);
    }
  }

  async function deleteTask(taskId: number) {
    try {
      const data = await apiDelete(`/mobile/plan/task/${taskId}`);
      setChatMessages((prev) => [...prev, { role: "assistant", text: extractText(data), meta: "delete-task" }]);
      await loadPlan();
    } catch (e: any) {
      Alert.alert("Błąd", e?.message || "Nie udało się usunąć zadania.");
    }
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
      {
        text: "Usuń",
        style: "destructive",
        onPress: async () => {
          try {
            const data = await apiDelete(`/mobile/plan/day/${currentDate}`);
            setChatMessages((prev) => [...prev, { role: "assistant", text: extractText(data), meta: "clear-day" }]);
            await loadPlan();
          } catch (e: any) {
            Alert.alert("Błąd", e?.message || "Nie udało się wyczyścić dnia.");
          }
        },
      },
    ]);
  }

  function applyTranscript(text: string, target: VoiceTarget) {
    if (!text.trim()) return;
    if (target === "chat") {
      setChatInput(text.trim());
      if (voiceAutoSend) {
        setVoiceStatus("Przetwarzam...");
        setTimeout(() => runChat(text.trim()), 100);
      } else {
        setVoiceStatus("Gotowe.");
      }
    } else {
      setInboxInput(text.trim());
      if (voiceAutoSend) {
        setVoiceStatus("Przetwarzam...");
        setTimeout(() => addInbox(text.trim()), 100);
      } else {
        setVoiceStatus("Gotowe.");
      }
    }
  }

  async function startVoice(target: VoiceTarget) {
    if (!SpeechModule) {
      Alert.alert(
        "Voice",
        "Brak expo-speech-recognition w tym buildzie. Uruchom development build po npx expo run:android."
      );
      return;
    }
    setVoiceTarget(target);
    setVoiceStatus("Proszę o dostęp do mikrofonu...");
    transcriptRef.current = "";
    cleanupSpeechListeners();
    try {
      if (SpeechModule?.requestPermissionsAsync) {
        const perm = await SpeechModule.requestPermissionsAsync();
        const granted = perm === true || perm?.granted === true || perm?.status === "granted";
        if (!granted) {
          setVoiceStatus("Brak zgody na mikrofon.");
          return;
        }
      }
      if (SpeechModule?.addListener) {
        subscriptionsRef.current.push(
          SpeechModule.addListener("result", (event: any) => {
            const transcript = parseTranscriptFromEvent(event);
            if (transcript) {
              transcriptRef.current = transcript;
              setVoiceStatus(`Słucham... ${transcript}`);
            }
          })
        );
        subscriptionsRef.current.push(
          SpeechModule.addListener("error", (event: any) => {
            setVoiceStatus(`Voice error: ${event?.message || event?.error || "Błąd voice."}`);
            setVoiceListening(false);
          })
        );
        subscriptionsRef.current.push(
          SpeechModule.addListener("end", () => {
            const finalTranscript = transcriptRef.current.trim();
            if (finalTranscript) {
              applyTranscript(finalTranscript, target);
            } else {
              setVoiceStatus("Nie rozpoznałam wypowiedzi.");
            }
            setVoiceListening(false);
            cleanupSpeechListeners();
          })
        );
      }
      setVoiceListening(true);
      setVoiceStatus("Słucham...");
      if (SpeechModule?.start) {
        await SpeechModule.start({
          lang: "pl-PL",
          interimResults: true,
          continuous: false,
          maxAlternatives: 1,
        });
      } else if (SpeechModule?.startAsync) {
        const result = await SpeechModule.startAsync({ lang: "pl-PL", interimResults: false });
        const transcript = result?.transcript || "";
        if (transcript) applyTranscript(transcript, target);
        else setVoiceStatus("Nie rozpoznałam wypowiedzi.");
        setVoiceListening(false);
      } else {
        setVoiceListening(false);
        setVoiceStatus("Ten build nie expose'uje metody start.");
      }
    } catch (e: any) {
      setVoiceListening(false);
      setVoiceStatus(`Voice error: ${e?.message || "nie udało się uruchomić nasłuchu."}`);
      cleanupSpeechListeners();
    }
  }

  async function stopVoice() {
    try {
      setVoiceStatus("Przetwarzam...");
      if (SpeechModule?.stop) await SpeechModule.stop();
      if (SpeechModule?.stopAsync) await SpeechModule.stopAsync();
    } catch {
      setVoiceStatus("Nie udało się zatrzymać nasłuchu.");
    }
  }

  return (
    <SafeAreaView style={styles.safe}>
      <KeyboardAvoidingView style={styles.safe} behavior={Platform.OS === "ios" ? "padding" : undefined}>
        <View style={styles.header}>
          <View>
            <Text style={styles.brand}>Jarvis Mobile v9</Text>
            <Text style={styles.subtitle}>Chat-first + Shopping flow + Plan cleanup</Text>
          </View>
          <View style={styles.badge}>
            <Text style={styles.badgeText}>stable</Text>
          </View>
        </View>

        <View style={styles.content}>
          {tab === "home" && (
            <ScrollView contentContainerStyle={styles.screen}>
              <View style={styles.card}>
                <Text style={styles.screenTitle}>Home</Text>
                <Text style={styles.screenLead}>
                  Chat jest centrum dowodzenia. Inbox trzyma backlog bez terminu. Plan pokazuje zadania osadzone w czasie.
                </Text>
              </View>
              <View style={styles.card}>
                <Text style={styles.sectionTitle}>Plan dziś</Text>
                <Text style={styles.body}>{todayItems.length ? `${todayItems.length} pozycji` : "Brak pozycji."}</Text>
              </View>
              <View style={styles.card}>
                <Text style={styles.sectionTitle}>Inbox</Text>
                <Text style={styles.body}>Zakupy: {shoppingItems.length} • Bez terminu: {unscheduledItems.length}</Text>
              </View>
            </ScrollView>
          )}

          {tab === "chat" && (
            <View style={styles.flexScreen}>
              <View style={styles.screenHeader}>
                <Text style={styles.screenTitle}>Chat</Text>
                <Text style={styles.screenLead}>
                  Każda komenda głosowa trafia najpierw do chatu. Jarvis pokazuje, co zrozumiał, a potem zapisuje do planu lub Inboxa.
                </Text>
              </View>

              <View style={styles.chatFrame}>
                <ScrollView
                  ref={scrollRef}
                  style={styles.chatScroll}
                  contentContainerStyle={styles.chatScrollContent}
                  showsVerticalScrollIndicator
                  persistentScrollbar
                  indicatorStyle="white"
                  keyboardShouldPersistTaps="handled"
                >
                  {chatMessages.map((m, i) => (
                    <View
                      key={`${i}-${m.role}`}
                      style={[
                        styles.bubble,
                        m.role === "user" ? styles.userBubble : styles.assistantBubble,
                        m.error ? styles.errorBubble : null,
                      ]}
                    >
                      <Text style={styles.bubbleRole}>{m.role === "user" ? "Ty" : "Jarvis"}</Text>
                      <Text style={styles.bubbleText}>{m.text}</Text>
                      {m.meta ? <Text style={styles.bubbleMeta}>{m.meta}</Text> : null}
                    </View>
                  ))}

                  {shoppingReview && (
                    <View style={[styles.bubble, styles.assistantBubble, styles.reviewBubble]}>
                      <Text style={styles.bubbleRole}>Potwierdzenie zakupów</Text>
                      <Text style={styles.bubbleText}>Zaznacz, co dodać do zadania:</Text>
                      {shoppingReview.items.map((item, idx) => (
                        <TouchableOpacity
                          key={`${item.id}-${idx}`}
                          style={styles.checkboxRow}
                          onPress={() =>
                            setShoppingReview((prev) =>
                              prev
                                ? {
                                    ...prev,
                                    items: prev.items.map((x) =>
                                      x.id === item.id ? { ...x, checked: !x.checked } : x
                                    ),
                                  }
                                : prev
                            )
                          }
                        >
                          <Text style={styles.checkboxMark}>{item.checked ? "☑" : "☐"}</Text>
                          <Text style={styles.checkboxText}>{item.text}</Text>
                        </TouchableOpacity>
                      ))}
                      <Text style={[styles.bubbleText, { marginTop: 12 }]}>Czy dodać coś jeszcze?</Text>
                      <TextInput
                        style={styles.reviewInput}
                        value={extraShoppingText}
                        onChangeText={setExtraShoppingText}
                        placeholder="Np. chleb, jajka"
                        placeholderTextColor="#7E93B9"
                        multiline
                      />
                      <TouchableOpacity style={styles.primaryBtnSmall} onPress={submitShoppingReview}>
                        <Text style={styles.primaryBtnText}>Utwórz zadanie zakupów</Text>
                      </TouchableOpacity>
                    </View>
                  )}

                  {chatLoading && (
                    <View style={[styles.bubble, styles.assistantBubble]}>
                      <Text style={styles.bubbleRole}>Jarvis</Text>
                      <View style={styles.loadingRow}>
                        <ActivityIndicator color="#A7C4FF" />
                        <Text style={styles.loadingText}>Jarvis myśli...</Text>
                      </View>
                    </View>
                  )}
                </ScrollView>
              </View>

              <View style={styles.inputDock}>
                <TextInput
                  style={styles.input}
                  value={chatInput}
                  onChangeText={setChatInput}
                  placeholder="Napisz albo powiedz do Jarvisa..."
                  placeholderTextColor="#7E93B9"
                  multiline
                  textAlignVertical="top"
                  autoCapitalize="sentences"
                />
                <View style={styles.actionRow}>
                  <TouchableOpacity style={styles.primaryBtnSmall} onPress={() => runChat()}>
                    <Text style={styles.primaryBtnText}>Wyślij</Text>
                  </TouchableOpacity>
                  <TouchableOpacity
                    style={[styles.secondaryBtnSmall, voiceListening && voiceTarget === "chat" ? styles.stopBtn : null]}
                    onPress={() => (voiceListening && voiceTarget === "chat" ? stopVoice() : startVoice("chat"))}
                  >
                    <Text style={styles.secondaryBtnText}>
                      {voiceListening && voiceTarget === "chat" ? "■ Stop" : "🎤 Voice"}
                    </Text>
                  </TouchableOpacity>
                </View>
                <Text style={styles.helper}>{speechAvailable ? voiceStatus : "Voice module nie znaleziony w tym buildzie."}</Text>
              </View>
            </View>
          )}

          {tab === "plan" && (
            <ScrollView contentContainerStyle={styles.screen}>
              <View style={styles.card}>
                <Text style={styles.screenTitle}>Plan</Text>
                <Text style={styles.screenLead}>Usuwaj pojedyncze zadania przez X albo wyczyść cały dzień po potwierdzeniu.</Text>
                <View style={styles.segmentWrap}>
                  <TouchableOpacity
                    style={[styles.segmentBtn, !showTomorrow && styles.segmentBtnActive]}
                    onPress={() => setShowTomorrow(false)}
                  >
                    <Text style={[styles.segmentText, !showTomorrow && styles.segmentTextActive]}>Dziś</Text>
                  </TouchableOpacity>
                  <TouchableOpacity
                    style={[styles.segmentBtn, showTomorrow && styles.segmentBtnActive]}
                    onPress={() => setShowTomorrow(true)}
                  >
                    <Text style={[styles.segmentText, showTomorrow && styles.segmentTextActive]}>Jutro</Text>
                  </TouchableOpacity>
                </View>
                <View style={styles.actionRow}>
                  <TouchableOpacity style={styles.primaryBtn} onPress={loadPlan}>
                    <Text style={styles.primaryBtnText}>{planLoading ? "Ładuję..." : "Odśwież"}</Text>
                  </TouchableOpacity>
                  <TouchableOpacity style={styles.secondaryBtn} onPress={runPlanner}>
                    <Text style={styles.secondaryBtnText}>AI planner</Text>
                  </TouchableOpacity>
                  <TouchableOpacity style={styles.secondaryBtn} onPress={confirmClearDay}>
                    <Text style={styles.secondaryBtnText}>Wyczyść dzień</Text>
                  </TouchableOpacity>
                </View>
              </View>

              <View style={styles.card}>
                <Text style={styles.sectionTitle}>{showTomorrow ? "Jutro" : "Dziś"}</Text>
                {currentItems.length ? (
                  currentItems.map((item) => (
                    <View key={item.id} style={styles.timelineRow}>
                      <Text style={styles.timelineTime}>{prettyTime(item?.start)}</Text>
                      <View style={styles.timelineDot} />
                      <View style={{ flex: 1 }}>
                        <Text style={styles.timelineTitle}>{item?.title || "Pozycja"}</Text>
                        <Text style={styles.timelineMeta}>{item?.category || item?.kind || "item"}</Text>
                      </View>
                      {item.deletable && item.task_id ? (
                        <TouchableOpacity style={styles.deleteBtn} onPress={() => confirmDeleteTask(item.task_id!, item.title)}>
                          <Text style={styles.deleteBtnText}>X</Text>
                        </TouchableOpacity>
                      ) : null}
                    </View>
                  ))
                ) : (
                  <Text style={styles.body}>Brak pozycji do pokazania.</Text>
                )}
              </View>

              <View style={styles.card}>
                <Text style={styles.sectionTitle}>Planner dnia</Text>
                <Text style={styles.body}>{plannerText}</Text>
              </View>
            </ScrollView>
          )}

          {tab === "brain" && (
            <ScrollView contentContainerStyle={styles.screen}>
              <View style={styles.card}>
                <Text style={styles.screenTitle}>Brain</Text>
                <Text style={styles.screenLead}>Priorytety i pamięć Jarvisa.</Text>
                <View style={styles.actionRow}>
                  <TouchableOpacity style={styles.primaryBtn} onPress={loadBrain}>
                    <Text style={styles.primaryBtnText}>{brainLoading ? "Ładuję..." : "Odśwież"}</Text>
                  </TouchableOpacity>
                </View>
              </View>
              <View style={styles.card}>
                <Text style={styles.sectionTitle}>Top priorytety jutra</Text>
                {priorities.length ? (
                  priorities.map((item, idx) => (
                    <View key={idx} style={styles.priorityRow}>
                      <View style={styles.priorityCircle}>
                        <Text style={styles.priorityCircleText}>{item?.priority || idx + 1}</Text>
                      </View>
                      <View style={{ flex: 1 }}>
                        <Text style={styles.timelineTitle}>{item?.title || "Priorytet"}</Text>
                        <Text style={styles.timelineMeta}>{prettyTime(item?.time)}</Text>
                      </View>
                    </View>
                  ))
                ) : (
                  <Text style={styles.body}>Brak priorytetów jutra.</Text>
                )}
              </View>
              <View style={styles.card}>
                <Text style={styles.sectionTitle}>Pamięć Jarvisa</Text>
                <Text style={styles.body}>{memoryText}</Text>
              </View>
            </ScrollView>
          )}

          {tab === "inbox" && (
            <ScrollView contentContainerStyle={styles.screen}>
              <View style={styles.card}>
                <Text style={styles.screenTitle}>Inbox</Text>
                <Text style={styles.screenLead}>Tu trafiają rzeczy bez terminu. Zakupy są osobno, żeby dało się je potem przypiąć do jednego zadania.</Text>
                <TextInput
                  style={styles.input}
                  value={inboxInput}
                  onChangeText={setInboxInput}
                  placeholder="Np. kup pastę do zębów albo ogarnąć przegląd auta"
                  placeholderTextColor="#7E93B9"
                  multiline
                />
                <View style={styles.actionRow}>
                  <TouchableOpacity style={styles.primaryBtnSmall} onPress={() => addInbox()}>
                    <Text style={styles.primaryBtnText}>{inboxLoading ? "Dodaję..." : "Dodaj"}</Text>
                  </TouchableOpacity>
                  <TouchableOpacity
                    style={[styles.secondaryBtnSmall, voiceListening && voiceTarget === "inbox" ? styles.stopBtn : null]}
                    onPress={() => (voiceListening && voiceTarget === "inbox" ? stopVoice() : startVoice("inbox"))}
                  >
                    <Text style={styles.secondaryBtnText}>
                      {voiceListening && voiceTarget === "inbox" ? "■ Stop" : "🎤 Voice"}
                    </Text>
                  </TouchableOpacity>
                  <TouchableOpacity style={styles.secondaryBtnSmall} onPress={loadInbox}>
                    <Text style={styles.secondaryBtnText}>Odśwież</Text>
                  </TouchableOpacity>
                </View>
                <Text style={styles.helper}>{inboxStatus || voiceStatus}</Text>
              </View>

              <View style={styles.card}>
                <Text style={styles.sectionTitle}>Lista zakupów</Text>
                {shoppingItems.length ? (
                  shoppingItems.map((item) => (
                    <View key={item.id} style={styles.inboxRow}>
                      <Text style={styles.inboxBullet}>•</Text>
                      <Text style={styles.body}>{item.text}</Text>
                    </View>
                  ))
                ) : (
                  <Text style={styles.body}>Brak rzeczy na liście zakupów.</Text>
                )}
              </View>

              <View style={styles.card}>
                <Text style={styles.sectionTitle}>Do zaplanowania</Text>
                {unscheduledItems.length ? (
                  unscheduledItems.map((item) => (
                    <View key={item.id} style={styles.inboxRow}>
                      <Text style={styles.inboxBullet}>•</Text>
                      <Text style={styles.body}>{item.text}</Text>
                    </View>
                  ))
                ) : (
                  <Text style={styles.body}>Brak oczekujących wpisów bez terminu.</Text>
                )}
              </View>
            </ScrollView>
          )}

          {tab === "settings" && (
            <ScrollView contentContainerStyle={styles.screen}>
              <View style={styles.card}>
                <Text style={styles.screenTitle}>Ustawienia</Text>
                <Text style={styles.screenLead}>Backend, test Ollamy i konfiguracja voice.</Text>
                <Text style={styles.label}>Backend URL</Text>
                <TextInput
                  style={styles.inputSingle}
                  value={backendDraft}
                  onChangeText={setBackendDraft}
                  placeholder={DEFAULT_BACKEND_URL}
                  placeholderTextColor="#7E93B9"
                />
                <View style={styles.actionRow}>
                  <TouchableOpacity style={styles.primaryBtn} onPress={saveBackend}>
                    <Text style={styles.primaryBtnText}>Zapisz</Text>
                  </TouchableOpacity>
                  <TouchableOpacity style={styles.secondaryBtn} onPress={testBackend}>
                    <Text style={styles.secondaryBtnText}>Test backendu</Text>
                  </TouchableOpacity>
                </View>
                <Text style={styles.helper}>{healthStatus}</Text>
              </View>

              <View style={styles.card}>
                <Text style={styles.sectionTitle}>Test Ollamy</Text>
                <TouchableOpacity style={styles.primaryBtn} onPress={testOllama}>
                  <Text style={styles.primaryBtnText}>Test Ollamy</Text>
                </TouchableOpacity>
                <Text style={styles.helper}>{ollamaStatus}</Text>
              </View>

              <View style={styles.card}>
                <View style={styles.toggleRow}>
                  <View style={{ flex: 1 }}>
                    <Text style={styles.sectionTitle}>Lokalne powiadomienia</Text>
                    <Text style={styles.small}>Powiadom po zmianie planu lub Inboxa.</Text>
                  </View>
                  <Switch
                    value={notifyEnabled}
                    onValueChange={(v) => {
                      setNotifyEnabled(v);
                      saveSettings(v, voiceAutoSend);
                    }}
                  />
                </View>

                <View style={styles.toggleRow}>
                  <View style={{ flex: 1 }}>
                    <Text style={styles.sectionTitle}>Voice auto-send</Text>
                    <Text style={styles.small}>Po rozpoznaniu od razu wysyła tekst do Jarvisa.</Text>
                  </View>
                  <Switch
                    value={voiceAutoSend}
                    onValueChange={(v) => {
                      setVoiceAutoSend(v);
                      saveSettings(notifyEnabled, v);
                    }}
                  />
                </View>

                <Text style={styles.helper}>
                  {speechAvailable
                    ? "Voice module dostępny w tym buildzie."
                    : "Voice module niewykryty. Uruchom npx expo run:android na telefonie."}
                </Text>
              </View>
            </ScrollView>
          )}
        </View>

        <View style={styles.tabBar}>
          {[
            ["home", "Home"],
            ["chat", "Chat"],
            ["plan", "Plan"],
            ["brain", "Brain"],
            ["inbox", "Inbox"],
            ["settings", "Ustaw."],
          ].map(([key, label]) => (
            <TouchableOpacity
              key={key}
              style={[styles.tabBtn, tab === key && styles.tabBtnActive]}
              onPress={() => setTab(key as TabKey)}
            >
              <Text style={[styles.tabText, tab === key && styles.tabTextActive]}>{label}</Text>
            </TouchableOpacity>
          ))}
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: "#07182D" },
  header: {
    backgroundColor: "#0F1A2E",
    borderBottomWidth: 1,
    borderBottomColor: "#20314A",
    paddingHorizontal: 18,
    paddingTop: 16,
    paddingBottom: 14,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
  },
  brand: { color: "#F5F8FF", fontSize: 22, fontWeight: "800" },
  subtitle: { color: "#8CA1C9", marginTop: 4, fontSize: 13 },
  badge: {
    borderWidth: 1.5,
    borderColor: "#2F68FF",
    borderRadius: 999,
    paddingHorizontal: 14,
    paddingVertical: 8,
    backgroundColor: "#13213D",
  },
  badgeText: { color: "#FFF", fontWeight: "800" },
  content: { flex: 1, minHeight: 0 },
  flexScreen: { flex: 1, minHeight: 0 },
  screen: { padding: 16, paddingBottom: 24 },
  screenHeader: { paddingHorizontal: 16, paddingTop: 16, paddingBottom: 10 },
  screenTitle: { color: "#F5F8FF", fontSize: 20, fontWeight: "800" },
  screenLead: { color: "#93A7CC", fontSize: 15, marginTop: 8, lineHeight: 22 },
  card: {
    backgroundColor: "#16243E",
    borderRadius: 24,
    borderWidth: 1,
    borderColor: "#263B5F",
    padding: 16,
    marginBottom: 16,
  },
  sectionTitle: { color: "#FFF", fontSize: 17, fontWeight: "800", marginBottom: 6 },
  body: { color: "#DCE6FA", fontSize: 15, lineHeight: 23 },
  small: { color: "#9CB1D3", fontSize: 13, lineHeight: 19 },
  chatFrame: { flex: 1, minHeight: 0, paddingHorizontal: 16 },
  chatScroll: {
    flex: 1,
    minHeight: 0,
    backgroundColor: "#081D33",
    borderRadius: 22,
    borderWidth: 1,
    borderColor: "#0D335A",
  },
  chatScrollContent: { padding: 12, paddingBottom: 20 },
  bubble: { maxWidth: "90%", borderRadius: 20, paddingHorizontal: 14, paddingVertical: 12, marginBottom: 12 },
  assistantBubble: { alignSelf: "flex-start", backgroundColor: "#273A59" },
  userBubble: { alignSelf: "flex-end", backgroundColor: "#2F68FF" },
  reviewBubble: { maxWidth: "100%" },
  errorBubble: { borderWidth: 1, borderColor: "#FF7B7B" },
  bubbleRole: { color: "#DFE8FA", fontWeight: "800", marginBottom: 6 },
  bubbleText: { color: "#FFF", fontSize: 16, lineHeight: 24 },
  bubbleMeta: { color: "#A8B8D5", fontSize: 12, marginTop: 8 },
  inputDock: {
    borderTopWidth: 1,
    borderTopColor: "#223654",
    backgroundColor: "#0F1A2E",
    paddingHorizontal: 16,
    paddingTop: 12,
    paddingBottom: 12,
  },
  input: {
    minHeight: 90,
    backgroundColor: "#182742",
    borderRadius: 18,
    paddingHorizontal: 16,
    paddingVertical: 14,
    color: "#FFF",
    fontSize: 17,
    textAlignVertical: "top",
  },
  inputSingle: {
    backgroundColor: "#182742",
    borderRadius: 18,
    paddingHorizontal: 16,
    paddingVertical: 14,
    color: "#FFF",
    fontSize: 16,
  },
  reviewInput: {
    minHeight: 64,
    backgroundColor: "#182742",
    borderRadius: 14,
    paddingHorizontal: 14,
    paddingVertical: 12,
    color: "#FFF",
    fontSize: 15,
    marginTop: 10,
    marginBottom: 12,
  },
  actionRow: { flexDirection: "row", gap: 10, flexWrap: "wrap", marginTop: 12 },
  primaryBtn: { backgroundColor: "#2F68FF", borderRadius: 16, paddingHorizontal: 18, paddingVertical: 14 },
  secondaryBtn: {
    backgroundColor: "#122744",
    borderRadius: 16,
    borderWidth: 1,
    borderColor: "#2C466C",
    paddingHorizontal: 18,
    paddingVertical: 14,
  },
  primaryBtnSmall: {
    backgroundColor: "#2F68FF",
    borderRadius: 16,
    paddingHorizontal: 18,
    paddingVertical: 14,
    minWidth: 110,
    alignItems: "center",
  },
  secondaryBtnSmall: {
    backgroundColor: "#122744",
    borderRadius: 16,
    borderWidth: 1,
    borderColor: "#2C466C",
    paddingHorizontal: 18,
    paddingVertical: 14,
    minWidth: 120,
    alignItems: "center",
  },
  stopBtn: { backgroundColor: "#4B2333", borderColor: "#8B5161" },
  deleteBtn: {
    width: 34,
    height: 34,
    borderRadius: 999,
    borderWidth: 1,
    borderColor: "#6B89B8",
    alignItems: "center",
    justifyContent: "center",
    marginLeft: 10,
  },
  deleteBtnText: { color: "#FFF", fontWeight: "800" },
  primaryBtnText: { color: "#FFF", fontWeight: "800", fontSize: 15 },
  secondaryBtnText: { color: "#E5EDFF", fontWeight: "700", fontSize: 15 },
  helper: { color: "#90A6CA", marginTop: 10, lineHeight: 20 },
  label: { color: "#FFF", fontWeight: "700", marginBottom: 8 },
  segmentWrap: {
    flexDirection: "row",
    backgroundColor: "#101D35",
    borderWidth: 1,
    borderColor: "#29456A",
    borderRadius: 18,
    padding: 6,
    marginTop: 14,
  },
  segmentBtn: { flex: 1, alignItems: "center", borderRadius: 14, paddingVertical: 12 },
  segmentBtnActive: { backgroundColor: "#2F68FF" },
  segmentText: { color: "#9BB0D4", fontWeight: "700" },
  segmentTextActive: { color: "#FFF" },
  timelineRow: { flexDirection: "row", alignItems: "flex-start", marginBottom: 14 },
  timelineTime: { width: 58, color: "#FFF", fontWeight: "800", marginTop: 2 },
  timelineDot: { width: 10, height: 10, borderRadius: 999, backgroundColor: "#4BA3FF", marginTop: 7, marginHorizontal: 10 },
  timelineTitle: { color: "#FFF", fontWeight: "800", fontSize: 16 },
  timelineMeta: { color: "#91A7CC", marginTop: 4 },
  priorityRow: { flexDirection: "row", alignItems: "center", marginBottom: 14 },
  priorityCircle: {
    width: 46,
    height: 46,
    borderRadius: 999,
    borderWidth: 1.5,
    borderColor: "#2F68FF",
    backgroundColor: "#12213A",
    alignItems: "center",
    justifyContent: "center",
    marginRight: 14,
  },
  priorityCircleText: { color: "#FFF", fontWeight: "800" },
  loadingRow: { flexDirection: "row", alignItems: "center" },
  loadingText: { color: "#DCE6FA", marginLeft: 10 },
  toggleRow: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", paddingVertical: 8 },
  checkboxRow: { flexDirection: "row", alignItems: "center", marginTop: 10 },
  checkboxMark: { color: "#FFF", fontSize: 20, marginRight: 10 },
  checkboxText: { color: "#DCE6FA", fontSize: 15, flex: 1 },
  inboxRow: { flexDirection: "row", alignItems: "flex-start", marginTop: 8 },
  inboxBullet: { color: "#4BA3FF", fontSize: 18, marginRight: 8, marginTop: 1 },
  tabBar: {
    backgroundColor: "#0F1A2E",
    borderTopWidth: 1,
    borderTopColor: "#223654",
    paddingHorizontal: 10,
    paddingTop: 10,
    paddingBottom: 14,
    flexDirection: "row",
    justifyContent: "space-between",
    gap: 8,
  },
  tabBtn: {
    flex: 1,
    borderRadius: 18,
    borderWidth: 1,
    borderColor: "#203A60",
    paddingVertical: 16,
    alignItems: "center",
    backgroundColor: "#0D1A31",
  },
  tabBtnActive: { backgroundColor: "#2F68FF", borderColor: "#2F68FF" },
  tabText: { color: "#E7EEFF", fontWeight: "800", fontSize: 14 },
  tabTextActive: { color: "#FFF" },
});
