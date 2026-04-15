import React, { useEffect, useState } from 'react';
import {
  View, Text, ScrollView, StyleSheet, TouchableOpacity, Alert, Platform,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import * as Application from 'expo-application';
import * as LocalAuthentication from 'expo-local-authentication';
import { useAuth } from '../src/contexts/AuthContext';
import { Colors, Spacing, FontSize } from '../src/constants/theme';

export default function SettingsScreen() {
  const router = useRouter();
  const { user, logout } = useAuth();
  const [biometricAvailable, setBiometricAvailable] = useState(false);
  const [biometricType, setBiometricType] = useState('');
  const [authenticated, setAuthenticated] = useState(false);

  useEffect(() => {
    checkBiometrics();
  }, []);

  const checkBiometrics = async () => {
    try {
      const compatible = await LocalAuthentication.hasHardwareAsync();
      const enrolled = await LocalAuthentication.isEnrolledAsync();
      setBiometricAvailable(compatible && enrolled);
      if (compatible) {
        const types = await LocalAuthentication.supportedAuthenticationTypesAsync();
        if (types.includes(LocalAuthentication.AuthenticationType.FACIAL_RECOGNITION)) {
          setBiometricType('Face ID');
        } else if (types.includes(LocalAuthentication.AuthenticationType.FINGERPRINT)) {
          setBiometricType('Fingerprint');
        } else {
          setBiometricType('Biometric');
        }
      }
    } catch (e) {
      console.error('Biometric check error:', e);
    }
  };

  const handleBiometricAuth = async () => {
    try {
      const result = await LocalAuthentication.authenticateAsync({
        promptMessage: 'Authenticate to BMIA',
        fallbackLabel: 'Use Passcode',
        disableDeviceFallback: false,
      });
      if (result.success) {
        setAuthenticated(true);
        Alert.alert('Success', 'Biometric authentication successful!');
      } else {
        Alert.alert('Failed', 'Authentication failed. Please try again.');
      }
    } catch (e) {
      Alert.alert('Error', 'Biometric authentication not available');
    }
  };

  const appVersion = Application.nativeApplicationVersion || '1.0.0';
  const buildNumber = Application.nativeBuildVersion || '1';

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <View style={styles.header}>
        <TouchableOpacity testID="settings-back" onPress={() => router.back()}>
          <Ionicons name="arrow-back" size={24} color={Colors.textPrimary} />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Settings</Text>
        <View style={{ width: 24 }} />
      </View>

      <ScrollView contentContainerStyle={styles.scrollContent}>
        {/* App Info */}
        <View style={styles.appInfo}>
          <View style={styles.appIconBox}>
            <Text style={styles.appIconText}>BMIA</Text>
          </View>
          <Text style={styles.appName}>Bharat Market Intel Agent</Text>
          <Text style={styles.appVersion}>Version {appVersion} (Build {buildNumber})</Text>
        </View>

        {/* Biometric Auth */}
        <Text style={styles.sectionTitle}>SECURITY</Text>
        <TouchableOpacity
          testID="biometric-auth-btn"
          style={styles.settingItem}
          onPress={handleBiometricAuth}
          disabled={!biometricAvailable}
        >
          <View style={styles.settingIcon}>
            <Ionicons name="finger-print" size={22} color={biometricAvailable ? Colors.brandPrimary : Colors.textTertiary} />
          </View>
          <View style={{ flex: 1 }}>
            <Text style={styles.settingLabel}>{biometricType || 'Biometric Auth'}</Text>
            <Text style={styles.settingDesc}>
              {biometricAvailable
                ? (authenticated ? 'Authenticated' : 'Tap to authenticate')
                : 'Not available on this device'}
            </Text>
          </View>
          {authenticated && <Ionicons name="checkmark-circle" size={22} color={Colors.positive} />}
        </TouchableOpacity>

        {/* User Info */}
        {user && (
          <>
            <Text style={styles.sectionTitle}>ACCOUNT</Text>
            <View style={styles.settingItem}>
              <View style={styles.settingIcon}>
                <Ionicons name="person" size={22} color={Colors.brandPrimary} />
              </View>
              <View style={{ flex: 1 }}>
                <Text style={styles.settingLabel}>{user.name || user.email}</Text>
                <Text style={styles.settingDesc}>{user.designation} | {user.department}</Text>
              </View>
            </View>
            <TouchableOpacity
              testID="logout-btn"
              style={[styles.settingItem, { marginTop: 8 }]}
              onPress={() => {
                Alert.alert('Logout', 'Are you sure you want to logout?', [
                  { text: 'Cancel', style: 'cancel' },
                  { text: 'Logout', style: 'destructive', onPress: () => logout() },
                ]);
              }}
            >
              <View style={[styles.settingIcon, { backgroundColor: 'rgba(239,68,68,0.1)' }]}>
                <Ionicons name="log-out" size={22} color={Colors.negative} />
              </View>
              <View style={{ flex: 1 }}>
                <Text style={[styles.settingLabel, { color: Colors.negative }]}>Logout</Text>
                <Text style={styles.settingDesc}>Sign out of your account</Text>
              </View>
            </TouchableOpacity>
          </>
        )}

        {/* About */}
        <Text style={styles.sectionTitle}>ABOUT</Text>
        {[
          { label: 'Platform', value: Platform.OS },
          { label: 'Expo SDK', value: '54' },
          { label: 'API Endpoint', value: 'bmia.pesmifs.com' },
          { label: 'Data Sources', value: 'NSE, BSE, Yahoo Finance' },
          { label: 'AI Models', value: 'GPT-4.1, Claude, Gemini' },
        ].map((item) => (
          <View key={item.label} style={styles.infoRow}>
            <Text style={styles.infoLabel}>{item.label}</Text>
            <Text style={styles.infoValue}>{item.value}</Text>
          </View>
        ))}

        {/* Disclaimer */}
        <View style={styles.disclaimerBox}>
          <Ionicons name="shield-checkmark" size={18} color={Colors.brandPrimary} />
          <Text style={styles.disclaimerText}>
            BMIA is for educational and informational purposes only. It does not constitute investment advice. All AI-generated signals and analysis are experimental. Always consult a SEBI-registered investment advisor before making financial decisions. Past performance does not guarantee future results.
          </Text>
        </View>

        <View style={{ height: 32 }} />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.background },
  header: {
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    paddingHorizontal: Spacing.base, paddingVertical: 12,
    borderBottomWidth: 1, borderBottomColor: Colors.border,
  },
  headerTitle: { color: Colors.textPrimary, fontSize: FontSize.h4, fontWeight: '700' },
  scrollContent: { padding: Spacing.base },
  appInfo: { alignItems: 'center', paddingVertical: 24 },
  appIconBox: {
    width: 72, height: 72, borderRadius: 16, backgroundColor: Colors.brandPrimary,
    justifyContent: 'center', alignItems: 'center',
  },
  appIconText: { color: '#fff', fontSize: 20, fontWeight: '900', letterSpacing: 2 },
  appName: { color: Colors.textPrimary, fontSize: FontSize.h3, fontWeight: '700', marginTop: 12 },
  appVersion: { color: Colors.textTertiary, fontSize: FontSize.small, marginTop: 4, fontVariant: ['tabular-nums'] },
  sectionTitle: {
    color: Colors.textTertiary, fontSize: FontSize.tiny, fontWeight: '700',
    letterSpacing: 1.5, marginTop: Spacing.section, marginBottom: Spacing.small,
  },
  settingItem: {
    flexDirection: 'row', alignItems: 'center', gap: 12,
    backgroundColor: Colors.surface, borderRadius: 8, borderWidth: 1, borderColor: Colors.border,
    padding: 14,
  },
  settingIcon: {
    width: 42, height: 42, borderRadius: 10, backgroundColor: 'rgba(59,130,246,0.1)',
    justifyContent: 'center', alignItems: 'center',
  },
  settingLabel: { color: Colors.textPrimary, fontSize: FontSize.bodyLarge, fontWeight: '600' },
  settingDesc: { color: Colors.textTertiary, fontSize: FontSize.small, marginTop: 2 },
  infoRow: {
    flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 10,
    borderBottomWidth: 1, borderBottomColor: 'rgba(39,39,42,0.5)',
  },
  infoLabel: { color: Colors.textTertiary, fontSize: FontSize.body },
  infoValue: { color: Colors.textPrimary, fontSize: FontSize.body, fontWeight: '600' },
  disclaimerBox: {
    flexDirection: 'row', gap: 10, backgroundColor: 'rgba(59,130,246,0.06)',
    padding: 14, borderRadius: 8, marginTop: Spacing.section,
  },
  disclaimerText: { color: Colors.textTertiary, fontSize: FontSize.small, flex: 1, lineHeight: 18 },
});
