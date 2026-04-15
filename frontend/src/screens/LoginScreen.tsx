import React, { useState, useRef } from 'react';
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet,
  ActivityIndicator, KeyboardAvoidingView, Platform, ScrollView,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { api } from '../api/client';
import { useAuth } from '../contexts/AuthContext';
import { Colors, Spacing, FontSize } from '../constants/theme';

type Step = 'email' | 'password' | 'set-password';

export default function LoginScreen() {
  const { login } = useAuth();
  const [step, setStep] = useState<Step>('email');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPw, setConfirmPw] = useState('');
  const [employee, setEmployee] = useState<any>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const pwRef = useRef<TextInput>(null);

  const handleEmailCheck = async () => {
    if (!email.trim()) return;
    setLoading(true); setError('');
    try {
      const data = await api.checkEmail(email.trim());
      setEmployee(data);
      setStep(data.has_password ? 'password' : 'set-password');
      setTimeout(() => pwRef.current?.focus(), 200);
    } catch (e: any) {
      setError(e.message || 'Verification failed');
    } finally {
      setLoading(false);
    }
  };

  const handleLogin = async () => {
    if (!password) return;
    setLoading(true); setError('');
    try {
      const data = await api.login(email.trim(), password);
      await login(data.token, {
        email: data.email,
        name: data.name,
        department: data.department,
        designation: data.designation,
        superadmin: data.superadmin,
      });
    } catch (e: any) {
      setError(e.message || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  const handleSetPassword = async () => {
    if (password.length < 6) { setError('Minimum 6 characters'); return; }
    if (password !== confirmPw) { setError('Passwords do not match'); return; }
    setLoading(true); setError('');
    try {
      await api.setPassword(email.trim(), password);
      // Auto-login after setting password
      const data = await api.login(email.trim(), password);
      await login(data.token, {
        email: data.email,
        name: data.name,
        department: data.department,
        designation: data.designation,
        superadmin: data.superadmin,
      });
    } catch (e: any) {
      setError(e.message || 'Failed to set password');
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.container}>
      <KeyboardAvoidingView
        style={{ flex: 1 }}
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      >
        <ScrollView contentContainerStyle={styles.scrollContent} keyboardShouldPersistTaps="handled">
          {/* Logo */}
          <View style={styles.logoSection}>
            <View style={styles.logoBox}>
              <Ionicons name="shield-checkmark" size={32} color={Colors.brandPrimary} />
            </View>
            <Text style={styles.logoText}>BMIA</Text>
            <Text style={styles.logoSub}>Bharat Market Intel Agent</Text>
          </View>

          {/* Employee Badge */}
          {employee && step !== 'email' && (
            <View style={styles.employeeBadge} testID="employee-badge">
              <Ionicons name="person-circle" size={20} color={Colors.positive} />
              <View style={{ flex: 1 }}>
                <Text style={styles.empName}>{employee.name}</Text>
                <Text style={styles.empRole}>{employee.designation} | {employee.department}</Text>
              </View>
            </View>
          )}

          {/* Step 1: Email */}
          {step === 'email' && (
            <View style={styles.formSection}>
              <Text style={styles.formTitle}>Enter your SMIFS email</Text>
              <View style={styles.inputRow}>
                <Ionicons name="mail-outline" size={18} color={Colors.textTertiary} style={styles.inputIcon} />
                <TextInput
                  testID="email-input"
                  style={styles.input}
                  placeholder="name@smifs.com"
                  placeholderTextColor={Colors.textTertiary}
                  value={email}
                  onChangeText={(t) => { setEmail(t); setError(''); }}
                  keyboardType="email-address"
                  autoCapitalize="none"
                  autoComplete="email"
                  returnKeyType="go"
                  onSubmitEditing={handleEmailCheck}
                />
              </View>
              <TouchableOpacity
                testID="email-continue-btn"
                style={[styles.primaryBtn, loading && styles.btnDisabled]}
                onPress={handleEmailCheck}
                disabled={loading}
              >
                {loading ? (
                  <ActivityIndicator size="small" color="#fff" />
                ) : (
                  <Ionicons name="arrow-forward" size={18} color="#fff" />
                )}
                <Text style={styles.primaryBtnText}>{loading ? 'Verifying...' : 'Continue'}</Text>
              </TouchableOpacity>
              <View style={styles.orgLensRow}>
                <Ionicons name="shield-checkmark" size={12} color={Colors.textTertiary} />
                <Text style={styles.orgLensText}>Verified via OrgLens employee directory</Text>
              </View>
            </View>
          )}

          {/* Step 2a: Login with password */}
          {step === 'password' && (
            <View style={styles.formSection}>
              <Text style={styles.formTitle}>Enter your password</Text>
              <View style={styles.inputRow}>
                <Ionicons name="lock-closed-outline" size={18} color={Colors.textTertiary} style={styles.inputIcon} />
                <TextInput
                  ref={pwRef}
                  testID="password-input"
                  style={styles.input}
                  placeholder="Password"
                  placeholderTextColor={Colors.textTertiary}
                  value={password}
                  onChangeText={(t) => { setPassword(t); setError(''); }}
                  secureTextEntry
                  autoComplete="password"
                  returnKeyType="go"
                  onSubmitEditing={handleLogin}
                />
              </View>
              <TouchableOpacity
                testID="login-btn"
                style={[styles.primaryBtn, loading && styles.btnDisabled]}
                onPress={handleLogin}
                disabled={loading}
              >
                {loading ? (
                  <ActivityIndicator size="small" color="#fff" />
                ) : (
                  <Ionicons name="log-in" size={18} color="#fff" />
                )}
                <Text style={styles.primaryBtnText}>{loading ? 'Signing in...' : 'Sign In'}</Text>
              </TouchableOpacity>
              <TouchableOpacity
                testID="back-to-email-btn"
                onPress={() => { setStep('email'); setPassword(''); setError(''); }}
              >
                <Text style={styles.linkText}>Use a different email</Text>
              </TouchableOpacity>
            </View>
          )}

          {/* Step 2b: Set new password */}
          {step === 'set-password' && (
            <View style={styles.formSection}>
              <Text style={styles.formTitle}>Create your password</Text>
              <Text style={styles.formSub}>First time? Set a password to access BMIA.</Text>
              <View style={styles.inputRow}>
                <Ionicons name="lock-closed-outline" size={18} color={Colors.textTertiary} style={styles.inputIcon} />
                <TextInput
                  ref={pwRef}
                  testID="new-password-input"
                  style={styles.input}
                  placeholder="New password (min 6 chars)"
                  placeholderTextColor={Colors.textTertiary}
                  value={password}
                  onChangeText={(t) => { setPassword(t); setError(''); }}
                  secureTextEntry
                  autoComplete="new-password"
                />
              </View>
              <View style={[styles.inputRow, { marginTop: 8 }]}>
                <Ionicons name="lock-closed-outline" size={18} color={Colors.textTertiary} style={styles.inputIcon} />
                <TextInput
                  testID="confirm-password-input"
                  style={styles.input}
                  placeholder="Confirm password"
                  placeholderTextColor={Colors.textTertiary}
                  value={confirmPw}
                  onChangeText={(t) => { setConfirmPw(t); setError(''); }}
                  secureTextEntry
                  autoComplete="new-password"
                  returnKeyType="go"
                  onSubmitEditing={handleSetPassword}
                />
              </View>
              <TouchableOpacity
                testID="set-password-btn"
                style={[styles.primaryBtn, loading && styles.btnDisabled]}
                onPress={handleSetPassword}
                disabled={loading}
              >
                {loading ? (
                  <ActivityIndicator size="small" color="#fff" />
                ) : (
                  <Ionicons name="checkmark-circle" size={18} color="#fff" />
                )}
                <Text style={styles.primaryBtnText}>{loading ? 'Setting up...' : 'Set Password & Sign In'}</Text>
              </TouchableOpacity>
              <TouchableOpacity
                testID="back-to-email-btn-2"
                onPress={() => { setStep('email'); setPassword(''); setConfirmPw(''); setError(''); }}
              >
                <Text style={styles.linkText}>Use a different email</Text>
              </TouchableOpacity>
            </View>
          )}

          {/* Error */}
          {error ? (
            <View style={styles.errorBox}>
              <Ionicons name="alert-circle" size={16} color={Colors.negative} />
              <Text style={styles.errorText}>{error}</Text>
            </View>
          ) : null}

          <Text style={styles.footer}>BMIA | Secured via OrgLens Employee Verification</Text>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.background },
  scrollContent: { flexGrow: 1, justifyContent: 'center', padding: Spacing.section },
  logoSection: { alignItems: 'center', marginBottom: 32 },
  logoBox: {
    width: 64, height: 64, borderRadius: 16,
    backgroundColor: 'rgba(59,130,246,0.12)', justifyContent: 'center', alignItems: 'center',
  },
  logoText: { color: Colors.brandPrimary, fontSize: 28, fontWeight: '900', letterSpacing: 3, marginTop: 12 },
  logoSub: { color: Colors.textTertiary, fontSize: FontSize.small, marginTop: 4, letterSpacing: 0.5 },
  employeeBadge: {
    flexDirection: 'row', alignItems: 'center', gap: 10,
    backgroundColor: 'rgba(16,185,129,0.08)', borderWidth: 1, borderColor: 'rgba(16,185,129,0.2)',
    borderRadius: 8, padding: 12, marginBottom: 16,
  },
  empName: { color: Colors.textPrimary, fontSize: FontSize.body, fontWeight: '700' },
  empRole: { color: Colors.textTertiary, fontSize: FontSize.tiny, marginTop: 2 },
  formSection: { marginBottom: 16 },
  formTitle: { color: Colors.textPrimary, fontSize: FontSize.bodyLarge, fontWeight: '600', marginBottom: 12 },
  formSub: { color: Colors.textTertiary, fontSize: FontSize.small, marginBottom: 12 },
  inputRow: {
    flexDirection: 'row', alignItems: 'center',
    backgroundColor: Colors.surface, borderWidth: 1, borderColor: Colors.border,
    borderRadius: 8, paddingHorizontal: 12,
  },
  inputIcon: { marginRight: 8 },
  input: {
    flex: 1, color: Colors.textPrimary, fontSize: FontSize.body,
    paddingVertical: 14,
  },
  primaryBtn: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8,
    backgroundColor: Colors.brandPrimary, borderRadius: 8, paddingVertical: 14, marginTop: 16,
  },
  btnDisabled: { opacity: 0.6 },
  primaryBtnText: { color: '#fff', fontSize: FontSize.body, fontWeight: '700' },
  orgLensRow: { flexDirection: 'row', alignItems: 'center', gap: 6, justifyContent: 'center', marginTop: 12 },
  orgLensText: { color: Colors.textTertiary, fontSize: FontSize.tiny },
  linkText: { color: Colors.textTertiary, fontSize: FontSize.small, textAlign: 'center', marginTop: 12 },
  errorBox: {
    flexDirection: 'row', alignItems: 'center', gap: 8,
    backgroundColor: 'rgba(239,68,68,0.1)', padding: 12, borderRadius: 8, marginTop: 12,
  },
  errorText: { color: Colors.negative, fontSize: FontSize.small, flex: 1 },
  footer: { color: Colors.textTertiary, fontSize: FontSize.tiny, textAlign: 'center', marginTop: 32 },
});
