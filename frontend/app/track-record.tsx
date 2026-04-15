import React, { useEffect, useState } from 'react';
import {
  View, Text, ScrollView, StyleSheet, TouchableOpacity, ActivityIndicator, RefreshControl,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { api } from '../src/api/client';
import { Colors, Spacing, FontSize } from '../src/constants/theme';

export default function TrackRecordScreen() {
  const router = useRouter();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const result = await api.trackRecord();
        setData(result);
      } catch (e) { console.error(e); }
      finally { setLoading(false); }
    })();
  }, []);

  if (loading) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.centered}>
          <ActivityIndicator size="large" color={Colors.brandPrimary} />
        </View>
      </SafeAreaView>
    );
  }

  const m = data?.metrics || {};
  const equityCurve = data?.equity_curve || [];
  const byAction = data?.by_action || {};
  const bySector = data?.by_sector || {};

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <View style={styles.header}>
        <TouchableOpacity testID="track-record-back" onPress={() => router.back()}>
          <Ionicons name="arrow-back" size={24} color={Colors.textPrimary} />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Track Record</Text>
        <View style={{ width: 24 }} />
      </View>

      <ScrollView contentContainerStyle={styles.scrollContent}>
        {/* Key Metrics Grid */}
        <View style={styles.metricsGrid}>
          {[
            { label: 'Win Rate', value: `${m.win_rate?.toFixed(1)}%`, color: m.win_rate >= 50 ? Colors.positive : Colors.negative },
            { label: 'Total Signals', value: `${data?.total_signals || 0}`, color: Colors.textPrimary },
            { label: 'Avg Return', value: `${m.avg_return?.toFixed(1)}%`, color: m.avg_return >= 0 ? Colors.positive : Colors.negative },
            { label: 'Profit Factor', value: `${m.profit_factor?.toFixed(2)}`, color: m.profit_factor >= 1 ? Colors.positive : Colors.negative },
            { label: 'Max Win', value: `${m.max_win?.toFixed(1)}%`, color: Colors.positive },
            { label: 'Max Loss', value: `${m.max_loss?.toFixed(1)}%`, color: Colors.negative },
            { label: 'Expectancy', value: `${m.expectancy?.toFixed(1)}%`, color: m.expectancy >= 0 ? Colors.positive : Colors.negative },
            { label: 'Open / Closed', value: `${data?.open_signals || 0} / ${data?.closed_signals || 0}`, color: Colors.textPrimary },
          ].map((item) => (
            <View key={item.label} style={styles.metricBox} testID={`metric-${item.label.toLowerCase().replace(/\s+/g, '-')}`}>
              <Text style={styles.metricLabel}>{item.label}</Text>
              <Text style={[styles.metricValue, { color: item.color }]}>{item.value}</Text>
            </View>
          ))}
        </View>

        {/* Equity Curve (simple text representation) */}
        {equityCurve.length > 0 && (
          <>
            <Text style={styles.sectionTitle}>EQUITY CURVE</Text>
            {equityCurve.map((e: any, i: number) => (
              <View key={i} style={styles.curveRow}>
                <Text style={styles.curveSym}>{e.symbol?.replace('.NS', '')}</Text>
                <Text style={styles.curveAction}>{e.action}</Text>
                <Text style={[styles.curveReturn, { color: e.return >= 0 ? Colors.positive : Colors.negative }]}>
                  {e.return >= 0 ? '+' : ''}{e.return?.toFixed(1)}%
                </Text>
                <Text style={[styles.curveCum, { color: e.cumulative >= 0 ? Colors.positive : Colors.negative }]}>
                  Σ {e.cumulative?.toFixed(1)}%
                </Text>
              </View>
            ))}
          </>
        )}

        {/* By Action */}
        {Object.keys(byAction).length > 0 && (
          <>
            <Text style={styles.sectionTitle}>BY ACTION</Text>
            {Object.entries(byAction).map(([action, stats]: [string, any]) => (
              <View key={action} style={styles.breakdownRow}>
                <Text style={styles.breakdownLabel}>{action}</Text>
                <Text style={styles.breakdownStat}>{stats.count} trades</Text>
                <Text style={[styles.breakdownStat, { color: stats.win_rate >= 50 ? Colors.positive : Colors.negative }]}>
                  WR: {stats.win_rate?.toFixed(0)}%
                </Text>
                <Text style={[styles.breakdownStat, { color: stats.avg_return >= 0 ? Colors.positive : Colors.negative }]}>
                  Avg: {stats.avg_return?.toFixed(1)}%
                </Text>
              </View>
            ))}
          </>
        )}

        {/* By Sector */}
        {Object.keys(bySector).length > 0 && (
          <>
            <Text style={styles.sectionTitle}>BY SECTOR</Text>
            {Object.entries(bySector).map(([sector, stats]: [string, any]) => (
              <View key={sector} style={styles.breakdownRow}>
                <Text style={[styles.breakdownLabel, { flex: 1 }]}>{sector}</Text>
                <Text style={styles.breakdownStat}>{stats.count}</Text>
                <Text style={[styles.breakdownStat, { color: stats.avg_return >= 0 ? Colors.positive : Colors.negative }]}>
                  {stats.avg_return >= 0 ? '+' : ''}{stats.avg_return?.toFixed(1)}%
                </Text>
              </View>
            ))}
          </>
        )}

        <View style={{ height: 32 }} />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.background },
  centered: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  header: {
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    paddingHorizontal: Spacing.base, paddingVertical: 12,
    borderBottomWidth: 1, borderBottomColor: Colors.border,
  },
  headerTitle: { color: Colors.textPrimary, fontSize: FontSize.h4, fontWeight: '700' },
  scrollContent: { padding: Spacing.base },
  metricsGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  metricBox: {
    width: '48%', backgroundColor: Colors.surface, borderRadius: 8,
    borderWidth: 1, borderColor: Colors.border, padding: 12,
  },
  metricLabel: { color: Colors.textTertiary, fontSize: FontSize.tiny, fontWeight: '700', letterSpacing: 0.5 },
  metricValue: { fontSize: FontSize.h4, fontWeight: '700', marginTop: 4, fontVariant: ['tabular-nums'] },
  sectionTitle: {
    color: Colors.textTertiary, fontSize: FontSize.tiny, fontWeight: '700',
    letterSpacing: 1.5, marginTop: Spacing.section, marginBottom: Spacing.small,
  },
  curveRow: {
    flexDirection: 'row', alignItems: 'center', gap: 8,
    paddingVertical: 8, borderBottomWidth: 1, borderBottomColor: 'rgba(39,39,42,0.5)',
  },
  curveSym: { color: Colors.textPrimary, fontSize: FontSize.small, fontWeight: '700', width: 80, letterSpacing: 0.5 },
  curveAction: { color: Colors.textTertiary, fontSize: FontSize.tiny, fontWeight: '600', width: 40 },
  curveReturn: { fontSize: FontSize.small, fontWeight: '600', fontVariant: ['tabular-nums'], width: 60, textAlign: 'right' },
  curveCum: { fontSize: FontSize.small, fontWeight: '600', fontVariant: ['tabular-nums'], flex: 1, textAlign: 'right' },
  breakdownRow: {
    flexDirection: 'row', alignItems: 'center', gap: 8,
    paddingVertical: 8, borderBottomWidth: 1, borderBottomColor: 'rgba(39,39,42,0.5)',
  },
  breakdownLabel: { color: Colors.textPrimary, fontSize: FontSize.small, fontWeight: '600', width: 80 },
  breakdownStat: { color: Colors.textSecondary, fontSize: FontSize.small, fontVariant: ['tabular-nums'], flex: 1, textAlign: 'right' },
});
