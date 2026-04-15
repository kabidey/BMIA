import React from 'react';
import { View, Text, ScrollView, StyleSheet, TouchableOpacity } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { Colors, Spacing, FontSize } from '../src/constants/theme';

export default function WatchlistScreen() {
  const router = useRouter();

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <View style={styles.header}>
        <TouchableOpacity testID="watchlist-back" onPress={() => router.back()}>
          <Ionicons name="arrow-back" size={24} color={Colors.textPrimary} />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Watchlist</Text>
        <View style={{ width: 24 }} />
      </View>

      <ScrollView contentContainerStyle={styles.scrollContent}>
        <View style={styles.empty}>
          <Ionicons name="eye-outline" size={64} color={Colors.textTertiary} />
          <Text style={styles.emptyTitle}>Watchlist</Text>
          <Text style={styles.emptyDesc}>
            This feature connects to your BMIA account. Add stocks from the Symbol Analysis page to track them here.
          </Text>
          <TouchableOpacity
            testID="watchlist-go-analysis"
            style={styles.actionBtn}
            onPress={() => router.push('/analysis')}
          >
            <Ionicons name="search" size={18} color="#fff" />
            <Text style={styles.actionBtnText}>Go to Analysis</Text>
          </TouchableOpacity>
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
  empty: { alignItems: 'center', paddingTop: 60 },
  emptyTitle: { color: Colors.textPrimary, fontSize: FontSize.h3, fontWeight: '700', marginTop: 16 },
  emptyDesc: { color: Colors.textTertiary, fontSize: FontSize.body, textAlign: 'center', marginTop: 8, lineHeight: 20, paddingHorizontal: 20 },
  actionBtn: {
    flexDirection: 'row', alignItems: 'center', gap: 8,
    backgroundColor: Colors.brandPrimary, paddingHorizontal: 20, paddingVertical: 12,
    borderRadius: 8, marginTop: 24,
  },
  actionBtnText: { color: '#fff', fontSize: FontSize.body, fontWeight: '600' },
});
