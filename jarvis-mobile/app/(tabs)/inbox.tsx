import { useState } from 'react';
import { Text, ScrollView, TextInput, Pressable, StyleSheet, Alert, View } from 'react-native';
import { createInboxItem } from '@/src/api/mobile';
import { colors } from '@/src/theme';

export default function InboxScreen() {
  const [text, setText] = useState('jutro o 9 dentysta przy Marszałkowska 10');

  const onSend = async () => {
    const result = await createInboxItem(text);
    Alert.alert('Jarvis', result.message);
    setText('');
  };

  return (
    <ScrollView style={styles.wrap} contentContainerStyle={styles.content}>
      <Text style={styles.h1}>Inbox</Text>
      <Text style={styles.sub}>Szybki capture</Text>

      <View style={styles.card}>
        <Text style={styles.section}>Dodaj do Jarvisa</Text>
        <TextInput
          multiline
          value={text}
          onChangeText={setText}
          placeholder='Napisz np. jutro o 9 dentysta przy Marszałkowska 10'
          style={styles.input}
        />
        <Pressable style={styles.btnDark} onPress={onSend}><Text style={styles.btnDarkText}>Dodaj</Text></Pressable>
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
  input: { minHeight: 120, borderWidth: 1, borderColor: colors.border, borderRadius: 16, padding: 12, backgroundColor: '#FAFAFA', textAlignVertical: 'top' },
  btnDark: { alignSelf: 'flex-start', backgroundColor: colors.primary, borderRadius: 999, paddingHorizontal: 14, paddingVertical: 10 },
  btnDarkText: { color: 'white', fontWeight: '700' },
});
