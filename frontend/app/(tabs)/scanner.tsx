import React, { useState } from 'react';
import {
  View, Text, ScrollView, StyleSheet, TouchableOpacity,
  ActivityIndicator, TextInput,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { api } from '../../src/api/client';
import { Colors, Spacing, FontSize } from '../../src/constants/theme';

const ACTION_COLORS: Record<string, string> = {
  BUY: Colors.positive, SELL: Colors.negative, HOLD: Colors.warning, AVOID: Colors.textTertiary,
};

export default function Scanner() {
  const [scanning, setScanning] = useState(false);
  const [results, setResults] = useState<any[]>([]);
  const [mode, setMode] = useState<'ai' | 'god'>('god');
  const [error, setError] = useState('');

  const runScan = async () => {
    setScanning(true);
    setError('');
    setResults([]);
    try {
      const scanFn = mode === 'god' ? api.godScan : api.batchScan;
      const result = await scanFn({
        market: 'NSE',
        max_universe: 2450,
        shortlist: 30,
        top_n: 15,
        god_mode: mode === 'god',
      });
      setResults(result?.results || result?.rankings || []);
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

      <ScrollView contentContainerStyle={styles.scrollContent}>
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

        <View style={styles.infoCard}>
          <Ionicons name="information-circle" size={18} color={Colors.brandPrimary} />
          <Text style={styles.infoText}>
            {mode === 'god'
              ? 'God Mode uses multi-LLM ensemble (OpenAI + Claude + Gemini) with consensus distillation to surface high-conviction BUY candidates.'
              : 'AI Scan uses a single model to analyze and rank stocks from the NSE universe.'}
          </Text>
        </View>

        <TouchableOpacity
          testID="run-scan-btn"
          style={[styles.scanBtn, scanning && styles.scanBtnDisabled]}
          onPress={runScan}
          disabled={scanning}
        >
          {scanning ? (
            <ActivityIndicator size="small" color="#fff" />
          ) : (
            <Ionicons name="rocket" size={20} color="#fff" />
          )}
          <Text style={styles.scanBtnText}>
            {scanning ? 'Scanning NSE Universe...' : 'Run Scanner'}
          </Text>
        </TouchableOpacity>

        {error ? (
          <View style={styles.errorCard}>
            <Ionicons name="alert-circle" size={18} color={Colors.negative} />
            <Text style={styles.errorText}>{error}</Text>
          </View>
        ) : null}

        {scanning && (
          <View style={styles.progressCard}>
            <ActivityIndicator size="large" color={Colors.brandPrimary} />
            <Text style={styles.progressTitle}>Pipeline Running</Text>
            <Text style={styles.progressSub}>Universe → Prefilter → Shortlist → {mode === 'god' ? 'Ensemble' : 'AI Analysis'} → Rank</Text>
            <Text style={styles.progressNote}>This may take 2-5 minutes</Text>
          </View>
        )}

        {results.length > 0 && (
          <>
            <Text style={styles.resultTitle}>TOP {results.length} RESULTS</Text>
            {results.map((r: any, i: number) => {
              const symbol = r.symbol?.replace('.NS', '') || r.name || `#${i + 1}`;
              const action = r.action || r.consensus_action || 'N/A';
              return (
                <View key={i} style={styles.resultCard} testID={`scan-result-${i}`}>
                  <View style={styles.resultHeader}>
                    <View style={styles.rankCircle}>
                      <Text style={styles.rankText}>#{i + 1}</Text>
                    </View>
                    <Text style={styles.resultSymbol}>{symbol}</Text>
                    <View style={[styles.actionPill, { backgroundColor: (ACTION_COLORS[action] || Colors.textTertiary) + '20' }]}>
                      <Text style={[styles.actionPillText, { color: ACTION_COLORS[action] || Colors.textTertiary }]}>{action}</Text>
                    </View>
                  </View>
                  {r.confidence != null && (
                    <View style={styles.resultMeta}>
                      <Text style={styles.resultMetaLabel}>Confidence: {r.confidence}%</Text>
                      {r.agreement_level && (
                        <Text style={styles.resultMetaLabel}>Agreement: {r.agreement_level}</Text>
                      )}
                    </View>
                  )}
                  {r.rationale && (
                    <Text style={styles.resultRationale} numberOfLines={3}>{r.rationale}</Text>
                  )}
                </View>
              );
            })}
          </>
        )}

        <View style={{ height: 32 }} />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.background },
  header: {
    paddingHorizontal: Spacing.base, paddingVertical: 12,
    borderBottomWidth: 1, borderBottomColor: Colors.border,
  },
  headerTitle: { color: Colors.textPrimary, fontSize: FontSize.h3, fontWeight: '700' },
  scrollContent: { padding: Spacing.base },
  modeRow: { flexDirection: 'row', gap: 8 },
  modeBtn: {
    flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 6,
    backgroundColor: Colors.surface, borderWidth: 1, borderColor: Colors.border,
    paddingVertical: 12, borderRadius: 8,
  },
  modeBtnActive: { borderColor: Colors.brandPrimary, backgroundColor: 'rgba(59,130,246,0.08)' },
  modeBtnText: { color: Colors.textTertiary, fontSize: FontSize.body, fontWeight: '600' },
  modeBtnTextActive: { color: Colors.brandPrimary },
  infoCard: {
    flexDirection: 'row', gap: 8, backgroundColor: 'rgba(59,130,246,0.08)',
    padding: 12, borderRadius: 8, marginTop: 12,
  },
  infoText: { color: Colors.textSecondary, fontSize: FontSize.small, flex: 1, lineHeight: 18 },
  scanBtn: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8,
    backgroundColor: Colors.brandPrimary, paddingVertical: 14, borderRadius: 8, marginTop: 16,
  },
  scanBtnDisabled: { opacity: 0.6 },
  scanBtnText: { color: '#fff', fontSize: FontSize.bodyLarge, fontWeight: '700' },
  errorCard: {
    flexDirection: 'row', gap: 8, backgroundColor: 'rgba(239,68,68,0.1)',
    padding: 12, borderRadius: 8, marginTop: 12,
  },
  errorText: { color: Colors.negative, fontSize: FontSize.small, flex: 1 },
  progressCard: { alignItems: 'center', padding: 24, marginTop: 24 },
  progressTitle: { color: Colors.textPrimary, fontSize: FontSize.h4, fontWeight: '700', marginTop: 16 },
  progressSub: { color: Colors.textSecondary, fontSize: FontSize.small, marginTop: 4, textAlign: 'center' },
  progressNote: { color: Colors.textTertiary, fontSize: FontSize.tiny, marginTop: 8 },
  resultTitle: {
    color: Colors.textTertiary, fontSize: FontSize.tiny, fontWeight: '700',
    letterSpacing: 1.5, marginTop: 24, marginBottom: 8,
  },
  resultCard: {
    backgroundColor: Colors.surface, borderRadius: 8, borderWidth: 1, borderColor: Colors.border,
    padding: 12, marginBottom: 10,
  },
  resultHeader: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  rankCircle: {
    width: 28, height: 28, borderRadius: 14, backgroundColor: Colors.surfaceElevated,
    justifyContent: 'center', alignItems: 'center',
  },
  rankText: { color: Colors.textSecondary, fontSize: FontSize.tiny, fontWeight: '800' },
  resultSymbol: { color: Colors.textPrimary, fontSize: FontSize.bodyLarge, fontWeight: '800', flex: 1, letterSpacing: 1 },
  actionPill: { paddingHorizontal: 8, paddingVertical: 3, borderRadius: 4 },
  actionPillText: { fontSize: FontSize.tiny, fontWeight: '800', letterSpacing: 1 },
  resultMeta: { flexDirection: 'row', gap: 12, marginTop: 8 },
  resultMetaLabel: { color: Colors.textTertiary, fontSize: FontSize.tiny, fontWeight: '600' },
  resultRationale: { color: Colors.textSecondary, fontSize: FontSize.small, lineHeight: 18, marginTop: 6 },
});
