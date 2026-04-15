import React, { useEffect, useState, useCallback } from 'react';
import {
  View, Text, ScrollView, StyleSheet, RefreshControl,
  TouchableOpacity, ActivityIndicator,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { api } from '../../src/api/client';
import { Colors, Spacing, FontSize } from '../../src/constants/theme';

export default function PortfolioScreen() {
  const [portfolios, setPortfolios] = useState<any[]>([]);
  const [walkForward, setWalkForward] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const router = useRouter();

  const loadData = useCallback(async () => {
    try {
      const [pRes, wfRes] = await Promise.all([
        api.portfolios().catch(() => ({ portfolios: [] })),
        fetch('https://bmia.pesmifs.com/api/portfolios/walk-forward').then(r => r.json()).catch(() => ({ records: [] })),
      ]);
      setPortfolios(pRes?.portfolios || []);
      setWalkForward(wfRes?.records || []);
    } catch (e) { console.error('Portfolio fetch error:', e); }
    finally { setLoading(false); setRefreshing(false); }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);
  const onRefresh = () => { setRefreshing(true); loadData(); };

  const getWF = (type: string) => walkForward.find(w => w.portfolio_type === type);

  if (loading) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.centered}>
          <ActivityIndicator size="large" color={Colors.brandPrimary} />
          <Text style={styles.loadingText}>Loading Portfolios...</Text>
        </View>
      </SafeAreaView>
    );
  }

  // Aggregate stats
  const totalInvested = portfolios.reduce((s, p) => s + (p.actual_invested || 0), 0);
  const totalCurrent = portfolios.reduce((s, p) => s + (p.current_value || 0), 0);
  const totalPnl = totalCurrent - totalInvested;
  const totalPnlPct = totalInvested > 0 ? (totalPnl / totalInvested) * 100 : 0;
  const totalHoldings = portfolios.reduce((s, p) => s + (p.holdings?.length || 0), 0);

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Portfolios</Text>
        <Text style={styles.headerCount}>{portfolios.length} Strategies</Text>
      </View>

      <ScrollView
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={Colors.brandPrimary} />}
        contentContainerStyle={styles.scrollContent}
      >
        {/* Aggregate Summary */}
        <View style={styles.summaryCard}>
          <Text style={styles.summaryLabel}>TOTAL PORTFOLIO VALUE</Text>
          <Text style={styles.summaryValue}>₹{(totalCurrent / 100000).toFixed(1)}L</Text>
          <View style={styles.summaryRow}>
            <View style={styles.sumCol}>
              <Text style={styles.sumStatLabel}>Invested</Text>
              <Text style={styles.sumStatVal}>₹{(totalInvested / 100000).toFixed(1)}L</Text>
            </View>
            <View style={styles.sumCol}>
              <Text style={styles.sumStatLabel}>P&L</Text>
              <Text style={[styles.sumStatVal, { color: totalPnlPct >= 0 ? Colors.positive : Colors.negative }]}>
                {totalPnlPct >= 0 ? '+' : ''}{totalPnlPct.toFixed(2)}%
              </Text>
            </View>
            <View style={styles.sumCol}>
              <Text style={styles.sumStatLabel}>Holdings</Text>
              <Text style={styles.sumStatVal}>{totalHoldings}</Text>
            </View>
          </View>
        </View>

        {/* Portfolio Cards */}
        {portfolios.map((p: any) => {
          const pnlColor = (p.total_pnl_pct || 0) >= 0 ? Colors.positive : Colors.negative;
          const wf = getWF(p.type);
          const holdingsCount = p.holdings?.length || 0;
          const iconMap: Record<string, string> = {
            swing: 'swap-horizontal', quick_entry: 'rocket', alpha_generator: 'diamond',
            value_stocks: 'cash', long_term: 'time', bespoke_forward_looking: 'telescope',
          };

          return (
            <TouchableOpacity
              key={p.type}
              style={styles.portfolioCard}
              testID={`portfolio-card-${p.type}`}
              onPress={() => router.push({ pathname: '/portfolio-detail', params: { type: p.type } })}
              activeOpacity={0.7}
            >
              <View style={styles.cardHeader}>
                <View style={styles.cardIcon}>
                  <Ionicons name={(iconMap[p.type] || 'briefcase') as any} size={20} color={Colors.brandPrimary} />
                </View>
                <View style={{ flex: 1 }}>
                  <Text style={styles.portfolioName}>{p.name}</Text>
                  <Text style={styles.portfolioDesc} numberOfLines={1}>{p.description}</Text>
                </View>
                <Ionicons name="chevron-forward" size={18} color={Colors.textTertiary} />
              </View>

              {/* Stats */}
              <View style={styles.statsRow}>
                <View style={styles.statCol}>
                  <Text style={styles.statLabel}>INVESTED</Text>
                  <Text style={styles.statValue}>₹{(p.actual_invested / 100000).toFixed(1)}L</Text>
                </View>
                <View style={styles.statCol}>
                  <Text style={styles.statLabel}>CURRENT</Text>
                  <Text style={styles.statValue}>₹{(p.current_value / 100000).toFixed(1)}L</Text>
                </View>
                <View style={styles.statCol}>
                  <Text style={styles.statLabel}>P&L</Text>
                  <Text style={[styles.statValue, { color: pnlColor }]}>
                    {p.total_pnl_pct >= 0 ? '+' : ''}{p.total_pnl_pct?.toFixed(2)}%
                  </Text>
                </View>
              </View>

              {/* Walk-Forward Simulation */}
              {wf?.forecast && (
                <View style={styles.simSection}>
                  <Text style={styles.simTitle}>
                    <Ionicons name="analytics" size={12} color={Colors.brandPrimary} /> SIMULATION FORECAST
                  </Text>
                  <View style={styles.simGrid}>
                    <View style={styles.simItem}>
                      <Text style={styles.simLabel}>Expected</Text>
                      <Text style={[styles.simVal, { color: wf.forecast.expected_return_pct >= 0 ? Colors.positive : Colors.negative }]}>
                        {wf.forecast.expected_return_pct >= 0 ? '+' : ''}{wf.forecast.expected_return_pct?.toFixed(1)}%
                      </Text>
                    </View>
                    <View style={styles.simItem}>
                      <Text style={styles.simLabel}>Median</Text>
                      <Text style={[styles.simVal, { color: wf.forecast.median_return_pct >= 0 ? Colors.positive : Colors.negative }]}>
                        {wf.forecast.median_return_pct >= 0 ? '+' : ''}{wf.forecast.median_return_pct?.toFixed(1)}%
                      </Text>
                    </View>
                    <View style={styles.simItem}>
                      <Text style={styles.simLabel}>VaR 95%</Text>
                      <Text style={[styles.simVal, { color: Colors.negative }]}>{wf.forecast.var_95_pct?.toFixed(1)}%</Text>
                    </View>
                    <View style={styles.simItem}>
                      <Text style={styles.simLabel}>P(Profit)</Text>
                      <Text style={[styles.simVal, { color: wf.forecast.probability_of_profit_pct >= 50 ? Colors.positive : Colors.negative }]}>
                        {wf.forecast.probability_of_profit_pct?.toFixed(0)}%
                      </Text>
                    </View>
                  </View>
                  {wf.forecast.lstm_annualized_return_pct != null && (
                    <View style={styles.lstmRow}>
                      <Text style={styles.lstmLabel}>LSTM Annual:</Text>
                      <Text style={[styles.lstmVal, { color: wf.forecast.lstm_annualized_return_pct >= 0 ? Colors.positive : Colors.negative }]}>
                        {wf.forecast.lstm_annualized_return_pct >= 0 ? '+' : ''}{wf.forecast.lstm_annualized_return_pct?.toFixed(1)}%
                      </Text>
                      <Text style={styles.lstmLabel}>Vol:</Text>
                      <Text style={styles.lstmVal}>{wf.forecast.lstm_annualized_vol_pct?.toFixed(1)}%</Text>
                    </View>
                  )}
                </View>
              )}

              {/* Construction Pipeline */}
              {p.construction_log && (
                <View style={styles.pipelineRow}>
                  <Ionicons name="git-branch" size={12} color={Colors.textTertiary} />
                  <Text style={styles.pipelineText}>
                    {p.construction_log.universe_size} universe → {p.construction_log.screened_candidates} screened → {p.construction_log.deep_enriched} enriched → {holdingsCount} selected
                  </Text>
                </View>
              )}

              {/* Holdings preview */}
              <View style={styles.holdingsRow}>
                <Text style={styles.holdingsLabel}>{holdingsCount} Holdings</Text>
                <Text style={styles.horizonLabel}>{p.horizon}</Text>
              </View>
              <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.holdingsPreview}>
                {(p.holdings || []).slice(0, 6).map((h: any) => (
                  <View key={h.symbol} style={styles.holdingChip}>
                    <Text style={styles.holdingSymbol}>{h.symbol?.replace('.NS', '')}</Text>
                    <Text style={[styles.holdingPnl, { color: h.pnl_pct >= 0 ? Colors.positive : Colors.negative }]}>
                      {h.pnl_pct >= 0 ? '+' : ''}{h.pnl_pct?.toFixed(1)}%
                    </Text>
                    <View style={[styles.gradeDot, {
                      backgroundColor: h.fundamental_grade === 'A' ? Colors.positive : h.fundamental_grade === 'B' ? Colors.warning : Colors.textTertiary,
                    }]} />
                  </View>
                ))}
              </ScrollView>
            </TouchableOpacity>
          );
        })}

        <View style={styles.disclaimer}>
          <Ionicons name="shield-checkmark" size={14} color={Colors.brandPrimary} />
          <Text style={styles.disclaimerText}>AI-constructed portfolios for educational purposes. Not investment advice. Always consult a SEBI-registered advisor.</Text>
        </View>
        <View style={{ height: 32 }} />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.background },
  centered: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  loadingText: { color: Colors.textSecondary, marginTop: 12, fontSize: FontSize.body },
  header: {
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    paddingHorizontal: Spacing.base, paddingVertical: 12, borderBottomWidth: 1, borderBottomColor: Colors.border,
  },
  headerTitle: { color: Colors.textPrimary, fontSize: FontSize.h3, fontWeight: '700' },
  headerCount: { color: Colors.brandPrimary, fontSize: FontSize.small, fontWeight: '600' },
  scrollContent: { padding: Spacing.base },
  summaryCard: {
    backgroundColor: Colors.surface, borderRadius: 8, borderWidth: 1, borderColor: Colors.brandPrimary + '40',
    padding: 14, marginBottom: 16,
  },
  summaryLabel: { color: Colors.textTertiary, fontSize: FontSize.tiny, fontWeight: '700', letterSpacing: 1 },
  summaryValue: { color: Colors.textPrimary, fontSize: FontSize.priceMedium, fontWeight: '800', fontVariant: ['tabular-nums'], marginTop: 4 },
  summaryRow: { flexDirection: 'row', marginTop: 12, gap: 8 },
  sumCol: { flex: 1 },
  sumStatLabel: { color: Colors.textTertiary, fontSize: FontSize.tiny, fontWeight: '600' },
  sumStatVal: { color: Colors.textPrimary, fontSize: FontSize.body, fontWeight: '700', fontVariant: ['tabular-nums'], marginTop: 2 },
  portfolioCard: {
    backgroundColor: Colors.surface, borderRadius: 8, borderWidth: 1, borderColor: Colors.border, padding: 14, marginBottom: 12,
  },
  cardHeader: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  cardIcon: { width: 40, height: 40, borderRadius: 8, backgroundColor: 'rgba(59,130,246,0.12)', justifyContent: 'center', alignItems: 'center' },
  portfolioName: { color: Colors.textPrimary, fontSize: FontSize.bodyLarge, fontWeight: '700' },
  portfolioDesc: { color: Colors.textTertiary, fontSize: FontSize.small, marginTop: 2 },
  statsRow: { flexDirection: 'row', marginTop: 12, gap: 8 },
  statCol: { flex: 1 },
  statLabel: { color: Colors.textTertiary, fontSize: FontSize.tiny, fontWeight: '700', letterSpacing: 0.5, marginBottom: 2 },
  statValue: { color: Colors.textPrimary, fontSize: FontSize.bodyLarge, fontWeight: '700', fontVariant: ['tabular-nums'] },
  simSection: {
    marginTop: 10, paddingTop: 10, borderTopWidth: 1, borderTopColor: Colors.border,
    backgroundColor: 'rgba(59,130,246,0.04)', borderRadius: 6, padding: 10, marginHorizontal: -2,
  },
  simTitle: { color: Colors.brandPrimary, fontSize: FontSize.tiny, fontWeight: '700', letterSpacing: 1, marginBottom: 8 },
  simGrid: { flexDirection: 'row', gap: 4 },
  simItem: { flex: 1 },
  simLabel: { color: Colors.textTertiary, fontSize: 9, fontWeight: '600' },
  simVal: { color: Colors.textPrimary, fontSize: FontSize.small, fontWeight: '700', fontVariant: ['tabular-nums'], marginTop: 1 },
  lstmRow: { flexDirection: 'row', alignItems: 'center', gap: 4, marginTop: 6 },
  lstmLabel: { color: Colors.textTertiary, fontSize: 9, fontWeight: '600' },
  lstmVal: { color: Colors.textPrimary, fontSize: FontSize.small, fontWeight: '700', fontVariant: ['tabular-nums'] },
  pipelineRow: { flexDirection: 'row', alignItems: 'center', gap: 6, marginTop: 8 },
  pipelineText: { color: Colors.textTertiary, fontSize: FontSize.tiny, fontWeight: '500' },
  holdingsRow: { flexDirection: 'row', justifyContent: 'space-between', marginTop: 10, paddingTop: 8, borderTopWidth: 1, borderTopColor: Colors.border },
  holdingsLabel: { color: Colors.textSecondary, fontSize: FontSize.small, fontWeight: '600' },
  horizonLabel: { color: Colors.textTertiary, fontSize: FontSize.small },
  holdingsPreview: { marginTop: 8 },
  holdingChip: { backgroundColor: Colors.surfaceElevated, paddingHorizontal: 10, paddingVertical: 6, borderRadius: 6, marginRight: 6, alignItems: 'center' },
  holdingSymbol: { color: Colors.textPrimary, fontSize: FontSize.tiny, fontWeight: '700', letterSpacing: 0.5 },
  holdingPnl: { fontSize: FontSize.tiny, fontWeight: '600', marginTop: 2, fontVariant: ['tabular-nums'] },
  gradeDot: { width: 6, height: 6, borderRadius: 3, marginTop: 3 },
  disclaimer: { flexDirection: 'row', alignItems: 'flex-start', gap: 6, backgroundColor: 'rgba(59,130,246,0.06)', padding: 10, borderRadius: 6, marginTop: 16 },
  disclaimerText: { color: Colors.textTertiary, fontSize: FontSize.tiny, flex: 1, lineHeight: 14 },
});
