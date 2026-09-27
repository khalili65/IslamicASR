import { useEffect, useState } from "react";
import {
  View,
  StyleSheet,
  ActivityIndicator,
  Pressable,
} from "react-native";
import { useLocalSearchParams, useRouter } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";
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
        if (!cancelled)
          setError(e instanceof Error ? e.message : "خطا");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [lecturer, course, session]);

  if (!lecturer) {
    return (
      <Screen>
        <View style={[styles.center, { paddingTop: insets.top }]}>
          <AppText tone="mist">استاد پیدا نشد.</AppText>
          <Pressable onPress={() => router.back()}>
            <AppText tone="copper">بازگشت</AppText>
          </Pressable>
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

  if (error || !payload) {
    return (
      <Screen>
        <View style={styles.center}>
          <AppText variant="title">جلسه بارگذاری نشد</AppText>
          <Pressable onPress={() => router.back()} style={styles.retry}>
            <AppText tone="copper">بازگشت</AppText>
          </Pressable>
        </View>
      </Screen>
    );
  }

  const audioUrl = resolveMediaUrl(payload.audio?.url, lecturer.mediaBase);

  return (
    <View style={[styles.root, { paddingTop: insets.top }]}>
      <View style={styles.topBar}>
        <Pressable
          onPress={() => router.back()}
          style={styles.back}
          accessibilityLabel="بازگشت"
        >
          <AppText variant="meta" tone="copper">
            بازگشت
          </AppText>
        </Pressable>
        <AppText variant="meta" tone="mist" numberOfLines={1} style={styles.topTitle}>
          {lecturer.name}
        </AppText>
        <View style={styles.back} />
      </View>
      {audioUrl ? (
        <LecturePlayer
          session={payload}
          cues={cues}
          audioUrl={audioUrl}
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
  center: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    gap: space.md,
    padding: space.lg,
  },
  topBar: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: space.md,
    paddingVertical: space.sm,
    backgroundColor: colors.parchment,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.line,
  },
  back: { minWidth: 64, minHeight: 44, justifyContent: "center" },
  topTitle: { flex: 1, textAlign: "center" },
  retry: { minHeight: 44, justifyContent: "center" },
});
