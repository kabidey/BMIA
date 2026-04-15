import React, { useEffect, useState } from 'react';
import {
  View, Text, ScrollView, StyleSheet, TouchableOpacity, ActivityIndicator,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { api } from '../src/api/client';
import { Colors, Spacing, FontSize } from '../src/constants/theme';

export default function PortfolioDetailScreen() {
  const router = useRouter();
  const { type } = useLocalSearchParams<{ type: string }>();
  const [portfolio, setPortfolio] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const result = await api.portfolios();
        const found = (result?.portfolios || []).find((p: any) => p.type === type);
        setPortfolio(found);
      } catch (e) { console.error(e); }
      finally { setLoading(false); }
    })();
  }, [type]);

  if (loading) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.centered}>
          <ActivityIndicator size="large" color={Colors.brandPrimary} />
        </View>
      </SafeAreaView>
    );
  }

  if (!portfolio) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.header}>
          <TouchableOpacity onPress={() => router.back()}>
            <Ionicons name="arrow-back" size={24} color={Colors.textPrimary} />
          </TouchableOpacity>
          <Text style={styles.headerTitle}>Portfolio Not Found</Text>
          <View style={{ width: 24 }} />
        </View>
      </SafeAreaView>
    );
  }

  const holdings = portfolio.holdings || [];
  const pnlColor = portfolio.total_pnl_pct >= 0 ? Colors.positive : Colors.negative;

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <View style={styles.header}>
        <TouchableOpacity testID="portfolio-detail-back" onPress={() => router.back()}>
          <Ionicons name="arrow-back" size={24} color={Colors.textPrimary} />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>{portfolio.name}</Text>
        <View style={{ width: 24 }} />
      </View>

      <ScrollView contentContainerStyle={styles.scrollContent}>
        {/* Summary */}
        <View style={styles.summaryCard}>
          <View style={styles.summaryRow}>
            <View style={styles.sumCol}>
              <Text style={styles.sumLabel}>INVESTED</Text>
              <Text style={styles.sumValue}>₹{(portfolio.actual_invested / 100000).toFixed(1)}L</Text>
            </View>
            <View style={styles.sumCol}>
              <Text style={styles.sumLabel}>CURRENT</Text>
              <Text style={styles.sumValue}>₹{(portfolio.current_value / 100000).toFixed(1)}L</Text>
            </View>
            <View style={styles.sumCol}>
              <Text style={styles.sumLabel}>P&L</Text>
              <Text style={[styles.sumValue, { color: pnlColor }]}>
                {portfolio.total_pnl_pct >= 0 ? '+' : ''}{portfolio.total_pnl_pct?.toFixed(2)}%
              </Text>
            </View>
          </View>
          <Text style={styles.thesis} numberOfLines={4}>{portfolio.portfolio_thesis}</Text>
        </View>

        {/* Holdings */}
        <Text style={styles.sectionTitle}>HOLDINGS ({holdings.length})</Text>
        {holdings.map((h: any) => {
          const sym = h.symbol?.replace('.NS', '') || 'N/A';
          const hpnlColor = h.pnl_pct >= 0 ? Colors.positive : Colors.negative;
          return (
            <TouchableOpacity
              key={h.symbol}
              style={styles.holdingCard}
              testID={`holding-card-${sym}`}
              onPress={() => router.push({ pathname: '/analysis', params: { symbol: h.symbol } })}
              activeOpacity={0.7}
            >
              <View style={styles.holdingHeader}>
                <View style={{ flex: 1 }}>
                  <Text style={styles.holdingSym}>{sym}</Text>
                  <Text style={styles.holdingName} numberOfLines={1}>{h.name}</Text>
                </View>
                <View style={styles.holdingPnlCol}>
                  <Text style={[styles.holdingPnl, { color: hpnlColor }]}>
                    {h.pnl_pct >= 0 ? '+' : ''}{h.pnl_pct?.toFixed(2)}%
                  </Text>
                  <Text style={styles.holdingSector}>{h.sector}</Text>
                </View>
              </View>
              <View style={styles.holdingMeta}>
                <Text style={styles.metaItem}>Entry: ₹{h.entry_price?.toFixed(1)}</Text>
                <Text style={styles.metaItem}>CMP: ₹{h.current_price?.toFixed(1)}</Text>
                <Text style={styles.metaItem}>Wt: {h.weight}%</Text>
                <View style={[styles.convictionPill, {
                  backgroundColor: h.conviction === 'HIGH' ? 'rgba(16,185,129,0.15)' : 'rgba(245,158,11,0.15)'
                }]}>
                  <Text style={[styles.convictionText, {
                    color: h.conviction === 'HIGH' ? Colors.positive : Colors.warning
                  }]}>{h.conviction}</Text>
                </View>
              </View>
              {h.rationale && <Text style={styles.rationale} numberOfLines={2}>{h.rationale}</Text>}
            </TouchableOpacity>
          );
        })}

        {/* Risk */}
        {portfolio.risk_assessment && (
          <View style={styles.riskCard}>
            <Ionicons name="warning" size={16} color={Colors.warning} />
            <View style={{ flex: 1 }}>
              <Text style={styles.riskLabel}>RISK ASSESSMENT</Text>
              <Text style={styles.riskText}>{portfolio.risk_assessment}</Text>
            </View>
          </View>
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
  summaryCard: {
    backgroundColor: Colors.surface, borderRadius: 8, borderWidth: 1, borderColor: Colors.border, padding: 14,
  },
  summaryRow: { flexDirection: 'row', gap: 8 },
  sumCol: { flex: 1 },
  sumLabel: { color: Colors.textTertiary, fontSize: FontSize.tiny, fontWeight: '700', letterSpacing: 0.5, marginBottom: 2 },
  sumValue: { color: Colors.textPrimary, fontSize: FontSize.h4, fontWeight: '700', fontVariant: ['tabular-nums'] },
  thesis: { color: Colors.textSecondary, fontSize: FontSize.small, lineHeight: 18, marginTop: 12 },
  sectionTitle: {
    color: Colors.textTertiary, fontSize: FontSize.tiny, fontWeight: '700',
    letterSpacing: 1.5, marginTop: Spacing.section, marginBottom: Spacing.small,
  },
  holdingCard: {
    backgroundColor: Colors.surface, borderRadius: 8, borderWidth: 1, borderColor: Colors.border,
    padding: 12, marginBottom: 8,
  },
  holdingHeader: { flexDirection: 'row', alignItems: 'flex-start' },
  holdingSym: { color: Colors.textPrimary, fontSize: FontSize.bodyLarge, fontWeight: '800', letterSpacing: 1 },
  holdingName: { color: Colors.textTertiary, fontSize: FontSize.small, marginTop: 2 },
  holdingPnlCol: { alignItems: 'flex-end' },
  holdingPnl: { fontSize: FontSize.bodyLarge, fontWeight: '700', fontVariant: ['tabular-nums'] },
  holdingSector: { color: Colors.textTertiary, fontSize: FontSize.tiny, marginTop: 2 },
  holdingMeta: { flexDirection: 'row', gap: 8, marginTop: 8, flexWrap: 'wrap', alignItems: 'center' },
  metaItem: { color: Colors.textTertiary, fontSize: FontSize.tiny, fontWeight: '600', fontVariant: ['tabular-nums'] },
  convictionPill: { paddingHorizontal: 6, paddingVertical: 2, borderRadius: 3 },
  convictionText: { fontSize: FontSize.tiny, fontWeight: '800', letterSpacing: 0.5 },
  rationale: { color: Colors.textSecondary, fontSize: FontSize.small, lineHeight: 17, marginTop: 6 },
  riskCard: {
    flexDirection: 'row', gap: 10, backgroundColor: 'rgba(245,158,11,0.08)',
    padding: 12, borderRadius: 8, marginTop: Spacing.section,
  },
  riskLabel: { color: Colors.warning, fontSize: FontSize.tiny, fontWeight: '700', letterSpacing: 1, marginBottom: 4 },
  riskText: { color: Colors.textSecondary, fontSize: FontSize.small, lineHeight: 18 },
});
