import React from 'react';
import { View, Text, ScrollView, StyleSheet, TouchableOpacity } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { Colors, Spacing, FontSize } from '../src/constants/theme';

const STEPS = [
  { icon: 'globe', title: 'Data Ingestion', desc: 'BMIA pulls live market data from NSE, BSE, Yahoo Finance, and RSS news feeds. 2450+ stocks are tracked daily.' },
  { icon: 'calculator', title: 'Quant Analysis', desc: '25+ technical indicators and 30+ fundamental metrics are computed for each stock, including RSI, MACD, Stochastic, P/E, debt ratios, and more.' },
  { icon: 'sparkles', title: 'AI Intelligence Engine', desc: 'Multi-LLM ensemble (OpenAI + Claude + Gemini) generates actionable signals with entry, targets, stop-loss, confidence, and risk/reward analysis.' },
  { icon: 'flash', title: 'God Mode Consensus', desc: 'In God Mode, three independent AI models analyze each stock. Results are synthesized into a consensus signal with agreement scores.' },
  { icon: 'briefcase', title: 'Portfolio Construction', desc: 'AI-optimized portfolios (Swing, Quick Entry, Alpha Generator, Value) are built with sector diversification and volatility-based position sizing.' },
  { icon: 'refresh', title: 'Learning Loop', desc: 'Signals are tracked over time. Outcomes are evaluated and fed back into the intelligence engine to improve future predictions.' },
  { icon: 'shield-checkmark', title: 'SEBI Compliance', desc: 'All outputs include explicit disclaimers. BMIA is for educational purposes only and does not constitute investment advice.' },
];

export default function HowItWorksScreen() {
  const router = useRouter();

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <View style={styles.header}>
        <TouchableOpacity testID="how-it-works-back" onPress={() => router.back()}>
          <Ionicons name="arrow-back" size={24} color={Colors.textPrimary} />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>How It Works</Text>
        <View style={{ width: 24 }} />
      </View>

      <ScrollView contentContainerStyle={styles.scrollContent}>
        <Text style={styles.intro}>
          BMIA (Bharat Market Intel Agent) is an AI-powered Indian stock market intelligence platform.
        </Text>

        {STEPS.map((step, i) => (
          <View key={i} style={styles.stepCard} testID={`step-card-${i}`}>
            <View style={styles.stepIcon}>
              <Ionicons name={step.icon as any} size={24} color={Colors.brandPrimary} />
            </View>
            <View style={styles.stepContent}>
              <Text style={styles.stepNum}>STEP {i + 1}</Text>
              <Text style={styles.stepTitle}>{step.title}</Text>
              <Text style={styles.stepDesc}>{step.desc}</Text>
            </View>
          </View>
        ))}

        <View style={styles.techStack}>
          <Text style={styles.sectionLabel}>TECHNOLOGY STACK</Text>
          {['FastAPI + MongoDB Backend', 'NSE/BSE Live Data Feeds (nselib, yfinance)', 'OpenAI GPT-4.1 + Claude Sonnet + Gemini Flash', 'React Native (Expo) Mobile App', '25+ Technical Indicators + 30+ Fundamentals'].map((t, i) => (
            <View key={i} style={styles.techItem}>
              <Ionicons name="code-slash" size={14} color={Colors.brandPrimary} />
              <Text style={styles.techText}>{t}</Text>
            </View>
          ))}
        </View>

        <View style={{ height: 32 }} />
      </ScrollView>
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
  scrollContent: { padding: Spacing.base },
  intro: { color: Colors.textSecondary, fontSize: FontSize.bodyLarge, lineHeight: 24, marginBottom: 20 },
  stepCard: {
    flexDirection: 'row', gap: 12, backgroundColor: Colors.surface,
    borderRadius: 8, borderWidth: 1, borderColor: Colors.border, padding: 14, marginBottom: 10,
  },
  stepIcon: {
    width: 44, height: 44, borderRadius: 10, backgroundColor: 'rgba(59,130,246,0.1)',
    justifyContent: 'center', alignItems: 'center',
  },
  stepContent: { flex: 1 },
  stepNum: { color: Colors.brandPrimary, fontSize: FontSize.tiny, fontWeight: '800', letterSpacing: 1 },
  stepTitle: { color: Colors.textPrimary, fontSize: FontSize.bodyLarge, fontWeight: '700', marginTop: 2 },
  stepDesc: { color: Colors.textTertiary, fontSize: FontSize.small, lineHeight: 18, marginTop: 4 },
  techStack: { marginTop: 24 },
  sectionLabel: { color: Colors.textTertiary, fontSize: FontSize.tiny, fontWeight: '700', letterSpacing: 1.5, marginBottom: 10 },
  techItem: { flexDirection: 'row', alignItems: 'center', gap: 8, paddingVertical: 8 },
  techText: { color: Colors.textSecondary, fontSize: FontSize.body },
});
