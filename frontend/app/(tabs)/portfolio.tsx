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
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const router = useRouter();

  const loadData = useCallback(async () => {
    try {
      const result = await api.portfolios();
      setPortfolios(result?.portfolios || []);
    } catch (e) {
      console.error('Portfolio fetch error:', e);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);
  const onRefresh = () => { setRefreshing(true); loadData(); };

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

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Portfolios</Text>
      </View>

      <ScrollView
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={Colors.brandPrimary} />}
        contentContainerStyle={styles.scrollContent}
      >
        {portfolios.length === 0 ? (
          <View style={styles.empty}>
            <Ionicons name="briefcase-outline" size={48} color={Colors.textTertiary} />
            <Text style={styles.emptyText}>No portfolios found</Text>
          </View>
        ) : (
          portfolios.map((p: any) => {
            const pnlColor = (p.total_pnl_pct || 0) >= 0 ? Colors.positive : Colors.negative;
            const holdingsCount = p.holdings?.length || 0;
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
                    <Ionicons
                      name={p.type === 'swing' ? 'swap-horizontal' : p.type === 'quick_entry' ? 'rocket' : p.type === 'alpha_generator' ? 'diamond' : 'cash'}
                      size={20}
                      color={Colors.brandPrimary}
                    />
                  </View>
                  <View style={{ flex: 1 }}>
                    <Text style={styles.portfolioName}>{p.name}</Text>
                    <Text style={styles.portfolioDesc} numberOfLines={1}>{p.description}</Text>
                  </View>
                  <Ionicons name="chevron-forward" size={18} color={Colors.textTertiary} />
                </View>

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

                <View style={styles.holdingsRow}>
                  <Text style={styles.holdingsLabel}>{holdingsCount} Holdings</Text>
                  <Text style={styles.horizonLabel}>{p.horizon}</Text>
                </View>

                {/* Holdings preview */}
                <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.holdingsPreview}>
                  {(p.holdings || []).slice(0, 5).map((h: any) => (
                    <View key={h.symbol} style={styles.holdingChip}>
                      <Text style={styles.holdingSymbol}>{h.symbol?.replace('.NS', '')}</Text>
                      <Text style={[styles.holdingPnl, { color: h.pnl_pct >= 0 ? Colors.positive : Colors.negative }]}>
                        {h.pnl_pct >= 0 ? '+' : ''}{h.pnl_pct?.toFixed(1)}%
                      </Text>
                    </View>
                  ))}
                </ScrollView>
              </TouchableOpacity>
            );
          })
        )}

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
    paddingHorizontal: Spacing.base, paddingVertical: 12,
    borderBottomWidth: 1, borderBottomColor: Colors.border,
  },
  headerTitle: { color: Colors.textPrimary, fontSize: FontSize.h3, fontWeight: '700' },
  scrollContent: { padding: Spacing.base },
  empty: { alignItems: 'center', marginTop: 60 },
  emptyText: { color: Colors.textTertiary, fontSize: FontSize.body, marginTop: 12 },
  portfolioCard: {
    backgroundColor: Colors.surface, borderRadius: 8, borderWidth: 1, borderColor: Colors.border,
    padding: 14, marginBottom: 12,
  },
  cardHeader: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  cardIcon: {
    width: 40, height: 40, borderRadius: 8, backgroundColor: 'rgba(59,130,246,0.12)',
    justifyContent: 'center', alignItems: 'center',
  },
  portfolioName: { color: Colors.textPrimary, fontSize: FontSize.bodyLarge, fontWeight: '700' },
  portfolioDesc: { color: Colors.textTertiary, fontSize: FontSize.small, marginTop: 2 },
  statsRow: { flexDirection: 'row', marginTop: 14, gap: 8 },
  statCol: { flex: 1 },
  statLabel: { color: Colors.textTertiary, fontSize: FontSize.tiny, fontWeight: '700', letterSpacing: 0.5, marginBottom: 2 },
  statValue: { color: Colors.textPrimary, fontSize: FontSize.bodyLarge, fontWeight: '700', fontVariant: ['tabular-nums'] },
  holdingsRow: {
    flexDirection: 'row', justifyContent: 'space-between',
    marginTop: 12, paddingTop: 10, borderTopWidth: 1, borderTopColor: Colors.border,
  },
  holdingsLabel: { color: Colors.textSecondary, fontSize: FontSize.small, fontWeight: '600' },
  horizonLabel: { color: Colors.textTertiary, fontSize: FontSize.small },
  holdingsPreview: { marginTop: 8 },
  holdingChip: {
    backgroundColor: Colors.surfaceElevated, paddingHorizontal: 10, paddingVertical: 6,
    borderRadius: 6, marginRight: 6, alignItems: 'center',
  },
  holdingSymbol: { color: Colors.textPrimary, fontSize: FontSize.tiny, fontWeight: '700', letterSpacing: 0.5 },
  holdingPnl: { fontSize: FontSize.tiny, fontWeight: '600', marginTop: 2, fontVariant: ['tabular-nums'] },
});
