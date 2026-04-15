import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { Colors } from '../src/constants/theme';

export default function RootLayout() {
  return (
    <>
      <StatusBar style="light" />
      <Stack
        screenOptions={{
          headerShown: false,
          contentStyle: { backgroundColor: Colors.background },
          animation: 'slide_from_right',
        }}
      >
        <Stack.Screen name="(tabs)" />
        <Stack.Screen name="analysis" options={{ presentation: 'card' }} />
        <Stack.Screen name="portfolio-detail" options={{ presentation: 'card' }} />
        <Stack.Screen name="track-record" options={{ presentation: 'card' }} />
        <Stack.Screen name="watchlist" options={{ presentation: 'card' }} />
        <Stack.Screen name="guidance" options={{ presentation: 'card' }} />
        <Stack.Screen name="how-it-works" options={{ presentation: 'card' }} />
        <Stack.Screen name="audit-log" options={{ presentation: 'card' }} />
        <Stack.Screen name="settings" options={{ presentation: 'card' }} />
      </Stack>
    </>
  );
}
