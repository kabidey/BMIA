import React from 'react';
import { View, Text, ScrollView, StyleSheet, TouchableOpacity } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { Colors, Spacing, FontSize } from '../../src/constants/theme';

const MENU_ITEMS = [
  { label: 'Track Record', icon: 'trophy', route: '/track-record', desc: 'Signal performance metrics' },
  { label: 'Watchlist', icon: 'eye', route: '/watchlist', desc: 'Your saved stocks' },
  { label: 'Guidance', icon: 'book', route: '/guidance', desc: 'Market guidance & insights' },
  { label: 'How It Works', icon: 'help-circle', route: '/how-it-works', desc: 'Learn about BMIA' },
  { label: 'Audit Log', icon: 'document-text', route: '/audit-log', desc: 'Activity log' },
  { label: 'Settings', icon: 'settings', route: '/settings', desc: 'App settings & version' },
];

export default function MoreScreen() {
  const router = useRouter();

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>More</Text>
      </View>

      <ScrollView contentContainerStyle={styles.scrollContent}>
        {MENU_ITEMS.map((item) => (
          <TouchableOpacity
            key={item.route}
            style={styles.menuItem}
            testID={`more-menu-${item.label.toLowerCase().replace(/\s+/g, '-')}`}
            onPress={() => router.push(item.route as any)}
            activeOpacity={0.7}
          >
            <View style={styles.menuIcon}>
              <Ionicons name={item.icon as any} size={22} color={Colors.brandPrimary} />
            </View>
            <View style={styles.menuContent}>
              <Text style={styles.menuLabel}>{item.label}</Text>
              <Text style={styles.menuDesc}>{item.desc}</Text>
            </View>
            <Ionicons name="chevron-forward" size={18} color={Colors.textTertiary} />
          </TouchableOpacity>
        ))}

        <View style={styles.disclaimer}>
          <Ionicons name="shield-checkmark" size={16} color={Colors.brandPrimary} />
          <Text style={styles.disclaimerText}>
            BMIA is for educational and informational purposes only. All analysis is AI-generated and does not constitute investment advice. Always consult a SEBI-registered advisor before making investment decisions.
          </Text>
        </View>
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
  menuItem: {
    flexDirection: 'row', alignItems: 'center', gap: 12,
    backgroundColor: Colors.surface, borderRadius: 8, borderWidth: 1, borderColor: Colors.border,
    padding: 14, marginBottom: 8,
  },
  menuIcon: {
    width: 42, height: 42, borderRadius: 10, backgroundColor: 'rgba(59,130,246,0.1)',
    justifyContent: 'center', alignItems: 'center',
  },
  menuContent: { flex: 1 },
  menuLabel: { color: Colors.textPrimary, fontSize: FontSize.bodyLarge, fontWeight: '600' },
  menuDesc: { color: Colors.textTertiary, fontSize: FontSize.small, marginTop: 2 },
  disclaimer: {
    flexDirection: 'row', alignItems: 'flex-start', gap: 8,
    backgroundColor: 'rgba(59,130,246,0.06)', padding: 12, borderRadius: 8, marginTop: 16,
  },
  disclaimerText: { color: Colors.textTertiary, fontSize: FontSize.small, flex: 1, lineHeight: 18 },
});
