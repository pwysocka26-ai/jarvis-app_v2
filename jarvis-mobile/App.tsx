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

const STORAGE_BACKEND_URL = "jarvis_backend_url_v7";
const STORAGE_NOTIFY = "jarvis_notify_enabled_v7";
const STORAGE_VOICE_AUTOSEND = "jarvis_voice_autosend_v7";
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

function isExplicitTaskCommand(text: string) {
  const lower = text.toLowerCase().trim();
  return (
    lower.startsWith("dodaj ") ||
    lower.startsWith("ustaw ") ||
    lower.startsWith("zaplanuj ") ||
    lower.startsWith("jutro ") ||
    lower.startsWith("dziś ") ||
    lower.startsWith("dzis ") ||
    lower.startsWith("pojutrze ")
  );
}

function summarizeDay(items: any[], label: string): string {
  if (!items?.length) return `${label}: brak pozycji do pokazania.`;
  const first = items[0];
  return `${label}: ${items.length} pozycji. Najbliżej: ${prettyTime(
    first?.time || first?.start
  )} ${first?.title || first?.name || first?.text || "pozycja"}.`;
}

function parseTaskMeta(text: string) {
  const lower = text.toLowerCase();
  const day = lower.includes("pojutrze")
    ? "pojutrze"
    : lower.includes("jutro")
    ? "jutro"
    : "dziś";
  const tm = lower.match(/(\d{1,2})[:.]?(\d{2})?/);
  const time = tm
    ? `${String(Number(tm[1])).padStart(2, "0")}:${String(
        Number(tm[2] || "0")
      ).padStart(2, "0")}`
    : "brak czasu";
  return `${day} • ${time}`;
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
      text: "Jarvis v7 gotowy. Voice jest wpięty w Chat i Inbox.",
      meta: "klik → słucham → input → opcjonalny auto-send",
    },
  ]);

  const [inboxInput, setInboxInput] = useState("");
  const [inboxLoading, setInboxLoading] = useState(false);
  const [inboxStatus, setInboxStatus] = useState("");

  const [todayItems, setTodayItems] = useState<any[]>([]);
  const [tomorrowItems, setTomorrowItems] = useState<any[]>([]);
  const [planLoading, setPlanLoading] = useState(false);
  const [showTomorrow, setShowTomorrow] = useState(false);

  const [priorities, setPriorities] = useState<any[]>([]);
  const [brainLoading, setBrainLoading] = useState(false);
  const [memoryText, setMemoryText] = useState("Brak pamięci do pokazania.");
  const [plannerText, setPlannerText] = useState("Planner jeszcze nie został uruchomiony.");

  const [healthStatus, setHealthStatus] = useState("Nie sprawdzano backendu.");
  const [ollamaStatus, setOllamaStatus] = useState("Nie sprawdzano Ollamy.");
  const [notifyEnabled, setNotifyEnabled] = useState(true);
  const [voiceAutoSend, setVoiceAutoSend] = useState(false);

  const [voiceListening, setVoiceListening] = useState(false);
  const [voiceTarget, setVoiceTarget] = useState<VoiceTarget>("chat");
  const [voiceStatus, setVoiceStatus] = useState("Voice gotowy.");
  const transcriptRef = useRef("");
  const subscriptionsRef = useRef<any[]>([]);
  const scrollRef = useRef<ScrollView | null>(null);

  const speechAvailable = useMemo(() => !!SpeechModule, []);

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
  }, [chatMessages]);

  useEffect(() => {
    return () => cleanupSpeechListeners();
  }, []);

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
        const items = Array.isArray(today.value?.items)
          ? today.value.items
          : Array.isArray(today.value?.timeline)
          ? today.value.timeline
          : [];
        setTodayItems(items);
      }

      if (tomorrow.status === "fulfilled") {
        const items = Array.isArray(tomorrow.value?.items)
          ? tomorrow.value.items
          : Array.isArray(tomorrow.value?.timeline)
          ? tomorrow.value.timeline
          : [];
        setTomorrowItems(items);
      }
    } catch {
      Alert.alert("Plan", "Nie udało się pobrać planu.");
    } finally {
      setPlanLoading(false);
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
        const items = Array.isArray(prio.value?.items)
          ? prio.value.items
          : Array.isArray(prio.value?.priorities)
          ? prio.value.priorities
          : [];
        setPriorities(items);
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
      setPlannerText("Brak pozycji do zaplanowania. Dodaj coś do Inboxa.");
      return;
    }
    const top = priorities[0]?.title || priorities[0]?.name || priorities[0]?.text || "brak";
    setPlannerText(
      [
        `Top priorytet: ${top}`,
        "",
        ...base
          .slice(0, 8)
          .map(
            (x) =>
              `${prettyTime(x?.time || x?.start)} — ${x?.title || x?.name || x?.text || "pozycja"}`
          ),
      ].join("\n")
    );
  }

  async function runChat(textOverride?: string) {
    const text = (textOverride ?? chatInput).trim();
    if (!text || chatLoading) return;

    setChatMessages((prev) => [
      ...prev,
      {
        role: "user",
        text,
        meta: isExplicitTaskCommand(text) ? `inbox-intent • ${parseTaskMeta(text)}` : "ai",
      },
    ]);
    setChatInput("");
    setChatLoading(true);

    try {
      if (text.toLowerCase().includes("co mam dziś") || text.toLowerCase().includes("co mam dzis")) {
        if (!todayItems.length) await loadPlan();
        setChatMessages((prev) => [
          ...prev,
          { role: "assistant", text: summarizeDay(todayItems, "Dziś"), meta: "plan/today" },
        ]);
      } else if (
        text.toLowerCase().includes("plan jutra") ||
        text.toLowerCase().includes("pokaż plan jutra")
      ) {
        if (!tomorrowItems.length) await loadPlan();
        setChatMessages((prev) => [
          ...prev,
          { role: "assistant", text: summarizeDay(tomorrowItems, "Jutro"), meta: "plan/tomorrow" },
        ]);
      } else if (text.toLowerCase().includes("test ollama")) {
        const data = await apiPost("/mobile/ai/chat", {
          message: "Napisz dokładnie: TEST OLLAMA DZIALA",
        });
        setChatMessages((prev) => [
          ...prev,
          { role: "assistant", text: extractText(data), meta: "ollama-test" },
        ]);
      } else if (isExplicitTaskCommand(text)) {
        const data = await apiPost("/mobile/inbox", { text });
        setChatMessages((prev) => [
          ...prev,
          { role: "assistant", text: extractText(data), meta: `inbox • ${parseTaskMeta(text)}` },
        ]);
        await loadPlan();
      } else {
        const data = await apiPost("/mobile/ai/chat", { message: text });
        setChatMessages((prev) => [...prev, { role: "assistant", text: extractText(data), meta: "ai" }]);
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
      const reply = extractText(data);
      setInboxStatus(reply);
      setInboxInput("");
      setChatMessages((prev) => [
        ...prev,
        { role: "assistant", text: `Inbox: ${reply}`, meta: `inbox • ${parseTaskMeta(text)}` },
      ]);
      await loadPlan();

      if (notifyEnabled) {
        try {
          await Notifications?.scheduleNotificationAsync?.({
            content: { title: "Jarvis", body: text },
            trigger: null,
          });
        } catch {}
      }
    } catch (e: any) {
      setInboxStatus(`Błąd Inboxa: ${e?.message || "nieznany błąd"}`);
    } finally {
      setInboxLoading(false);
    }
  }

  
function smartParse(text: string) {
  const lower = text.toLowerCase();
  let date = "";
  let time = "";

  const now = new Date();

  if (lower.includes("jutro")) {
    const d = new Date(now);
    d.setDate(d.getDate() + 1);
    date = d.toISOString().split("T")[0];
  } else if (lower.includes("pojutrze")) {
    const d = new Date(now);
    d.setDate(d.getDate() + 2);
    date = d.toISOString().split("T")[0];
  } else if (lower.includes("dziś") || lower.includes("dzis")) {
    date = now.toISOString().split("T")[0];
  }

  if (lower.includes("rano")) time = "09:00";
  if (lower.includes("po pracy")) time = "18:00";
  if (lower.includes("wiecz")) time = "20:00";

  const timeMatch = text.match(/(\d{1,2})[:.]?(\d{2})?/);
  if (timeMatch) {
    const h = timeMatch[1];
    const m = timeMatch[2] || "00";
    time = `${h.padStart(2,"0")}:${m}`;
  }

  return {
    text,
    date,
    time,
  };
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
      const parsed = smartParse(text.trim());
      const finalText = parsed.text + (parsed.date ? ` | ${parsed.date}` : "") + (parsed.time ? ` ${parsed.time}` : "");
      setInboxInput(finalText);
      if (voiceAutoSend) {
        setVoiceStatus("Przetwarzam...");
        setTimeout(() => addInbox(finalText), 100);
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
        const result = await SpeechModule.startAsync({
          lang: "pl-PL",
          interimResults: false,
        });
        const transcript = result?.transcript || "";
        if (transcript) {
          applyTranscript(transcript, target);
        } else {
          setVoiceStatus("Nie rozpoznałam wypowiedzi.");
        }
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

  const currentItems = showTomorrow ? tomorrowItems : todayItems;

  return (
    <SafeAreaView style={styles.safe}>
      <KeyboardAvoidingView
        style={styles.safe}
        behavior={Platform.OS === "ios" ? "padding" : undefined}
      >
        <View style={styles.header}>
          <View>
            <Text style={styles.brand}>Jarvis Mobile v7</Text>
            <Text style={styles.subtitle}>Full app + voice in Chat and Inbox</Text>
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
                  Wracamy do pełnego Jarvisa: chat, inbox, plan, brain i voice.
                </Text>
                <View style={styles.actionRow}>
                  <TouchableOpacity style={styles.primaryBtn} onPress={() => setTab("chat")}>
                    <Text style={styles.primaryBtnText}>Otwórz Chat</Text>
                  </TouchableOpacity>
                  <TouchableOpacity style={styles.secondaryBtn} onPress={() => setTab("inbox")}>
                    <Text style={styles.secondaryBtnText}>Otwórz Inbox</Text>
                  </TouchableOpacity>
                </View>
              </View>
              <View style={styles.card}>
                <Text style={styles.sectionTitle}>Dziś</Text>
                <Text style={styles.body}>{summarizeDay(todayItems, "Dziś")}</Text>
              </View>
              <View style={styles.card}>
                <Text style={styles.sectionTitle}>Jutro</Text>
                <Text style={styles.body}>{summarizeDay(tomorrowItems, "Jutro")}</Text>
              </View>
            </ScrollView>
          )}

          {tab === "chat" && (
            <View style={styles.flexScreen}>
              <View style={styles.screenHeader}>
                <Text style={styles.screenTitle}>Chat</Text>
                <Text style={styles.screenLead}>
                  Kliknij Voice → start nasłuchu → wynik wpada do inputa → opcjonalnie auto-send.
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
                  placeholder="Napisz do Jarvisa..."
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
                    style={[
                      styles.secondaryBtnSmall,
                      voiceListening && voiceTarget === "chat" ? styles.stopBtn : null,
                    ]}
                    onPress={() =>
                      voiceListening && voiceTarget === "chat" ? stopVoice() : startVoice("chat")
                    }
                  >
                    <Text style={styles.secondaryBtnText}>
                      {voiceListening && voiceTarget === "chat" ? "■ Stop" : "🎤 Voice"}
                    </Text>
                  </TouchableOpacity>
                </View>
                <Text style={styles.helper}>
                  {speechAvailable ? voiceStatus : "Voice module nie znaleziony w tym buildzie."}
                </Text>
              </View>
            </View>
          )}

          {tab === "plan" && (
            <ScrollView contentContainerStyle={styles.screen}>
              <View style={styles.card}>
                <Text style={styles.screenTitle}>Plan</Text>
                <Text style={styles.screenLead}>Dziś i jutro z backendu + planner AI.</Text>
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
                </View>
              </View>

              <View style={styles.card}>
                <Text style={styles.sectionTitle}>{showTomorrow ? "Jutro" : "Dziś"}</Text>
                {currentItems.length ? (
                  currentItems.map((item, idx) => (
                    <View key={idx} style={styles.timelineRow}>
                      <Text style={styles.timelineTime}>{prettyTime(item?.time || item?.start)}</Text>
                      <View style={styles.timelineDot} />
                      <View style={{ flex: 1 }}>
                        <Text style={styles.timelineTitle}>
                          {item?.title || item?.name || item?.text || "Pozycja"}
                        </Text>
                        <Text style={styles.timelineMeta}>{item?.type || item?.category || "item"}</Text>
                      </View>
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
                <Text style={styles.screenLead}>Priorytety i pamięć długoterminowa.</Text>
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
                        <Text style={styles.timelineTitle}>
                          {item?.title || item?.name || item?.text || "Priorytet"}
                        </Text>
                        <Text style={styles.timelineMeta}>{prettyTime(item?.time || item?.start)}</Text>
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
                <Text style={styles.screenLead}>
                  Voice może wpisać komendę do inboxa i opcjonalnie od razu ją wysłać.
                </Text>
                <TextInput
                  style={styles.input}
                  value={inboxInput}
                  onChangeText={setInboxInput}
                  placeholder="Np. jutro 9:00 dentysta"
                  placeholderTextColor="#7E93B9"
                  multiline
                />
                <View style={styles.actionRow}>
                  <TouchableOpacity style={styles.primaryBtnSmall} onPress={() => addInbox()}>
                    <Text style={styles.primaryBtnText}>{inboxLoading ? "Dodaję..." : "Dodaj"}</Text>
                  </TouchableOpacity>
                  <TouchableOpacity
                    style={[
                      styles.secondaryBtnSmall,
                      voiceListening && voiceTarget === "inbox" ? styles.stopBtn : null,
                    ]}
                    onPress={() =>
                      voiceListening && voiceTarget === "inbox" ? stopVoice() : startVoice("inbox")
                    }
                  >
                    <Text style={styles.secondaryBtnText}>
                      {voiceListening && voiceTarget === "inbox" ? "■ Stop" : "🎤 Voice"}
                    </Text>
                  </TouchableOpacity>
                </View>
                <Text style={styles.helper}>{inboxStatus || voiceStatus}</Text>
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
                    <Text style={styles.small}>Przypomnienia po dodaniu do inboxa.</Text>
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
                    <Text style={styles.small}>Po rozpoznaniu od razu wysyła tekst.</Text>
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
  bubble: { maxWidth: "86%", borderRadius: 20, paddingHorizontal: 14, paddingVertical: 12, marginBottom: 12 },
  assistantBubble: { alignSelf: "flex-start", backgroundColor: "#273A59" },
  userBubble: { alignSelf: "flex-end", backgroundColor: "#2F68FF" },
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
  tabBar: {
    backgroundColor: "#0F1A2E",
    borderTopWidth: 1,
    borderTopColor: "#20314A",
    paddingHorizontal: 10,
    paddingTop: 12,
    paddingBottom: 18,
    flexDirection: "row",
    gap: 8,
  },
  tabBtn: {
    flex: 1,
    backgroundColor: "#121F37",
    borderWidth: 1,
    borderColor: "#263A58",
    borderRadius: 16,
    paddingVertical: 13,
    alignItems: "center",
  },
  tabBtnActive: { backgroundColor: "#2F68FF", borderColor: "#2F68FF" },
  tabText: { color: "#D9E4FA", fontWeight: "700", fontSize: 13 },
  tabTextActive: { color: "#FFF" },
});

