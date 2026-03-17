import { useEffect, useState } from 'react';
import { View, Text, ScrollView, Pressable, StyleSheet, ActivityIndicator, Alert } from 'react-native';
import { getTomorrow, planTomorrow, DayPayload } from '@/src/api/mobile';
import { colors } from '@/src/theme';

export default function TomorrowScreen() {
  const [data, setData] = useState<DayPayload | null>(null);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try { setData(await getTomorrow()); } finally { setLoading(false); }
  };

  const onPlan = async () => {
    const result = await planTomorrow();
    Alert.alert('Jarvis', result.message);
    await load();
  };

  useEffect(() => { load(); }, []);

  return (
    <ScrollView style={styles.wrap} contentContainerStyle={styles.content}>
      <Text style={styles.h1}>Jutro</Text>
      <Text style={styles.sub}>Planner i przebudowa dnia</Text>

      <View style={styles.card}>
        <View style={{flexDirection: 'row', gap: 8}}>
          <Pressable style={styles.btnDark} onPress={onPlan}><Text style={styles.btnDarkText}>Zaplanuj jutro</Text></Pressable>
          <Pressable style={styles.btnLight} onPress={load}><Text style={styles.btnLightText}>Odśwież</Text></Pressable>
        </View>
      </View>

      {loading ? <ActivityIndicator /> : null}

      <View style={styles.card}>
        <Text style={styles.section}>Timeline jutra</Text>
        {(data?.timeline ?? []).map(item => (
          <View key={item.id} style={styles.row}>
            <Text style={styles.time}>{item.start}</Text>
            <View style={styles.dot} />
            <View style={{flex: 1}}>
              <Text style={styles.title}>{item.title}</Text>
              {!!item.location && <Text style={styles.muted}>{item.location}</Text>}
            </View>
          </View>
        ))}
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  wrap: { flex: 1, backgroundColor: colors.bg },
  content: { padding: 16, gap: 16 },
  h1: { fontSize: 28, fontWeight: '800', color: colors.text },
  sub: { color: colors.muted, marginTop: -8 },
  card: { backgroundColor: colors.card, borderRadius: 20, borderWidth: 1, borderColor: colors.border, padding: 16, gap: 12 },
  btnDark: { backgroundColor: colors.primary, borderRadius: 999, paddingHorizontal: 14, paddingVertical: 10 },
  btnDarkText: { color: 'white', fontWeight: '700' },
  btnLight: { backgroundColor: colors.chip, borderRadius: 999, paddingHorizontal: 14, paddingVertical: 10 },
  btnLightText: { color: colors.text, fontWeight: '700' },
  section: { fontSize: 16, fontWeight: '700', color: colors.text },
  row: { flexDirection: 'row', gap: 10 },
  time: { width: 52, fontWeight: '700', color: colors.text },
  dot: { width: 8, height: 8, borderRadius: 4, backgroundColor: colors.primary, marginTop: 6 },
  title: { fontWeight: '600', color: colors.text },
  muted: { color: colors.muted, fontSize: 12 }
});
