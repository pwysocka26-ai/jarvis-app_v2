import { useEffect, useState } from 'react';
import { View, Text, ScrollView, Pressable, StyleSheet, ActivityIndicator } from 'react-native';
import { getToday, DayPayload } from '@/src/api/mobile';
import { colors } from '@/src/theme';

export default function TodayScreen() {
  const [data, setData] = useState<DayPayload | null>(null);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try { setData(await getToday()); } finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  return (
    <ScrollView style={styles.wrap} contentContainerStyle={styles.content}>
      <Text style={styles.h1}>Dziś</Text>
      <Text style={styles.sub}>Plan dnia i szybkie akcje</Text>

      <View style={[styles.card, styles.hero]}>
        <Text style={styles.heroLabel}>Co teraz</Text>
        <Text style={styles.heroTitle}>{data?.summary.next_item ?? 'Brak punktów'}</Text>
        <Text style={styles.heroSub}>Najbliższy punkt: {data?.summary.next_time ?? '—'}</Text>
        <Pressable style={styles.btnLight} onPress={load}><Text style={styles.btnLightText}>Odśwież</Text></Pressable>
      </View>

      {loading ? <ActivityIndicator /> : null}

      <View style={styles.card}>
        <Text style={styles.section}>Timeline</Text>
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
  hero: { backgroundColor: colors.primary, borderColor: colors.primary },
  heroLabel: { color: '#D1D5DB', fontSize: 12, textTransform: 'uppercase' },
  heroTitle: { color: 'white', fontSize: 24, fontWeight: '800' },
  heroSub: { color: '#D1D5DB' },
  btnLight: { alignSelf: 'flex-start', backgroundColor: 'white', borderRadius: 999, paddingHorizontal: 14, paddingVertical: 10 },
  btnLightText: { color: colors.text, fontWeight: '700' },
  section: { fontSize: 16, fontWeight: '700', color: colors.text },
  row: { flexDirection: 'row', gap: 10 },
  time: { width: 52, fontWeight: '700', color: colors.text },
  dot: { width: 8, height: 8, borderRadius: 4, backgroundColor: colors.primary, marginTop: 6 },
  title: { fontWeight: '600', color: colors.text },
  muted: { color: colors.muted, fontSize: 12 }
});
