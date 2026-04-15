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

function formatNum(n: number | null | undefined, decimals = 2): string {
  if (n == null || isNaN(n)) return '--';
  return n.toLocaleString('en-IN', { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
}

function formatCr(n: number): string {
  if (Math.abs(n) >= 10000000) return (n / 10000000).toFixed(1) + ' Cr';
  if (Math.abs(n) >= 100000) return (n / 100000).toFixed(1) + ' L';
  return formatNum(n, 0);
}

function PctBadge({ value }: { value: number }) {
  const isPos = value >= 0;
  return (
    <View style={[styles.badge, isPos ? styles.badgePos : styles.badgeNeg]}>
      <Text style={[styles.badgeText, { color: isPos ? Colors.positive : Colors.negative }]}>
        {isPos ? '+' : ''}{value.toFixed(2)}%
      </Text>
    </View>
  );
}

export default function MarketOverview() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const router = useRouter();

  const loadData = useCallback(async () => {
    try {
      const result = await api.cockpit();
      setData(result);
    } catch (e) {
      console.error('Cockpit fetch error:', e);
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
          <Text style={styles.loadingText}>Loading Market Data...</Text>
        </View>
      </SafeAreaView>
    );
  }

  const indices = data?.indices?.indices || [];
  const breadth = data?.breadth;
  const vix = data?.vix;
  const sectors = data?.sectors?.sectors || [];
  const pcr = data?.pcr;

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <View style={styles.header}>
        <View>
          <Text style={styles.headerTitle}>BMIA</Text>
          <Text style={styles.headerSubtitle}>Bharat Market Intel Agent</Text>
        </View>
        <TouchableOpacity testID="market-search-btn" onPress={() => router.push('/analysis')}>
          <Ionicons name="search" size={24} color={Colors.textSecondary} />
        </TouchableOpacity>
      </View>

      <ScrollView
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={Colors.brandPrimary} />}
        contentContainerStyle={styles.scrollContent}
      >
        {/* Key Indices */}
        <Text style={styles.sectionTitle}>KEY INDICES</Text>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.indicesScroll}>
          {indices.slice(0, 6).map((idx: any) => (
            <View key={idx.symbol} style={styles.indexCard} testID={`index-card-${idx.symbol}`}>
              <Text style={styles.indexName} numberOfLines={1}>{idx.name}</Text>
              <Text style={styles.indexPrice}>{formatNum(idx.last)}</Text>
              <View style={styles.indexChange}>
                <Ionicons
                  name={idx.change >= 0 ? 'arrow-up' : 'arrow-down'}
                  size={12}
                  color={idx.change >= 0 ? Colors.positive : Colors.negative}
                />
                <Text style={[styles.indexChangePct, { color: idx.change >= 0 ? Colors.positive : Colors.negative }]}>
                  {idx.change >= 0 ? '+' : ''}{idx.change_pct?.toFixed(2)}%
                </Text>
              </View>
            </View>
          ))}
        </ScrollView>

        {/* Market Breadth & VIX */}
        <View style={styles.row}>
          <View style={[styles.card, styles.halfCard]}>
            <Text style={styles.cardLabel}>MARKET BREADTH</Text>
            {breadth && (
              <>
                <View style={styles.breadthBar}>
                  <View style={[styles.breadthFill, { width: `${breadth.advance_pct}%`, backgroundColor: Colors.positive }]} />
                </View>
                <View style={styles.breadthLabels}>
                  <Text style={[styles.breadthVal, { color: Colors.positive }]}>
                    <Ionicons name="arrow-up" size={10} color={Colors.positive} /> {breadth.advances}
                  </Text>
                  <Text style={[styles.breadthVal, { color: Colors.negative }]}>
                    {breadth.declines} <Ionicons name="arrow-down" size={10} color={Colors.negative} />
                  </Text>
                </View>
                <Text style={styles.adRatio}>A/D: {breadth.ad_ratio?.toFixed(1)}</Text>
              </>
            )}
          </View>

          <View style={[styles.card, styles.halfCard]}>
            <Text style={styles.cardLabel}>INDIA VIX</Text>
            {vix && (
              <>
                <Text style={styles.vixValue}>{formatNum(vix.current)}</Text>
                <PctBadge value={vix.change_pct} />
                <View style={[styles.regimePill, {
                  backgroundColor: vix.regime === 'risk' ? 'rgba(239,68,68,0.15)' : vix.regime === 'caution' ? 'rgba(245,158,11,0.15)' : 'rgba(16,185,129,0.15)'
                }]}>
                  <Text style={[styles.regimeText, {
                    color: vix.regime === 'risk' ? Colors.negative : vix.regime === 'caution' ? Colors.warning : Colors.positive
                  }]}>{vix.regime_label}</Text>
                </View>
              </>
            )}
          </View>
        </View>

        {/* PCR */}
        {pcr && (
          <>
            <Text style={styles.sectionTitle}>PUT-CALL RATIO</Text>
            <View style={styles.row}>
              <View style={[styles.card, styles.halfCard]}>
                <Text style={styles.pcrLabel}>NIFTY PCR</Text>
                <Text style={styles.pcrValue}>{pcr.nifty?.pcr?.toFixed(2)}</Text>
                <Text style={[styles.pcrSentiment, {
                  color: pcr.nifty?.sentiment === 'bullish' ? Colors.positive : pcr.nifty?.sentiment === 'bearish' ? Colors.negative : Colors.warning
                }]}>{pcr.nifty?.label}</Text>
              </View>
              <View style={[styles.card, styles.halfCard]}>
                <Text style={styles.pcrLabel}>BANKNIFTY PCR</Text>
                <Text style={styles.pcrValue}>{pcr.banknifty?.pcr?.toFixed(2)}</Text>
                <Text style={[styles.pcrSentiment, {
                  color: pcr.banknifty?.sentiment === 'bullish' ? Colors.positive : pcr.banknifty?.sentiment === 'bearish' ? Colors.negative : Colors.warning
                }]}>{pcr.banknifty?.label}</Text>
              </View>
            </View>
          </>
        )}

        {/* Sector Rotation */}
        <Text style={styles.sectionTitle}>SECTOR ROTATION</Text>
        {sectors.map((s: any) => (
          <View key={s.name} style={styles.sectorRow} testID={`sector-row-${s.name}`}>
            <View style={styles.sectorLeft}>
              <Text style={styles.sectorName}>{s.name}</Text>
              <Text style={styles.sectorSub}>{s.advances}↑ {s.declines}↓</Text>
            </View>
            <View style={styles.sectorRight}>
              <Text style={[styles.sectorPct, { color: s.change_pct >= 0 ? Colors.positive : Colors.negative }]}>
                {s.change_pct >= 0 ? '+' : ''}{s.change_pct?.toFixed(2)}%
              </Text>
              <View style={styles.sectorBarBg}>
                <View style={[styles.sectorBarFill, {
                  width: `${Math.min(Math.abs(s.change_pct) * 20, 100)}%`,
                  backgroundColor: s.change_pct >= 0 ? Colors.positive : Colors.negative,
                }]} />
              </View>
            </View>
          </View>
        ))}

        {/* All Indices */}
        <Text style={styles.sectionTitle}>ALL INDICES</Text>
        {indices.map((idx: any) => (
          <View key={idx.symbol} style={styles.indexRow} testID={`all-index-${idx.symbol}`}>
            <View style={{ flex: 1 }}>
              <Text style={styles.indexRowName}>{idx.name}</Text>
            </View>
            <Text style={styles.indexRowPrice}>{formatNum(idx.last)}</Text>
            <PctBadge value={idx.change_pct} />
          </View>
        ))}

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
    paddingHorizontal: Spacing.base, paddingVertical: 12,
    borderBottomWidth: 1, borderBottomColor: Colors.border,
  },
  headerTitle: { color: Colors.brandPrimary, fontSize: FontSize.h2, fontWeight: '800', letterSpacing: 2 },
  headerSubtitle: { color: Colors.textTertiary, fontSize: FontSize.tiny, letterSpacing: 1, textTransform: 'uppercase' },
  scrollContent: { padding: Spacing.base },
  sectionTitle: {
    color: Colors.textTertiary, fontSize: FontSize.tiny, fontWeight: '700',
    letterSpacing: 1.5, marginTop: Spacing.section, marginBottom: Spacing.small,
    textTransform: 'uppercase',
  },
  indicesScroll: { marginHorizontal: -Spacing.base },
  indexCard: {
    backgroundColor: Colors.surface, borderRadius: 8, borderWidth: 1, borderColor: Colors.border,
    padding: 12, marginLeft: Spacing.base, width: 140,
  },
  indexName: { color: Colors.textSecondary, fontSize: FontSize.small, marginBottom: 4 },
  indexPrice: { color: Colors.textPrimary, fontSize: FontSize.h4, fontWeight: '700', fontVariant: ['tabular-nums'] },
  indexChange: { flexDirection: 'row', alignItems: 'center', marginTop: 4 },
  indexChangePct: { fontSize: FontSize.small, fontWeight: '600', marginLeft: 2, fontVariant: ['tabular-nums'] },
  row: { flexDirection: 'row', gap: Spacing.small },
  card: {
    backgroundColor: Colors.surface, borderRadius: 8, borderWidth: 1, borderColor: Colors.border,
    padding: 12, marginTop: Spacing.small,
  },
  halfCard: { flex: 1 },
  cardLabel: { color: Colors.textTertiary, fontSize: FontSize.tiny, fontWeight: '700', letterSpacing: 1, marginBottom: 8 },
  breadthBar: { height: 6, backgroundColor: Colors.surfaceElevated, borderRadius: 3, overflow: 'hidden' },
  breadthFill: { height: '100%', borderRadius: 3 },
  breadthLabels: { flexDirection: 'row', justifyContent: 'space-between', marginTop: 6 },
  breadthVal: { fontSize: FontSize.small, fontWeight: '600', fontVariant: ['tabular-nums'] },
  adRatio: { color: Colors.textTertiary, fontSize: FontSize.tiny, marginTop: 4, textAlign: 'center' },
  vixValue: { color: Colors.textPrimary, fontSize: FontSize.h3, fontWeight: '700', fontVariant: ['tabular-nums'] },
  regimePill: { alignSelf: 'flex-start', paddingHorizontal: 8, paddingVertical: 3, borderRadius: 4, marginTop: 6 },
  regimeText: { fontSize: FontSize.tiny, fontWeight: '700', letterSpacing: 0.5 },
  badge: { paddingHorizontal: 6, paddingVertical: 2, borderRadius: 4, alignSelf: 'flex-start' },
  badgePos: { backgroundColor: 'rgba(16,185,129,0.12)' },
  badgeNeg: { backgroundColor: 'rgba(239,68,68,0.12)' },
  badgeText: { fontSize: FontSize.small, fontWeight: '700', fontVariant: ['tabular-nums'] },
  pcrLabel: { color: Colors.textTertiary, fontSize: FontSize.tiny, fontWeight: '700', letterSpacing: 1 },
  pcrValue: { color: Colors.textPrimary, fontSize: FontSize.h3, fontWeight: '700', marginTop: 4, fontVariant: ['tabular-nums'] },
  pcrSentiment: { fontSize: FontSize.small, fontWeight: '600', marginTop: 4 },
  sectorRow: {
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    paddingVertical: 10, borderBottomWidth: 1, borderBottomColor: 'rgba(39,39,42,0.5)',
  },
  sectorLeft: { flex: 1 },
  sectorName: { color: Colors.textPrimary, fontSize: FontSize.body, fontWeight: '600' },
  sectorSub: { color: Colors.textTertiary, fontSize: FontSize.tiny, marginTop: 2 },
  sectorRight: { alignItems: 'flex-end', width: 100 },
  sectorPct: { fontSize: FontSize.body, fontWeight: '700', fontVariant: ['tabular-nums'] },
  sectorBarBg: { height: 3, width: 80, backgroundColor: Colors.surfaceElevated, borderRadius: 2, marginTop: 4 },
  sectorBarFill: { height: '100%', borderRadius: 2 },
  indexRow: {
    flexDirection: 'row', alignItems: 'center', paddingVertical: 10,
    borderBottomWidth: 1, borderBottomColor: 'rgba(39,39,42,0.5)',
  },
  indexRowName: { color: Colors.textPrimary, fontSize: FontSize.body, fontWeight: '500' },
  indexRowPrice: { color: Colors.textPrimary, fontSize: FontSize.body, fontWeight: '600', fontVariant: ['tabular-nums'], marginRight: 8 },
});
