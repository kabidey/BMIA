import React, { useState } from 'react';
import {
  View, Text, ScrollView, StyleSheet, TouchableOpacity,
  ActivityIndicator, TextInput, KeyboardAvoidingView, Platform,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { api } from '../../src/api/client';
import { Colors, Spacing, FontSize } from '../../src/constants/theme';

const ACTION_COLORS: Record<string, string> = {
  BUY: Colors.positive, SELL: Colors.negative, HOLD: Colors.warning, AVOID: Colors.textTertiary,
};

const POPULAR_SYMBOLS = [
  'RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'INFY.NS', 'ICICIBANK.NS',
  'HINDUNILVR.NS', 'ITC.NS', 'SBIN.NS', 'BHARTIARTL.NS', 'KOTAKBANK.NS',
  'LT.NS', 'AXISBANK.NS', 'WIPRO.NS', 'TATAMOTORS.NS', 'MARUTI.NS',
];

export default function Scanner() {
  const [scanning, setScanning] = useState(false);
  const [results, setResults] = useState<any[]>([]);
  const [mode, setMode] = useState<'ai' | 'god'>('ai');
  const [error, setError] = useState('');
  const [customSymbols, setCustomSymbols] = useState('');
  const [selectedPreset, setSelectedPreset] = useState<'nifty50' | 'custom'>('nifty50');
  const [expandedIdx, setExpandedIdx] = useState<number | null>(null);
  const [scanMeta, setScanMeta] = useState<any>(null);

  const runScan = async () => {
    setScanning(true); setError(''); setResults([]); setScanMeta(null);
    try {
      let symbols: string[];
      if (selectedPreset === 'custom' && customSymbols.trim()) {
        symbols = customSymbols.split(',').map(s => {
          const sym = s.trim().toUpperCase();
          return sym.endsWith('.NS') ? sym : sym + '.NS';
        }).filter(Boolean);
      } else {
        symbols = POPULAR_SYMBOLS;
      }

      if (symbols.length === 0) {
        setError('Enter at least one symbol'); setScanning(false); return;
      }

      if (mode === 'ai') {
        const result = await api.batchScan({ symbols, mode: 'ai' });
        setResults(result?.results || []);
        setScanMeta({
          total: result?.total,
          provider: result?.provider,
          model: result?.model,
          generated_at: result?.generated_at,
        });
      } else {
        // God scan is async — start job
        const job = await api.godScan({
          market: 'NSE',
          max_universe: 2450,
          shortlist: 30,
          top_n: 15,
          god_mode: true,
        });
        if (job?.results) {
          setResults(job.results);
        } else if (job?.job_id) {
          setError(`God Mode scan started (Job: ${job.job_id}). This takes 2-5 minutes. Check back shortly.`);
        } else {
          setError('God scan returned unexpected response');
        }
      }
    } catch (e: any) {
      setError(e.message || 'Scan failed. Try again later.');
    } finally {
      setScanning(false);
    }
  };

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Batch Scanner</Text>
      </View>

      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : 'height'}>
        <ScrollView contentContainerStyle={styles.scrollContent} keyboardShouldPersistTaps="handled">
          {/* Mode Toggle */}
          <View style={styles.modeRow}>
            <TouchableOpacity
              testID="scanner-mode-ai"
              style={[styles.modeBtn, mode === 'ai' && styles.modeBtnActive]}
              onPress={() => setMode('ai')}
            >
              <Ionicons name="sparkles" size={16} color={mode === 'ai' ? Colors.brandPrimary : Colors.textTertiary} />
              <Text style={[styles.modeBtnText, mode === 'ai' && styles.modeBtnTextActive]}>AI Scan</Text>
            </TouchableOpacity>
            <TouchableOpacity
              testID="scanner-mode-god"
              style={[styles.modeBtn, mode === 'god' && styles.modeBtnActive]}
              onPress={() => setMode('god')}
            >
              <Ionicons name="flash" size={16} color={mode === 'god' ? Colors.warning : Colors.textTertiary} />
              <Text style={[styles.modeBtnText, mode === 'god' && styles.modeBtnTextActive]}>God Mode</Text>
            </TouchableOpacity>
          </View>

          {/* Symbol Selection (AI mode) */}
          {mode === 'ai' && (
            <>
              <Text style={styles.sectionLabel}>SYMBOL SET</Text>
              <View style={styles.presetRow}>
                <TouchableOpacity
                  testID="preset-nifty50"
                  style={[styles.presetBtn, selectedPreset === 'nifty50' && styles.presetBtnActive]}
                  onPress={() => setSelectedPreset('nifty50')}
                >
                  <Text style={[styles.presetText, selectedPreset === 'nifty50' && styles.presetTextActive]}>Top 15 Large Caps</Text>
                </TouchableOpacity>
                <TouchableOpacity
                  testID="preset-custom"
                  style={[styles.presetBtn, selectedPreset === 'custom' && styles.presetBtnActive]}
                  onPress={() => setSelectedPreset('custom')}
                >
                  <Text style={[styles.presetText, selectedPreset === 'custom' && styles.presetTextActive]}>Custom</Text>
                </TouchableOpacity>
              </View>

              {selectedPreset === 'custom' && (
                <TextInput
                  testID="custom-symbols-input"
                  style={styles.symbolInput}
                  placeholder="RELIANCE, TCS, INFY (comma separated)"
                  placeholderTextColor={Colors.textTertiary}
                  value={customSymbols}
                  onChangeText={setCustomSymbols}
                  multiline
                  autoCapitalize="characters"
                />
              )}

              {selectedPreset === 'nifty50' && (
                <View style={styles.chipWrap}>
                  {POPULAR_SYMBOLS.map(s => (
                    <View key={s} style={styles.symChip}>
                      <Text style={styles.symChipText}>{s.replace('.NS', '')}</Text>
                    </View>
                  ))}
                </View>
              )}
            </>
          )}

          {mode === 'god' && (
            <View style={styles.infoCard}>
              <Ionicons name="flash" size={18} color={Colors.warning} />
              <Text style={styles.infoText}>
                God Mode scans the entire NSE universe (2450+ stocks) using multi-LLM ensemble (OpenAI + Claude + Gemini). Pipeline: Universe → Prefilter → Shortlist → Ensemble → Consensus. Takes 2-5 minutes.
              </Text>
            </View>
          )}

          <TouchableOpacity
            testID="run-scan-btn"
            style={[styles.scanBtn, scanning && styles.scanBtnDisabled]}
            onPress={runScan}
            disabled={scanning}
          >
            {scanning ? (
              <ActivityIndicator size="small" color="#fff" />
            ) : (
              <Ionicons name={mode === 'god' ? 'flash' : 'rocket'} size={20} color="#fff" />
            )}
            <Text style={styles.scanBtnText}>
              {scanning ? (mode === 'god' ? 'Launching God Mode...' : 'Scanning...') : (mode === 'god' ? 'Launch God Scan' : 'Run AI Scan')}
            </Text>
          </TouchableOpacity>

          {error ? (
            <View style={[styles.errorCard, error.includes('started') && { backgroundColor: 'rgba(245,158,11,0.1)' }]}>
              <Ionicons name={error.includes('started') ? 'time' : 'alert-circle'} size={18} color={error.includes('started') ? Colors.warning : Colors.negative} />
              <Text style={[styles.errorText, error.includes('started') && { color: Colors.warning }]}>{error}</Text>
            </View>
          ) : null}

          {scanning && (
            <View style={styles.progressCard}>
              <ActivityIndicator size="large" color={Colors.brandPrimary} />
              <Text style={styles.progressTitle}>Analyzing...</Text>
              <Text style={styles.progressSub}>Computing technicals, fundamentals & AI rankings</Text>
            </View>
          )}

          {/* Results */}
          {results.length > 0 && (
            <>
              <View style={styles.resultHeaderRow}>
                <Text style={styles.resultTitle}>RESULTS ({results.length})</Text>
                {scanMeta?.model && (
                  <Text style={styles.resultMeta}>{scanMeta.provider} / {scanMeta.model}</Text>
                )}
              </View>

              {results.map((r: any, i: number) => {
                const symbol = r.symbol?.replace('.NS', '') || `#${i + 1}`;
                const action = r.action || 'N/A';
                const isExpanded = expandedIdx === i;
                return (
                  <TouchableOpacity
                    key={i}
                    style={styles.resultCard}
                    testID={`scan-result-${i}`}
                    onPress={() => setExpandedIdx(isExpanded ? null : i)}
                    activeOpacity={0.7}
                  >
                    <View style={styles.resultHeader}>
                      <View style={styles.rankCircle}>
                        <Text style={styles.rankText}>#{r.rank || i + 1}</Text>
                      </View>
                      <View style={{ flex: 1 }}>
                        <Text style={styles.resultSymbol}>{symbol}</Text>
                        <Text style={styles.resultName} numberOfLines={1}>{r.name || ''}</Text>
                      </View>
                      <View style={[styles.actionPill, { backgroundColor: (ACTION_COLORS[action] || Colors.textTertiary) + '20' }]}>
                        <Text style={[styles.actionPillText, { color: ACTION_COLORS[action] || Colors.textTertiary }]}>{action}</Text>
                      </View>
                    </View>

                    {/* Quick Stats */}
                    <View style={styles.quickStats}>
                      <View style={styles.qStat}>
                        <Text style={styles.qLabel}>PRICE</Text>
                        <Text style={styles.qValue}>₹{r.price?.toFixed(1)}</Text>
                      </View>
                      <View style={styles.qStat}>
                        <Text style={styles.qLabel}>CHG</Text>
                        <Text style={[styles.qValue, { color: (r.change_pct || 0) >= 0 ? Colors.positive : Colors.negative }]}>
                          {(r.change_pct || 0) >= 0 ? '+' : ''}{r.change_pct?.toFixed(2)}%
                        </Text>
                      </View>
                      <View style={styles.qStat}>
                        <Text style={styles.qLabel}>AI SCORE</Text>
                        <Text style={[styles.qValue, { color: Colors.brandPrimary }]}>{r.ai_score || '--'}</Text>
                      </View>
                      <View style={styles.qStat}>
                        <Text style={styles.qLabel}>CONV.</Text>
                        <Text style={[styles.qValue, {
                          color: r.conviction === 'HIGH' ? Colors.positive : r.conviction === 'MEDIUM' ? Colors.warning : Colors.textTertiary,
                        }]}>{r.conviction || '--'}</Text>
                      </View>
                    </View>

                    {/* Technical Indicators */}
                    <View style={styles.techRow}>
                      <View style={[styles.techChip, { backgroundColor: r.rsi > 70 ? 'rgba(239,68,68,0.12)' : r.rsi < 30 ? 'rgba(16,185,129,0.12)' : 'rgba(113,113,122,0.12)' }]}>
                        <Text style={styles.techLabel}>RSI {r.rsi?.toFixed(0)}</Text>
                      </View>
                      {r.adx_direction && (
                        <View style={[styles.techChip, { backgroundColor: r.adx_direction === 'bullish' ? 'rgba(16,185,129,0.12)' : 'rgba(239,68,68,0.12)' }]}>
                          <Text style={styles.techLabel}>ADX {r.adx?.toFixed(0)} {r.adx_direction === 'bullish' ? '↑' : '↓'}</Text>
                        </View>
                      )}
                      {r.obv_trend && (
                        <View style={[styles.techChip, { backgroundColor: r.obv_trend === 'accumulation' ? 'rgba(16,185,129,0.12)' : 'rgba(239,68,68,0.12)' }]}>
                          <Text style={styles.techLabel}>OBV: {r.obv_trend}</Text>
                        </View>
                      )}
                    </View>

                    {/* Expanded */}
                    {isExpanded && (
                      <View style={styles.expandedSection}>
                        {r.rationale && (
                          <>
                            <Text style={styles.expandLabel}>RATIONALE</Text>
                            <Text style={styles.rationaleText}>{r.rationale}</Text>
                          </>
                        )}
                        <View style={styles.expandGrid}>
                          {[
                            { label: 'Sector', value: r.sector },
                            { label: 'P/E', value: r.pe_ratio?.toFixed(1) },
                            { label: 'ROE', value: r.roe ? `${r.roe.toFixed(1)}%` : '--' },
                            { label: 'Rev Growth', value: r.revenue_growth ? `${r.revenue_growth.toFixed(1)}%` : '--' },
                            { label: 'Volume', value: r.volume?.toLocaleString() },
                          ].map(item => (
                            <View key={item.label} style={styles.expandItem}>
                              <Text style={styles.expandItemLabel}>{item.label}</Text>
                              <Text style={styles.expandItemValue}>{item.value || '--'}</Text>
                            </View>
                          ))}
                        </View>
                        {r.key_strength && (
                          <View style={styles.strengthRow}>
                            <Ionicons name="checkmark-circle" size={14} color={Colors.positive} />
                            <Text style={styles.strengthText}>{r.key_strength}</Text>
                          </View>
                        )}
                        {r.key_risk && (
                          <View style={styles.strengthRow}>
                            <Ionicons name="alert-circle" size={14} color={Colors.negative} />
                            <Text style={styles.strengthText}>{r.key_risk}</Text>
                          </View>
                        )}
                      </View>
                    )}

                    <Ionicons
                      name={isExpanded ? 'chevron-up' : 'chevron-down'}
                      size={14} color={Colors.textTertiary}
                      style={{ alignSelf: 'center', marginTop: 4 }}
                    />
                  </TouchableOpacity>
                );
              })}
            </>
          )}

          <View style={styles.disclaimer}>
            <Ionicons name="warning" size={14} color={Colors.warning} />
            <Text style={styles.disclaimerText}>For educational purposes only. Not investment advice.</Text>
          </View>
          <View style={{ height: 32 }} />
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.background },
  header: { paddingHorizontal: Spacing.base, paddingVertical: 12, borderBottomWidth: 1, borderBottomColor: Colors.border },
  headerTitle: { color: Colors.textPrimary, fontSize: FontSize.h3, fontWeight: '700' },
  scrollContent: { padding: Spacing.base },
  modeRow: { flexDirection: 'row', gap: 8 },
  modeBtn: {
    flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 6,
    backgroundColor: Colors.surface, borderWidth: 1, borderColor: Colors.border, paddingVertical: 12, borderRadius: 8,
  },
  modeBtnActive: { borderColor: Colors.brandPrimary, backgroundColor: 'rgba(59,130,246,0.08)' },
  modeBtnText: { color: Colors.textTertiary, fontSize: FontSize.body, fontWeight: '600' },
  modeBtnTextActive: { color: Colors.brandPrimary },
  sectionLabel: { color: Colors.textTertiary, fontSize: FontSize.tiny, fontWeight: '700', letterSpacing: 1.5, marginTop: 16, marginBottom: 8 },
  presetRow: { flexDirection: 'row', gap: 8 },
  presetBtn: {
    flex: 1, paddingVertical: 10, borderRadius: 6, borderWidth: 1, borderColor: Colors.border,
    backgroundColor: Colors.surface, alignItems: 'center',
  },
  presetBtnActive: { borderColor: Colors.brandPrimary, backgroundColor: 'rgba(59,130,246,0.08)' },
  presetText: { color: Colors.textTertiary, fontSize: FontSize.small, fontWeight: '600' },
  presetTextActive: { color: Colors.brandPrimary },
  symbolInput: {
    backgroundColor: Colors.surface, borderWidth: 1, borderColor: Colors.border, borderRadius: 8,
    padding: 12, color: Colors.textPrimary, fontSize: FontSize.body, marginTop: 8, minHeight: 60,
    textAlignVertical: 'top',
  },
  chipWrap: { flexDirection: 'row', flexWrap: 'wrap', gap: 6, marginTop: 8 },
  symChip: { backgroundColor: Colors.surfaceElevated, paddingHorizontal: 8, paddingVertical: 4, borderRadius: 4 },
  symChipText: { color: Colors.textSecondary, fontSize: FontSize.tiny, fontWeight: '700', letterSpacing: 0.5 },
  infoCard: { flexDirection: 'row', gap: 8, backgroundColor: 'rgba(245,158,11,0.08)', padding: 12, borderRadius: 8, marginTop: 12 },
  infoText: { color: Colors.textSecondary, fontSize: FontSize.small, flex: 1, lineHeight: 18 },
  scanBtn: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8,
    backgroundColor: Colors.brandPrimary, paddingVertical: 14, borderRadius: 8, marginTop: 16,
  },
  scanBtnDisabled: { opacity: 0.6 },
  scanBtnText: { color: '#fff', fontSize: FontSize.bodyLarge, fontWeight: '700' },
  errorCard: { flexDirection: 'row', gap: 8, backgroundColor: 'rgba(239,68,68,0.1)', padding: 12, borderRadius: 8, marginTop: 12 },
  errorText: { color: Colors.negative, fontSize: FontSize.small, flex: 1 },
  progressCard: { alignItems: 'center', padding: 24, marginTop: 24 },
  progressTitle: { color: Colors.textPrimary, fontSize: FontSize.h4, fontWeight: '700', marginTop: 16 },
  progressSub: { color: Colors.textSecondary, fontSize: FontSize.small, marginTop: 4 },
  resultHeaderRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginTop: 20, marginBottom: 8 },
  resultTitle: { color: Colors.textTertiary, fontSize: FontSize.tiny, fontWeight: '700', letterSpacing: 1.5 },
  resultMeta: { color: Colors.textTertiary, fontSize: FontSize.tiny },
  resultCard: { backgroundColor: Colors.surface, borderRadius: 8, borderWidth: 1, borderColor: Colors.border, padding: 12, marginBottom: 10 },
  resultHeader: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  rankCircle: { width: 28, height: 28, borderRadius: 14, backgroundColor: Colors.surfaceElevated, justifyContent: 'center', alignItems: 'center' },
  rankText: { color: Colors.textSecondary, fontSize: FontSize.tiny, fontWeight: '800' },
  resultSymbol: { color: Colors.textPrimary, fontSize: FontSize.bodyLarge, fontWeight: '800', letterSpacing: 1 },
  resultName: { color: Colors.textTertiary, fontSize: FontSize.tiny, marginTop: 1 },
  actionPill: { paddingHorizontal: 8, paddingVertical: 3, borderRadius: 4 },
  actionPillText: { fontSize: FontSize.tiny, fontWeight: '800', letterSpacing: 1 },
  quickStats: { flexDirection: 'row', marginTop: 10, gap: 4 },
  qStat: { flex: 1 },
  qLabel: { color: Colors.textTertiary, fontSize: 9, fontWeight: '700', letterSpacing: 0.5 },
  qValue: { color: Colors.textPrimary, fontSize: FontSize.small, fontWeight: '700', fontVariant: ['tabular-nums'], marginTop: 1 },
  techRow: { flexDirection: 'row', gap: 6, marginTop: 8, flexWrap: 'wrap' },
  techChip: { paddingHorizontal: 6, paddingVertical: 2, borderRadius: 3 },
  techLabel: { color: Colors.textSecondary, fontSize: 9, fontWeight: '700' },
  expandedSection: { marginTop: 10, paddingTop: 10, borderTopWidth: 1, borderTopColor: Colors.border },
  expandLabel: { color: Colors.textTertiary, fontSize: FontSize.tiny, fontWeight: '700', letterSpacing: 1, marginBottom: 4 },
  rationaleText: { color: Colors.textSecondary, fontSize: FontSize.small, lineHeight: 18, marginBottom: 10 },
  expandGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  expandItem: { width: '30%' },
  expandItemLabel: { color: Colors.textTertiary, fontSize: 9, fontWeight: '600' },
  expandItemValue: { color: Colors.textPrimary, fontSize: FontSize.small, fontWeight: '600', fontVariant: ['tabular-nums'] },
  strengthRow: { flexDirection: 'row', alignItems: 'flex-start', gap: 6, marginTop: 8 },
  strengthText: { color: Colors.textSecondary, fontSize: FontSize.small, flex: 1, lineHeight: 17 },
  disclaimer: { flexDirection: 'row', alignItems: 'center', gap: 6, backgroundColor: 'rgba(245,158,11,0.08)', padding: 10, borderRadius: 6, marginTop: 16 },
  disclaimerText: { color: Colors.textTertiary, fontSize: FontSize.tiny, flex: 1 },
});
