import React, { useEffect, useState, useCallback } from 'react';
import {
  View, Text, ScrollView, StyleSheet, RefreshControl,
  TouchableOpacity, ActivityIndicator,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { api } from '../../src/api/client';
import { Colors, Spacing, FontSize } from '../../src/constants/theme';

const ACTION_COLORS: Record<string, string> = {
  BUY: Colors.positive,
  SELL: Colors.negative,
  HOLD: Colors.warning,
  AVOID: Colors.textTertiary,
};

function ActionBadge({ action }: { action: string }) {
  const color = ACTION_COLORS[action] || Colors.textSecondary;
  return (
    <View style={[styles.actionBadge, { backgroundColor: color + '20', borderColor: color + '40' }]}>
      <Text style={[styles.actionBadgeText, { color }]}>{action}</Text>
    </View>
  );
}

function ConfidenceBar({ value }: { value: number }) {
  const color = value >= 70 ? Colors.positive : value >= 40 ? Colors.warning : Colors.negative;
  return (
    <View style={styles.confBar}>
      <View style={[styles.confFill, { width: `${value}%`, backgroundColor: color }]} />
      <Text style={[styles.confText, { color }]}>{value}%</Text>
    </View>
  );
}

export default function SignalDashboard() {
  const [signals, setSignals] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    try {
      const result = await api.activeSignals();
      setSignals(result?.signals || []);
    } catch (e) {
      console.error('Signal fetch error:', e);
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
          <Text style={styles.loadingText}>Loading Signals...</Text>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>AI Signals</Text>
        <Text style={styles.headerCount}>{signals.length} Active</Text>
      </View>

      <ScrollView
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={Colors.brandPrimary} />}
        contentContainerStyle={styles.scrollContent}
      >
        {signals.length === 0 ? (
          <View style={styles.empty}>
            <Ionicons name="pulse-outline" size={48} color={Colors.textTertiary} />
            <Text style={styles.emptyText}>No active signals</Text>
          </View>
        ) : (
          signals.map((sig: any) => {
            const symbol = sig.symbol?.replace('.NS', '') || 'N/A';
            const isExpanded = expandedId === sig._id;
            return (
              <TouchableOpacity
                key={sig._id}
                style={styles.signalCard}
                testID={`signal-card-${symbol}`}
                onPress={() => setExpandedId(isExpanded ? null : sig._id)}
                activeOpacity={0.7}
              >
                <View style={styles.signalHeader}>
                  <View style={styles.signalLeft}>
                    <Text style={styles.symbolText}>{symbol}</Text>
                    {sig.god_mode && (
                      <View style={styles.godModePill}>
                        <Ionicons name="flash" size={10} color={Colors.warning} />
                        <Text style={styles.godModeText}>GOD</Text>
                      </View>
                    )}
                  </View>
                  <ActionBadge action={sig.action} />
                </View>

                <View style={styles.signalMeta}>
                  <Text style={styles.metaItem}>{sig.timeframe}</Text>
                  <Text style={styles.metaDot}>·</Text>
                  <Text style={styles.metaItem}>{sig.horizon_days}d</Text>
                  <Text style={styles.metaDot}>·</Text>
                  <Text style={styles.metaItem}>{sig.days_open}d open</Text>
                </View>

                <View style={styles.priceRow}>
                  <View style={styles.priceCol}>
                    <Text style={styles.priceLabel}>ENTRY</Text>
                    <Text style={styles.priceValue}>{sig.entry_price > 0 ? sig.entry_price?.toFixed(1) : '--'}</Text>
                  </View>
                  <View style={styles.priceCol}>
                    <Text style={styles.priceLabel}>CURRENT</Text>
                    <Text style={styles.priceValue}>{sig.current_price > 0 ? sig.current_price?.toFixed(1) : '--'}</Text>
                  </View>
                  <View style={styles.priceCol}>
                    <Text style={styles.priceLabel}>RETURN</Text>
                    <Text style={[styles.priceValue, {
                      color: sig.return_pct >= 0 ? Colors.positive : Colors.negative
                    }]}>
                      {sig.return_pct >= 0 ? '+' : ''}{sig.return_pct?.toFixed(2)}%
                    </Text>
                  </View>
                </View>

                <View style={styles.confRow}>
                  <Text style={styles.confLabel}>CONFIDENCE</Text>
                  <ConfidenceBar value={sig.confidence} />
                </View>

                {/* God Mode Votes */}
                {sig.god_mode && sig.model_votes && (
                  <View style={styles.votesRow}>
                    {Object.entries(sig.model_votes).map(([model, vote]: [string, any]) => (
                      <View key={model} style={styles.voteChip}>
                        <Text style={styles.voteModel}>{model.charAt(0).toUpperCase()}</Text>
                        <Text style={[styles.voteAction, { color: ACTION_COLORS[vote.action] || Colors.textSecondary }]}>
                          {vote.action}
                        </Text>
                      </View>
                    ))}
                  </View>
                )}

                {/* Expanded Detail */}
                {isExpanded && (
                  <View style={styles.expandedSection}>
                    {sig.key_theses?.length > 0 && (
                      <>
                        <Text style={styles.expandLabel}>KEY THESES</Text>
                        {sig.key_theses.map((t: string, i: number) => (
                          <Text key={i} style={styles.thesisText}>• {t}</Text>
                        ))}
                      </>
                    )}
                    {sig.targets?.length > 0 && (
                      <View style={styles.targetRow}>
                        {sig.targets.map((t: any, i: number) => (
                          <View key={i} style={styles.targetChip}>
                            <Text style={styles.targetLabel}>{t.label}</Text>
                            <Text style={styles.targetPrice}>{t.price}</Text>
                          </View>
                        ))}
                        <View style={styles.targetChip}>
                          <Text style={[styles.targetLabel, { color: Colors.negative }]}>STOP</Text>
                          <Text style={[styles.targetPrice, { color: Colors.negative }]}>{sig.stop_loss?.price}</Text>
                        </View>
                      </View>
                    )}
                  </View>
                )}

                <Ionicons
                  name={isExpanded ? 'chevron-up' : 'chevron-down'}
                  size={16} color={Colors.textTertiary}
                  style={styles.expandIcon}
                />
              </TouchableOpacity>
            );
          })
        )}

        <View style={styles.disclaimer}>
          <Ionicons name="warning" size={14} color={Colors.warning} />
          <Text style={styles.disclaimerText}>
            For educational purposes only. Not investment advice. Past performance does not guarantee future results.
          </Text>
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
    paddingHorizontal: Spacing.base, paddingVertical: 12,
    borderBottomWidth: 1, borderBottomColor: Colors.border,
  },
  headerTitle: { color: Colors.textPrimary, fontSize: FontSize.h3, fontWeight: '700' },
  headerCount: { color: Colors.brandPrimary, fontSize: FontSize.body, fontWeight: '600' },
  scrollContent: { padding: Spacing.base },
  empty: { alignItems: 'center', marginTop: 60 },
  emptyText: { color: Colors.textTertiary, fontSize: FontSize.body, marginTop: 12 },
  signalCard: {
    backgroundColor: Colors.surface, borderRadius: 8, borderWidth: 1, borderColor: Colors.border,
    padding: 14, marginBottom: 12,
  },
  signalHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  signalLeft: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  symbolText: { color: Colors.textPrimary, fontSize: FontSize.h4, fontWeight: '800', letterSpacing: 1 },
  godModePill: {
    flexDirection: 'row', alignItems: 'center', gap: 2,
    backgroundColor: 'rgba(245,158,11,0.15)', paddingHorizontal: 6, paddingVertical: 2, borderRadius: 4,
  },
  godModeText: { color: Colors.warning, fontSize: 9, fontWeight: '800', letterSpacing: 1 },
  actionBadge: {
    paddingHorizontal: 10, paddingVertical: 4, borderRadius: 4, borderWidth: 1,
  },
  actionBadgeText: { fontSize: FontSize.small, fontWeight: '800', letterSpacing: 1 },
  signalMeta: { flexDirection: 'row', alignItems: 'center', marginTop: 6, gap: 4 },
  metaItem: { color: Colors.textTertiary, fontSize: FontSize.tiny, fontWeight: '600', textTransform: 'uppercase' },
  metaDot: { color: Colors.textTertiary, fontSize: FontSize.tiny },
  priceRow: { flexDirection: 'row', marginTop: 12, gap: 8 },
  priceCol: { flex: 1 },
  priceLabel: { color: Colors.textTertiary, fontSize: FontSize.tiny, fontWeight: '700', letterSpacing: 0.5, marginBottom: 2 },
  priceValue: { color: Colors.textPrimary, fontSize: FontSize.bodyLarge, fontWeight: '700', fontVariant: ['tabular-nums'] },
  confRow: { marginTop: 12 },
  confLabel: { color: Colors.textTertiary, fontSize: FontSize.tiny, fontWeight: '700', letterSpacing: 0.5, marginBottom: 4 },
  confBar: { height: 18, backgroundColor: Colors.surfaceElevated, borderRadius: 4, overflow: 'hidden', position: 'relative' },
  confFill: { height: '100%', borderRadius: 4 },
  confText: {
    position: 'absolute', right: 6, top: 1,
    fontSize: FontSize.tiny, fontWeight: '800', fontVariant: ['tabular-nums'],
  },
  votesRow: { flexDirection: 'row', gap: 6, marginTop: 10 },
  voteChip: {
    flexDirection: 'row', alignItems: 'center', gap: 4,
    backgroundColor: Colors.surfaceElevated, paddingHorizontal: 8, paddingVertical: 3, borderRadius: 4,
  },
  voteModel: { color: Colors.textTertiary, fontSize: FontSize.tiny, fontWeight: '800' },
  voteAction: { fontSize: FontSize.tiny, fontWeight: '700' },
  expandedSection: { marginTop: 12, paddingTop: 12, borderTopWidth: 1, borderTopColor: Colors.border },
  expandLabel: { color: Colors.textTertiary, fontSize: FontSize.tiny, fontWeight: '700', letterSpacing: 1, marginBottom: 6 },
  thesisText: { color: Colors.textSecondary, fontSize: FontSize.small, lineHeight: 18, marginBottom: 4 },
  targetRow: { flexDirection: 'row', gap: 8, marginTop: 10, flexWrap: 'wrap' },
  targetChip: {
    backgroundColor: Colors.surfaceElevated, paddingHorizontal: 10, paddingVertical: 6, borderRadius: 4,
  },
  targetLabel: { color: Colors.positive, fontSize: FontSize.tiny, fontWeight: '700', letterSpacing: 0.5 },
  targetPrice: { color: Colors.textPrimary, fontSize: FontSize.body, fontWeight: '700', fontVariant: ['tabular-nums'] },
  expandIcon: { alignSelf: 'center', marginTop: 6 },
  disclaimer: {
    flexDirection: 'row', alignItems: 'flex-start', gap: 6,
    backgroundColor: 'rgba(245,158,11,0.08)', padding: 10, borderRadius: 6, marginTop: 16,
  },
  disclaimerText: { color: Colors.textTertiary, fontSize: FontSize.tiny, flex: 1, lineHeight: 14 },
});
