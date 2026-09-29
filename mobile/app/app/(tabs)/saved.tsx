import { FlatList, View, StyleSheet, Pressable } from "react-native";
import { useRouter } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { Screen } from "@/components/Screen";
import { AppText } from "@/components/AppText";
import { space } from "@/constants/theme";
import { useColors } from "@/lib/useTheme";
import { useLibraryStore } from "@/lib/store";

export default function SavedScreen() {
  const colors = useColors();
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const saved = useLibraryStore((s) => s.saved);
  const toggleSaved = useLibraryStore((s) => s.toggleSaved);

  return (
    <Screen>
      <FlatList
        data={saved}
        keyExtractor={(s) =>
          `${s.site}:${s.lecturerSlug}/${s.courseSlug}/${s.sessionId}`
        }
        contentContainerStyle={[
          styles.content,
          { paddingBottom: insets.bottom + space.xl },
        ]}
        ListHeaderComponent={
          <View style={styles.hero}>
            <AppText variant="display">فهرست من</AppText>
            <AppText variant="body" tone="soft">
              جلساتی که برای بازگشت ذخیره کرده‌اید
            </AppText>
            <View style={[styles.rule, { backgroundColor: colors.line }]} />
          </View>
        }
        ListEmptyComponent={
          <View style={styles.empty}>
            <AppText variant="title" style={styles.emptyTitle}>
              فهرستی خالی است
            </AppText>
            <AppText variant="body" tone="mist" style={styles.emptyBody}>
              هنگام پخش یک جلسه، «افزودن به فهرست من» را بزنید.
            </AppText>
          </View>
        }
        renderItem={({ item }) => (
          <Pressable
            style={({ pressed }) => [styles.row, { borderBottomColor: colors.line }, pressed && { opacity: 0.7 }]}
            onPress={() =>
              router.push({
                pathname: "/player/[lecturer]/[course]/[session]",
                params: {
                  lecturer: item.lecturerSlug,
                  course: item.courseSlug,
                  session: item.sessionId,
                },
              })
            }
          >
            <View style={styles.body}>
              <AppText variant="title" numberOfLines={2}>
                {item.title}
              </AppText>
              <AppText variant="caption" tone="mist">
                {item.lecturerName} · {item.courseTitle}
              </AppText>
            </View>
            <Pressable
              onPress={() => toggleSaved(item)}
              hitSlop={12}
              accessibilityLabel="حذف از فهرست"
            >
              <AppText variant="meta" tone="copper">
                حذف
              </AppText>
            </Pressable>
          </Pressable>
        )}
      />
    </Screen>
  );
}

const styles = StyleSheet.create({
  content: { paddingHorizontal: space.lg, paddingTop: space.md },
  hero: { gap: 6, paddingBottom: space.md },
  rule: {
    height: StyleSheet.hairlineWidth,
    
    marginTop: space.lg,
  },
  empty: {
    paddingVertical: space.xxl,
    alignItems: "center",
    gap: space.sm,
  },
  emptyTitle: { textAlign: "center" },
  emptyBody: { textAlign: "center", maxWidth: 280 },
  row: {
    flexDirection: "row",
    alignItems: "center",
    gap: space.md,
    paddingVertical: 14,
    borderBottomWidth: StyleSheet.hairlineWidth,
    
    minHeight: 64,
  },
  body: { flex: 1, gap: 2 },
});
