import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { View, ActivityIndicator, StyleSheet } from 'react-native';
import { AuthProvider, useAuth } from '../src/contexts/AuthContext';
import LoginScreen from '../src/screens/LoginScreen';
import { Colors } from '../src/constants/theme';

function AuthGate({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <View style={styles.loading}>
        <ActivityIndicator size="large" color={Colors.brandPrimary} />
      </View>
    );
  }

  if (!user) {
    return <LoginScreen />;
  }

  return <>{children}</>;
}

export default function RootLayout() {
  return (
    <AuthProvider>
      <StatusBar style="light" />
      <AuthGate>
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
      </AuthGate>
    </AuthProvider>
  );
}

const styles = StyleSheet.create({
  loading: {
    flex: 1, backgroundColor: Colors.background,
    justifyContent: 'center', alignItems: 'center',
  },
});
