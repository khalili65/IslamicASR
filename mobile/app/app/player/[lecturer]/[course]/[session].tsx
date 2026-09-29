import { useEffect, useState } from "react";
import {
  View,
  StyleSheet,
  ActivityIndicator,
  Pressable,
} from "react-native";
import { useLocalSearchParams, useRouter } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import { Screen } from "@/components/Screen";
import { AppText } from "@/components/AppText";
import { LecturePlayer } from "@/components/LecturePlayer";
import { colors, space } from "@/constants/theme";
import { useLibraryStore } from "@/lib/store";
import { loadCues, loadSession } from "@/lib/api";
import { resolveMediaUrl } from "@/lib/format";
import type { Cue, SessionPayload } from "@/lib/types";

export default function PlayerScreen() {
  const { lecturer: lecturerSlug, course, session } = useLocalSearchParams<{
    lecturer: string;
    course: string;
    session: string;
  }>();
  const lecturer = useLibraryStore((s) => s.findLecturer(lecturerSlug));
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const [payload, setPayload] = useState<SessionPayload | null>(null);
  const [cues, setCues] = useState<Cue[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const isSaved = useLibraryStore((s) =>
    s.isSaved(lecturerSlug, course, session),
  );
  const toggleSaved = useLibraryStore((s) => s.toggleSaved);
  const courseTitle =
    lecturer?.courses.find((c) => c.slug === course)?.title ?? course;

  useEffect(() => {
    if (!lecturer) return;
    let cancelled = false;
    setLoading(true);
    Promise.all([
      loadSession(lecturer, course, session),
      loadCues(lecturer, course, session).catch(() => ({ cues: [] as Cue[] })),
    ])
      .then(([sess, cuesFile]) => {
        if (cancelled) return;
        setPayload(sess);
        setCues(cuesFile.cues ?? []);
        setError(null);
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : "خطا");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [lecturer, course, session]);

  function goBack() {
    if (router.canGoBack()) router.back();
    else
      router.replace({
        pathname: "/course/[lecturer]/[course]",
        params: { lecturer: lecturerSlug, course },
      });
  }

  function goToCourse() {
    router.push({
      pathname: "/course/[lecturer]/[course]",
      params: { lecturer: lecturerSlug, course },
    });
  }

  if (!lecturer) {
    return (
      <Screen>
        <View style={[styles.center, { paddingTop: insets.top }]}>
          <AppText tone="mist">استاد پیدا نشد.</AppText>
          <Pressable onPress={() => router.back()} hitSlop={12}>
            <AppText tone="ink">بازگشت</AppText>
          </Pressable>
        </View>
      </Screen>
    );
  }

  if (loading) {
    return (
      <Screen>
        <View style={styles.center}>
          <ActivityIndicator color={colors.ink} />
        </View>
      </Screen>
    );
  }

  if (error || !payload) {
    return (
      <Screen>
        <View style={styles.center}>
          <AppText variant="title">جلسه بارگذاری نشد</AppText>
          <Pressable onPress={goBack} style={styles.retry} hitSlop={12}>
            <AppText tone="ink">بازگشت</AppText>
          </Pressable>
        </View>
      </Screen>
    );
  }

  const audioUrl = resolveMediaUrl(payload.audio?.url, lecturer.mediaBase);

  return (
    <View style={[styles.root, { paddingTop: insets.top }]}>
      <View style={styles.header}>
        <Pressable
          onPress={goBack}
          style={styles.backBtn}
          accessibilityLabel="بازگشت"
          hitSlop={8}
        >
          <Ionicons name="chevron-back" size={22} color={colors.ink} />
        </Pressable>
        <View style={styles.headerText}>
          <Pressable onPress={goToCourse} hitSlop={6}>
            <AppText variant="caption" tone="mist" numberOfLines={1} style={styles.courseLink}>
              {courseTitle}
            </AppText>
          </Pressable>
          <AppText variant="title" numberOfLines={2} style={styles.sessionTitle}>
            {payload.title}
          </AppText>
        </View>
        <View style={styles.backBtn} />
      </View>

      {audioUrl ? (
        <View style={styles.playerWrap}>
          <LecturePlayer
            session={payload}
            cues={cues}
            audioUrl={audioUrl}
            dataBase={lecturer.dataBase}
            lecturerName={lecturer.name}
            courseTitle={courseTitle}
            saved={isSaved}
            onToggleSave={() =>
              toggleSaved({
                lecturerSlug: lecturer.slug,
                courseSlug: course,
                sessionId: session,
                title: payload.title,
                courseTitle,
                lecturerName: lecturer.name,
                site: lecturer.site,
              })
            }
          />
        </View>
      ) : (
        <View style={styles.center}>
          <AppText tone="mist">فایل صوتی در دسترس نیست.</AppText>
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.parchment },
  playerWrap: { flex: 1, minHeight: 0 },
  center: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    gap: space.md,
    padding: space.lg,
  },
  header: {
    flexDirection: "row",
    alignItems: "flex-start",
    paddingHorizontal: space.sm,
    paddingTop: space.xs,
    paddingBottom: space.sm,
    gap: 4,
  },
  backBtn: {
    width: 44,
    height: 44,
    alignItems: "center",
    justifyContent: "center",
  },
  headerText: {
    flex: 1,
    minWidth: 0,
    paddingTop: 6,
    gap: 4,
  },
  courseLink: {
    textAlign: "center",
    writingDirection: "rtl",
  },
  sessionTitle: {
    textAlign: "center",
    writingDirection: "rtl",
    fontSize: 16,
    lineHeight: 24,
  },
  retry: { minHeight: 44, justifyContent: "center" },
});
