import { Tabs } from 'expo-router';

export default function TabsLayout() {
  return (
    <Tabs screenOptions={{ headerShown: false }}>
      <Tabs.Screen name="index" options={{ title: 'Dziś' }} />
      <Tabs.Screen name="tomorrow" options={{ title: 'Jutro' }} />
      <Tabs.Screen name="inbox" options={{ title: 'Inbox' }} />
      <Tabs.Screen name="brain" options={{ title: 'Brain' }} />
      <Tabs.Screen name="settings" options={{ title: 'Ustawienia' }} />
    </Tabs>
  );
}
