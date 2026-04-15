import React, { useEffect, useState } from 'react';
import {
  View, Text, ScrollView, StyleSheet, TouchableOpacity, ActivityIndicator,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { api } from '../src/api/client';
import { Colors, Spacing, FontSize } from '../src/constants/theme';

export default function AuditLogScreen() {
  const router = useRouter();
  const [logs, setLogs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    (async () => {
      try {
        const result = await api.auditLog();
        setLogs(result?.logs || []);
      } catch (e: any) {
        setError(e.message || 'Failed to load audit log');
      } finally { setLoading(false); }
    })();
  }, []);

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <View style={styles.header}>
        <TouchableOpacity testID="audit-log-back" onPress={() => router.back()}>
          <Ionicons name="arrow-back" size={24} color={Colors.textPrimary} />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Audit Log</Text>
        <View style={{ width: 24 }} />
      </View>

      <ScrollView contentContainerStyle={styles.scrollContent}>
        {loading && (
          <View style={styles.centered}>
            <ActivityIndicator size="large" color={Colors.brandPrimary} />
          </View>
        )}

        {error ? (
          <View style={styles.infoCard}>
            <Ionicons name="lock-closed" size={18} color={Colors.warning} />
            <Text style={styles.infoText}>{error}</Text>
          </View>
        ) : null}

        {!loading && logs.length === 0 && !error && (
          <View style={styles.empty}>
            <Ionicons name="document-text-outline" size={64} color={Colors.textTertiary} />
            <Text style={styles.emptyTitle}>No Audit Logs</Text>
            <Text style={styles.emptyDesc}>Activity logs will appear here as you use the platform.</Text>
          </View>
        )}

        {logs.map((log: any, i: number) => (
          <View key={i} style={styles.logItem} testID={`audit-log-item-${i}`}>
            <Text style={styles.logTime}>{log.timestamp || log.created_at}</Text>
            <Text style={styles.logAction}>{log.action || log.event}</Text>
            <Text style={styles.logDetail}>{log.detail || log.description || JSON.stringify(log)}</Text>
          </View>
        ))}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.background },
  centered: { flex: 1, justifyContent: 'center', alignItems: 'center', paddingTop: 40 },
  header: {
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    paddingHorizontal: Spacing.base, paddingVertical: 12,
    borderBottomWidth: 1, borderBottomColor: Colors.border,
  },
  headerTitle: { color: Colors.textPrimary, fontSize: FontSize.h4, fontWeight: '700' },
  scrollContent: { padding: Spacing.base },
  infoCard: {
    flexDirection: 'row', gap: 8, backgroundColor: 'rgba(245,158,11,0.1)',
    padding: 12, borderRadius: 8,
  },
  infoText: { color: Colors.warning, fontSize: FontSize.small, flex: 1 },
  empty: { alignItems: 'center', paddingTop: 60 },
  emptyTitle: { color: Colors.textPrimary, fontSize: FontSize.h3, fontWeight: '700', marginTop: 16 },
  emptyDesc: { color: Colors.textTertiary, fontSize: FontSize.body, marginTop: 8, textAlign: 'center' },
  logItem: {
    backgroundColor: Colors.surface, borderRadius: 8, borderWidth: 1, borderColor: Colors.border,
    padding: 12, marginBottom: 8,
  },
  logTime: { color: Colors.textTertiary, fontSize: FontSize.tiny, fontVariant: ['tabular-nums'] },
  logAction: { color: Colors.textPrimary, fontSize: FontSize.body, fontWeight: '600', marginTop: 4 },
  logDetail: { color: Colors.textSecondary, fontSize: FontSize.small, marginTop: 4 },
});
