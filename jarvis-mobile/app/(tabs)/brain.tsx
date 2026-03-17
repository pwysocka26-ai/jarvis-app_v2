import { useEffect, useState } from 'react';
import { Text, ScrollView, StyleSheet, ActivityIndicator, View } from 'react-native';
import { getPrioritiesTomorrow } from '@/src/api/mobile';
import { colors } from '@/src/theme';

export default function BrainScreen() {
  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getPrioritiesTomorrow().then(r => setItems(r.priorities)).finally(() => setLoading(false));
  }, []);

  return (
    <ScrollView style={styles.wrap} contentContainerStyle={styles.content}>
      <Text style={styles.h1}>Brain</Text>
      <Text style={styles.sub}>Pamięć i priorytety</Text>

      <View style={styles.card}>
        <Text style={styles.section}>Priorytety jutra</Text>
        {loading ? <ActivityIndicator /> : items.map((item, idx) => (
          <Text key={idx} style={styles.item}>• {item.time ?? '—'} {item.title} — {item.category} (p{item.priority})</Text>
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
  section: { fontSize: 16, fontWeight: '700', color: colors.text },
  item: { color: colors.text }
});
