import { Text, ScrollView, StyleSheet, View } from 'react-native';
import { API_BASE } from '@/src/api/client';
import { colors } from '@/src/theme';

export default function SettingsScreen() {
  return (
    <ScrollView style={styles.wrap} contentContainerStyle={styles.content}>
      <Text style={styles.h1}>Ustawienia</Text>
      <Text style={styles.sub}>Dom, dojazdy i API</Text>

      <View style={styles.card}>
        <Text style={styles.section}>API</Text>
        <Text style={styles.item}>{API_BASE}</Text>
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
