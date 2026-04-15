import React, { useState } from 'react';
import {
  View, Text, ScrollView, StyleSheet, TextInput,
  TouchableOpacity, ActivityIndicator, KeyboardAvoidingView, Platform,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { api } from '../src/api/client';
import { Colors, Spacing, FontSize } from '../src/constants/theme';

export default function AnalysisScreen() {
  const router = useRouter();
  const params = useLocalSearchParams<{ symbol?: string }>();
  const [query, setQuery] = useState(params.symbol || '');
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<any>(null);
  const [error, setError] = useState('');

  const doAnalyze = async () => {
    if (!query.trim()) return;
    setLoading(true); setError(''); setData(null);
    try {
      const symbol = query.trim().toUpperCase();
      const suffix = symbol.endsWith('.NS') ? '' : '.NS';
      const result = await api.analyzeSymbol(symbol + suffix);
      setData(result);
    } catch (e: any) {
      setError(e.message || 'Analysis failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : 'height'}>
        <View style={styles.header}>
          <TouchableOpacity testID="analysis-back-btn" onPress={() => router.back()}>
            <Ionicons name="arrow-back" size={24} color={Colors.textPrimary} />
          </TouchableOpacity>
          <Text style={styles.headerTitle}>Symbol Analysis</Text>
          <View style={{ width: 24 }} />
        </View>

        <View style={styles.searchRow}>
          <TextInput
            testID="analysis-search-input"
            style={styles.searchInput}
            placeholder="Enter symbol (e.g. RELIANCE)"
            placeholderTextColor={Colors.textTertiary}
            value={query}
            onChangeText={setQuery}
            onSubmitEditing={doAnalyze}
            autoCapitalize="characters"
            returnKeyType="search"
          />
          <TouchableOpacity testID="analysis-search-btn" style={styles.searchBtn} onPress={doAnalyze} disabled={loading}>
            {loading ? (
              <ActivityIndicator size="small" color="#fff" />
            ) : (
              <Ionicons name="search" size={20} color="#fff" />
            )}
          </TouchableOpacity>
        </View>

        <ScrollView contentContainerStyle={styles.scrollContent}>
          {error ? (
            <View style={styles.errorCard}>
              <Ionicons name="alert-circle" size={20} color={Colors.negative} />
              <Text style={styles.errorText}>{error}</Text>
            </View>
          ) : null}

          {loading && (
            <View style={styles.loadingBox}>
              <ActivityIndicator size="large" color={Colors.brandPrimary} />
              <Text style={styles.loadingText}>Analyzing {query.toUpperCase()}...</Text>
              <Text style={styles.loadingSub}>Fetching technicals, fundamentals & sentiment</Text>
            </View>
          )}

          {data && !loading && (
            <>
              {/* Header Info */}
              <View style={styles.symbolHeader}>
                <Text style={styles.symbolName}>{data.symbol || query}</Text>
                {data.current_price != null && (
                  <Text style={styles.symbolPrice}>₹{data.current_price?.toFixed(2)}</Text>
                )}
              </View>

              {/* Signal if available */}
              {data.signal && (
                <View style={styles.card}>
                  <Text style={styles.sectionLabel}>AI SIGNAL</Text>
                  <View style={styles.signalRow}>
                    <View style={[styles.actionBadge, {
                      backgroundColor: (data.signal.action === 'BUY' ? Colors.positive : data.signal.action === 'SELL' ? Colors.negative : Colors.warning) + '20'
                    }]}>
                      <Text style={[styles.actionText, {
                        color: data.signal.action === 'BUY' ? Colors.positive : data.signal.action === 'SELL' ? Colors.negative : Colors.warning
                      }]}>{data.signal.action}</Text>
                    </View>
                    <Text style={styles.signalConf}>Confidence: {data.signal.confidence}%</Text>
                  </View>
                  {data.signal.key_theses?.map((t: string, i: number) => (
                    <Text key={i} style={styles.thesisText}>• {t}</Text>
                  ))}
                </View>
              )}

              {/* Technical Summary */}
              {data.technicals && (
                <View style={styles.card}>
                  <Text style={styles.sectionLabel}>TECHNICALS</Text>
                  {Object.entries(data.technicals).slice(0, 15).map(([key, val]: [string, any]) => (
                    <View key={key} style={styles.dataRow}>
                      <Text style={styles.dataLabel}>{key.replace(/_/g, ' ')}</Text>
                      <Text style={styles.dataValue}>{typeof val === 'number' ? val.toFixed(2) : String(val ?? '--')}</Text>
                    </View>
                  ))}
                </View>
              )}

              {/* Fundamental Summary */}
              {data.fundamentals && (
                <View style={styles.card}>
                  <Text style={styles.sectionLabel}>FUNDAMENTALS</Text>
                  {Object.entries(data.fundamentals).slice(0, 15).map(([key, val]: [string, any]) => (
                    <View key={key} style={styles.dataRow}>
                      <Text style={styles.dataLabel}>{key.replace(/_/g, ' ')}</Text>
                      <Text style={styles.dataValue}>{typeof val === 'number' ? val.toFixed(2) : String(val ?? '--')}</Text>
                    </View>
                  ))}
                </View>
              )}

              {/* Sentiment */}
              {data.sentiment && (
                <View style={styles.card}>
                  <Text style={styles.sectionLabel}>SENTIMENT</Text>
                  <Text style={styles.sentScore}>
                    Score: {data.sentiment.score?.toFixed(2)} ({data.sentiment.label || 'N/A'})
                  </Text>
                  {data.sentiment.headlines?.slice(0, 5).map((h: any, i: number) => (
                    <Text key={i} style={styles.headline}>• {h.title || h}</Text>
                  ))}
                </View>
              )}
            </>
          )}

          {!data && !loading && !error && (
            <View style={styles.placeholder}>
              <Ionicons name="analytics-outline" size={64} color={Colors.textTertiary} />
              <Text style={styles.placeholderText}>Enter a stock symbol to analyze</Text>
              <Text style={styles.placeholderSub}>e.g. RELIANCE, TCS, HDFCBANK</Text>
            </View>
          )}

          <View style={{ height: 32 }} />
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.background },
  header: {
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    paddingHorizontal: Spacing.base, paddingVertical: 12,
    borderBottomWidth: 1, borderBottomColor: Colors.border,
  },
  headerTitle: { color: Colors.textPrimary, fontSize: FontSize.h4, fontWeight: '700' },
  searchRow: { flexDirection: 'row', padding: Spacing.base, gap: 8 },
  searchInput: {
    flex: 1, backgroundColor: Colors.surface, borderWidth: 1, borderColor: Colors.border,
    borderRadius: 8, paddingHorizontal: 14, paddingVertical: 12,
    color: Colors.textPrimary, fontSize: FontSize.body, fontWeight: '600', letterSpacing: 1,
  },
  searchBtn: {
    backgroundColor: Colors.brandPrimary, borderRadius: 8, width: 48,
    justifyContent: 'center', alignItems: 'center',
  },
  scrollContent: { padding: Spacing.base, paddingTop: 0 },
  errorCard: {
    flexDirection: 'row', gap: 8, backgroundColor: 'rgba(239,68,68,0.1)',
    padding: 12, borderRadius: 8, marginBottom: 12,
  },
  errorText: { color: Colors.negative, fontSize: FontSize.small, flex: 1 },
  loadingBox: { alignItems: 'center', paddingVertical: 40 },
  loadingText: { color: Colors.textPrimary, fontSize: FontSize.bodyLarge, fontWeight: '600', marginTop: 16 },
  loadingSub: { color: Colors.textTertiary, fontSize: FontSize.small, marginTop: 4 },
  symbolHeader: { marginBottom: 12 },
  symbolName: { color: Colors.textPrimary, fontSize: FontSize.h2, fontWeight: '800', letterSpacing: 1 },
  symbolPrice: { color: Colors.textPrimary, fontSize: FontSize.priceMedium, fontWeight: '700', fontVariant: ['tabular-nums'], marginTop: 4 },
  card: {
    backgroundColor: Colors.surface, borderRadius: 8, borderWidth: 1, borderColor: Colors.border,
    padding: 14, marginBottom: 12,
  },
  sectionLabel: { color: Colors.textTertiary, fontSize: FontSize.tiny, fontWeight: '700', letterSpacing: 1.5, marginBottom: 10 },
  signalRow: { flexDirection: 'row', alignItems: 'center', gap: 10, marginBottom: 10 },
  actionBadge: { paddingHorizontal: 10, paddingVertical: 4, borderRadius: 4 },
  actionText: { fontSize: FontSize.body, fontWeight: '800', letterSpacing: 1 },
  signalConf: { color: Colors.textSecondary, fontSize: FontSize.small, fontWeight: '600' },
  thesisText: { color: Colors.textSecondary, fontSize: FontSize.small, lineHeight: 18, marginBottom: 4 },
  dataRow: {
    flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 6,
    borderBottomWidth: 1, borderBottomColor: 'rgba(39,39,42,0.5)',
  },
  dataLabel: { color: Colors.textTertiary, fontSize: FontSize.small, textTransform: 'capitalize', flex: 1 },
  dataValue: { color: Colors.textPrimary, fontSize: FontSize.small, fontWeight: '600', fontVariant: ['tabular-nums'] },
  sentScore: { color: Colors.textPrimary, fontSize: FontSize.body, fontWeight: '600', marginBottom: 8 },
  headline: { color: Colors.textSecondary, fontSize: FontSize.small, lineHeight: 18, marginBottom: 4 },
  placeholder: { alignItems: 'center', paddingVertical: 60 },
  placeholderText: { color: Colors.textSecondary, fontSize: FontSize.bodyLarge, marginTop: 16 },
  placeholderSub: { color: Colors.textTertiary, fontSize: FontSize.small, marginTop: 4 },
});
