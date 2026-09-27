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
import { toPersianDigits } from "@/lib/format";

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

  const courseTotal = lecturers.reduce((n, l) => n + l.courses.length, 0);

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
            <AppText variant="caption" tone="copper" style={styles.center}>
              بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ
            </AppText>
            <AppText variant="display" style={styles.brand}>
              {APP_TITLE}
            </AppText>
            <AppText variant="body" tone="soft" style={styles.center}>
              سخنرانی و تفسیر، از همهٔ استادان
            </AppText>
            {lecturers.length > 0 ? (
              <AppText variant="meta" tone="mist" style={styles.metaLine}>
                {toPersianDigits(lecturers.length)} استاد
                {"  •  "}
                {toPersianDigits(courseTotal)} دوره
              </AppText>
            ) : null}
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
    paddingTop: space.md,
    paddingBottom: space.xl,
    paddingHorizontal: space.sm,
    gap: 0,
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
  metaLine: {
    textAlign: "center",
    writingDirection: "rtl",
    width: "100%",
    marginTop: 12,
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
