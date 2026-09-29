import { useCallback } from "react";
import {
  FlatList,
  RefreshControl,
  View,
  StyleSheet,
  ActivityIndicator,
  Pressable,
} from "react-native";
import { useRouter } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { Screen } from "@/components/Screen";
import { AppText } from "@/components/AppText";
import { LecturerRow } from "@/components/Rows";
import { APP_TITLE, colors, space } from "@/constants/theme";
import { useLibraryStore } from "@/lib/store";

export default function LibraryScreen() {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const lecturers = useLibraryStore((s) => s.lecturers);
  const loading = useLibraryStore((s) => s.loading);
  const error = useLibraryStore((s) => s.error);
  const load = useLibraryStore((s) => s.load);

  const onRefresh = useCallback(() => {
    load();
  }, [load]);

  return (
    <Screen>
      <FlatList
        data={lecturers}
        keyExtractor={(l) => `${l.site}:${l.slug}`}
        contentContainerStyle={[
          styles.content,
          { paddingBottom: insets.bottom + space.xl },
        ]}
        refreshControl={
          <RefreshControl
            refreshing={loading && lecturers.length > 0}
            onRefresh={onRefresh}
            tintColor={colors.copper}
          />
        }
        ListHeaderComponent={
          <View style={styles.hero}>
            <AppText variant="caption" tone="mist" style={styles.center}>
              بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ
            </AppText>
            <AppText variant="display" style={styles.brand}>
              {APP_TITLE}
            </AppText>
            <AppText variant="body" tone="mist" style={styles.center}>
              سخنرانی و تفسیر
            </AppText>
          </View>
        }
        ListEmptyComponent={
          <View style={styles.empty}>
            {loading ? (
              <ActivityIndicator color={colors.copper} />
            ) : error ? (
              <>
                <AppText variant="title" style={styles.center}>
                  بارگذاری نشد
                </AppText>
                <AppText variant="body" tone="mist" style={styles.center}>
                  اتصال را بررسی کنید و دوباره تلاش کنید.
                </AppText>
                <Pressable onPress={onRefresh} style={styles.retry}>
                  <AppText variant="meta" tone="copper">
                    تلاش دوباره
                  </AppText>
                </Pressable>
              </>
            ) : (
              <AppText variant="body" tone="mist" style={styles.center}>
                هنوز محتوایی نیست.
              </AppText>
            )}
          </View>
        }
        renderItem={({ item }) => (
          <LecturerRow
            lecturer={item}
            onPress={() =>
              router.push({
                pathname: "/lecturer/[slug]",
                params: { slug: item.slug },
              })
            }
          />
        )}
      />
    </Screen>
  );
}

const styles = StyleSheet.create({
  content: {
    paddingHorizontal: space.md,
    paddingTop: space.sm,
  },
  hero: {
    width: "100%",
    alignItems: "center",
    paddingTop: space.xl,
    paddingBottom: space.xl,
    paddingHorizontal: space.sm,
  },
  center: {
    textAlign: "center",
    writingDirection: "rtl",
    width: "100%",
  },
  brand: {
    textAlign: "center",
    writingDirection: "rtl",
    width: "100%",
    marginTop: 10,
    marginBottom: 8,
  },
  empty: {
    paddingVertical: space.xxl,
    alignItems: "center",
    gap: space.sm,
  },
  retry: {
    marginTop: space.sm,
    minHeight: 44,
    justifyContent: "center",
  },
});
