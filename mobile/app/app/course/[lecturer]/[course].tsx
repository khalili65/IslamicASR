import { useEffect, useLayoutEffect, useState } from "react";
import {
  FlatList,
  View,
  StyleSheet,
  ActivityIndicator,
  Pressable,
} from "react-native";
import { useLocalSearchParams, useNavigation, useRouter } from "expo-router";
import { Screen } from "@/components/Screen";
import { AppText } from "@/components/AppText";
import { SessionRow } from "@/components/Rows";
import { colors, space } from "@/constants/theme";
import { useLibraryStore } from "@/lib/store";
import { loadCourse } from "@/lib/api";
import type { CourseIndex } from "@/lib/types";
import { toPersianDigits } from "@/lib/format";

export default function CourseScreen() {
  const { lecturer: lecturerSlug, course: courseSlug } = useLocalSearchParams<{
    lecturer: string;
    course: string;
  }>();
  const lecturer = useLibraryStore((s) => s.findLecturer(lecturerSlug));
  const navigation = useNavigation();
  const router = useRouter();
  const [course, setCourse] = useState<CourseIndex | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!lecturer) return;
    let cancelled = false;
    setLoading(true);
    loadCourse(lecturer, courseSlug)
      .then((c) => {
        if (!cancelled) {
          setCourse(c);
          setError(null);
        }
      })
      .catch((e) => {
        if (!cancelled)
          setError(e instanceof Error ? e.message : "خطا");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [lecturer, courseSlug]);

  useLayoutEffect(() => {
    navigation.setOptions({ title: course?.title ?? "درس" });
  }, [navigation, course?.title]);

  if (!lecturer) {
    return (
      <Screen>
        <View style={styles.pad}>
          <AppText tone="mist">استاد پیدا نشد.</AppText>
        </View>
      </Screen>
    );
  }

  if (loading) {
    return (
      <Screen>
        <View style={styles.center}>
          <ActivityIndicator color={colors.copper} />
        </View>
      </Screen>
    );
  }

  if (error || !course) {
    return (
      <Screen>
        <View style={styles.center}>
          <AppText variant="title">بارگذاری نشد</AppText>
          <Pressable
            onPress={() => {
              setLoading(true);
              loadCourse(lecturer, courseSlug)
                .then(setCourse)
                .catch((e) =>
                  setError(e instanceof Error ? e.message : "خطا"),
                )
                .finally(() => setLoading(false));
            }}
            style={styles.retry}
          >
            <AppText tone="copper">تلاش دوباره</AppText>
          </Pressable>
        </View>
      </Screen>
    );
  }

  return (
    <Screen>
      <FlatList
        data={course.sessions}
        keyExtractor={(s) => s.id}
        contentContainerStyle={styles.content}
        ListHeaderComponent={
          <View style={styles.hero}>
            <AppText variant="display" style={styles.title}>
              {course.title}
            </AppText>
            {course.description ? (
              <AppText variant="body" tone="soft" style={styles.desc}>
                {course.description}
              </AppText>
            ) : null}
            <AppText variant="meta" tone="mist" style={styles.meta}>
              {toPersianDigits(course.sessionCount)} جلسه
              {course.totalDurationText
                ? ` · ${toPersianDigits(course.totalDurationText)}`
                : ""}
            </AppText>
            <View style={styles.rule} />
          </View>
        }
        renderItem={({ item }) => (
          <SessionRow
            index={item.index}
            title={item.title}
            durationText={item.durationText}
            onPress={() =>
              router.push({
                pathname: "/player/[lecturer]/[course]/[session]",
                params: {
                  lecturer: lecturer.slug,
                  course: course.slug,
                  session: item.id,
                },
              })
            }
          />
        )}
      />
    </Screen>
  );
}

const styles = StyleSheet.create({
  content: { paddingHorizontal: space.lg, paddingBottom: space.xxl },
  pad: { padding: space.lg },
  center: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    gap: space.md,
  },
  hero: { paddingTop: space.sm, paddingBottom: space.md, gap: 6 },
  title: { textAlign: "right" },
  desc: { marginTop: 4 },
  meta: { marginTop: space.sm },
  rule: {
    height: StyleSheet.hairlineWidth,
    backgroundColor: colors.line,
    marginTop: space.lg,
  },
  retry: { minHeight: 44, justifyContent: "center" },
});
