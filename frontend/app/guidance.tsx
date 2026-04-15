import React from 'react';
import { View, Text, ScrollView, StyleSheet, TouchableOpacity } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { Colors, Spacing, FontSize } from '../src/constants/theme';

export default function GuidanceScreen() {
  const router = useRouter();

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <View style={styles.header}>
        <TouchableOpacity testID="guidance-back" onPress={() => router.back()}>
          <Ionicons name="arrow-back" size={24} color={Colors.textPrimary} />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Market Guidance</Text>
        <View style={{ width: 24 }} />
      </View>

      <ScrollView contentContainerStyle={styles.scrollContent}>
        <View style={styles.empty}>
          <Ionicons name="book-outline" size={64} color={Colors.textTertiary} />
          <Text style={styles.emptyTitle}>Market Guidance</Text>
          <Text style={styles.emptyDesc}>
            AI-generated market guidance and educational insights. This feature connects to the BMIA guidance engine which processes regulatory filings, market data, and research to provide contextual insights.
          </Text>
          <View style={styles.featureList}>
            {[
              'AI-powered market regime analysis',
              'Sector rotation guidance',
              'Risk management frameworks',
              'Educational content on indicators',
            ].map((f, i) => (
              <View key={i} style={styles.featureItem}>
                <Ionicons name="checkmark-circle" size={16} color={Colors.positive} />
                <Text style={styles.featureText}>{f}</Text>
              </View>
            ))}
          </View>
        </View>
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
  empty: { alignItems: 'center', paddingTop: 40 },
  emptyTitle: { color: Colors.textPrimary, fontSize: FontSize.h3, fontWeight: '700', marginTop: 16 },
  emptyDesc: { color: Colors.textTertiary, fontSize: FontSize.body, textAlign: 'center', marginTop: 8, lineHeight: 20, paddingHorizontal: 10 },
  featureList: { marginTop: 24, alignSelf: 'stretch' },
  featureItem: {
    flexDirection: 'row', alignItems: 'center', gap: 10,
    backgroundColor: Colors.surface, borderRadius: 8, padding: 14, marginBottom: 8,
    borderWidth: 1, borderColor: Colors.border,
  },
  featureText: { color: Colors.textSecondary, fontSize: FontSize.body },
});
