import React, { useEffect, useState, useCallback } from 'react';
import {
  View, Text, ScrollView, StyleSheet, TouchableOpacity,
  ActivityIndicator, RefreshControl, Linking,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { Colors, Spacing, FontSize } from '../src/constants/theme';

const CATEGORY_COLORS: Record<string, string> = {
  'Company Update': Colors.brandPrimary,
  'Mutual Fund': Colors.warning,
  'Result': Colors.positive,
  'Board Meeting': Colors.textSecondary,
};

export default function GuidanceScreen() {
  const router = useRouter();
  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [loadingMore, setLoadingMore] = useState(false);

  const loadData = useCallback(async (pageNum = 1, append = false) => {
    try {
      const res = await fetch(`https://bmia.pesmifs.com/api/guidance?page=${pageNum}&limit=20`);
      const data = await res.json();
      const newItems = data?.items || [];
      setItems(prev => append ? [...prev, ...newItems] : newItems);
      setTotal(data?.total || 0);
      setTotalPages(data?.pages || 0);
      setPage(pageNum);
    } catch (e) {
      console.error('Guidance fetch error:', e);
    } finally {
      setLoading(false);
      setRefreshing(false);
      setLoadingMore(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const onRefresh = () => { setRefreshing(true); loadData(1); };
  const loadMore = () => {
    if (page < totalPages && !loadingMore) {
      setLoadingMore(true);
      loadData(page + 1, true);
    }
  };

  const formatDate = (dateStr: string) => {
    if (!dateStr) return '';
    const d = new Date(dateStr);
    return d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' });
  };

  if (loading) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.centered}>
          <ActivityIndicator size="large" color={Colors.brandPrimary} />
          <Text style={styles.loadingText}>Loading Guidance...</Text>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <View style={styles.header}>
        <TouchableOpacity testID="guidance-back" onPress={() => router.back()}>
          <Ionicons name="arrow-back" size={24} color={Colors.textPrimary} />
        </TouchableOpacity>
        <View style={{ flex: 1, marginLeft: 12 }}>
          <Text style={styles.headerTitle}>Market Guidance</Text>
          <Text style={styles.headerSub}>{total.toLocaleString()} BSE filings & disclosures</Text>
        </View>
      </View>

      <ScrollView
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={Colors.brandPrimary} />}
        contentContainerStyle={styles.scrollContent}
        onMomentumScrollEnd={(e) => {
          const { layoutMeasurement, contentOffset, contentSize } = e.nativeEvent;
          if (layoutMeasurement.height + contentOffset.y >= contentSize.height - 200) {
            loadMore();
          }
        }}
      >
        {items.length === 0 ? (
          <View style={styles.empty}>
            <Ionicons name="book-outline" size={48} color={Colors.textTertiary} />
            <Text style={styles.emptyText}>No guidance items found</Text>
          </View>
        ) : (
          items.map((item: any, i: number) => {
            const catColor = CATEGORY_COLORS[item.category] || Colors.textTertiary;
            return (
              <TouchableOpacity
                key={item.news_id || i}
                style={styles.guidanceCard}
                testID={`guidance-item-${i}`}
                onPress={() => {
                  if (item.pdf_url) {
                    Linking.openURL(item.pdf_url);
                  }
                }}
                activeOpacity={0.7}
              >
                <View style={styles.cardTop}>
                  <View style={[styles.categoryPill, { backgroundColor: catColor + '18' }]}>
                    <Text style={[styles.categoryText, { color: catColor }]}>{item.category || 'Filing'}</Text>
                  </View>
                  {item.critical && (
                    <View style={styles.criticalPill}>
                      <Ionicons name="alert" size={10} color={Colors.negative} />
                      <Text style={styles.criticalText}>Critical</Text>
                    </View>
                  )}
                  <Text style={styles.dateText}>{formatDate(item.news_date)}</Text>
                </View>

                <Text style={styles.headline} numberOfLines={3}>{item.headline}</Text>

                <View style={styles.stockRow}>
                  <Ionicons name="business" size={12} color={Colors.brandPrimary} />
                  <Text style={styles.stockName} numberOfLines={1}>{item.stock_name}</Text>
                  {item.stock_symbol && (
                    <View style={styles.symbolPill}>
                      <Text style={styles.symbolText}>{item.stock_symbol}</Text>
                    </View>
                  )}
                </View>

                <View style={styles.metaRow}>
                  {item.pdf_text_length > 0 && (
                    <View style={styles.metaChip}>
                      <Ionicons name="document-text" size={10} color={Colors.textTertiary} />
                      <Text style={styles.metaText}>{(item.pdf_text_length / 1000).toFixed(1)}k chars</Text>
                    </View>
                  )}
                  {item.pdf_url && (
                    <View style={styles.metaChip}>
                      <Ionicons name="link" size={10} color={Colors.brandPrimary} />
                      <Text style={[styles.metaText, { color: Colors.brandPrimary }]}>View PDF</Text>
                    </View>
                  )}
                  {item.pdf_extracted && (
                    <View style={styles.metaChip}>
                      <Ionicons name="checkmark-circle" size={10} color={Colors.positive} />
                      <Text style={[styles.metaText, { color: Colors.positive }]}>Extracted</Text>
                    </View>
                  )}
                </View>
              </TouchableOpacity>
            );
          })
        )}

        {loadingMore && (
          <View style={styles.loadMoreRow}>
            <ActivityIndicator size="small" color={Colors.brandPrimary} />
            <Text style={styles.loadMoreText}>Loading more...</Text>
          </View>
        )}

        {page < totalPages && !loadingMore && (
          <TouchableOpacity testID="load-more-btn" style={styles.loadMoreBtn} onPress={loadMore}>
            <Text style={styles.loadMoreBtnText}>Load More ({page}/{totalPages})</Text>
          </TouchableOpacity>
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
    flexDirection: 'row', alignItems: 'center',
    paddingHorizontal: Spacing.base, paddingVertical: 12, borderBottomWidth: 1, borderBottomColor: Colors.border,
  },
  headerTitle: { color: Colors.textPrimary, fontSize: FontSize.h4, fontWeight: '700' },
  headerSub: { color: Colors.textTertiary, fontSize: FontSize.tiny, marginTop: 2 },
  scrollContent: { padding: Spacing.base },
  empty: { alignItems: 'center', paddingTop: 60 },
  emptyText: { color: Colors.textTertiary, fontSize: FontSize.body, marginTop: 12 },
  guidanceCard: {
    backgroundColor: Colors.surface, borderRadius: 8, borderWidth: 1, borderColor: Colors.border,
    padding: 12, marginBottom: 8,
  },
  cardTop: { flexDirection: 'row', alignItems: 'center', gap: 6, marginBottom: 6 },
  categoryPill: { paddingHorizontal: 6, paddingVertical: 2, borderRadius: 3 },
  categoryText: { fontSize: 9, fontWeight: '700', letterSpacing: 0.5, textTransform: 'uppercase' },
  criticalPill: {
    flexDirection: 'row', alignItems: 'center', gap: 2,
    backgroundColor: 'rgba(239,68,68,0.12)', paddingHorizontal: 5, paddingVertical: 2, borderRadius: 3,
  },
  criticalText: { color: Colors.negative, fontSize: 9, fontWeight: '700' },
  dateText: { color: Colors.textTertiary, fontSize: FontSize.tiny, marginLeft: 'auto', fontVariant: ['tabular-nums'] },
  headline: { color: Colors.textPrimary, fontSize: FontSize.body, fontWeight: '600', lineHeight: 20 },
  stockRow: { flexDirection: 'row', alignItems: 'center', gap: 6, marginTop: 8 },
  stockName: { color: Colors.textSecondary, fontSize: FontSize.small, flex: 1 },
  symbolPill: { backgroundColor: Colors.surfaceElevated, paddingHorizontal: 6, paddingVertical: 2, borderRadius: 3 },
  symbolText: { color: Colors.brandPrimary, fontSize: FontSize.tiny, fontWeight: '700', letterSpacing: 0.5 },
  metaRow: { flexDirection: 'row', gap: 8, marginTop: 8 },
  metaChip: { flexDirection: 'row', alignItems: 'center', gap: 3 },
  metaText: { color: Colors.textTertiary, fontSize: 9, fontWeight: '600' },
  loadMoreRow: { flexDirection: 'row', justifyContent: 'center', alignItems: 'center', gap: 8, paddingVertical: 16 },
  loadMoreText: { color: Colors.textTertiary, fontSize: FontSize.small },
  loadMoreBtn: {
    alignSelf: 'center', backgroundColor: Colors.surface, borderWidth: 1, borderColor: Colors.border,
    paddingHorizontal: 20, paddingVertical: 10, borderRadius: 8,
  },
  loadMoreBtnText: { color: Colors.brandPrimary, fontSize: FontSize.small, fontWeight: '600' },
});
