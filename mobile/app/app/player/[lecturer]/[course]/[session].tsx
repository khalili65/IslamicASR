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
import { space } from "@/constants/theme";
import { useColors } from "@/lib/useTheme";
import { useLibraryStore } from "@/lib/store";
import { loadCues, loadSession } from "@/lib/api";
import { resolveMediaUrl } from "@/lib/format";
import {
  loadOfflineSession,
  resolveOfflinePaths,
  type OfflineLocalPaths,
} from "@/lib/offlineSession";
import type { Cue, SessionPayload } from "@/lib/types";

export default function PlayerScreen() {
  const { lecturer: lecturerSlug, course, session } = useLocalSearchParams<{
    lecturer: string;
    course: string;
    session: string;
  }>();
  const colors = useColors();
  const lecturer = useLibraryStore((s) => s.findLecturer(lecturerSlug));
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const [payload, setPayload] = useState<SessionPayload | null>(null);
  const [cues, setCues] = useState<Cue[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [offlinePaths, setOfflinePaths] = useState<OfflineLocalPaths | null>(
    null,
  );

  const isSaved = useLibraryStore((s) =>
    s.isSaved(lecturerSlug, course, session),
  );
  const toggleSaved = useLibraryStore((s) => s.toggleSaved);
  const courseTitle =
    lecturer?.courses.find((c) => c.slug === course)?.title ?? course;

  useEffect(() => {
    let cancelled = false;
    setLoading(true);

    const key = {
      lecturerSlug,
      courseSlug: course,
      sessionId: session,
    };

    (async () => {
      const local = await loadOfflineSession(key);
      const paths = await resolveOfflinePaths(key);
      if (cancelled) return;
      if (paths) setOfflinePaths(paths);

      if (lecturer) {
        try {
          const [sess, cuesFile] = await Promise.all([
            loadSession(lecturer, course, session),
            loadCues(lecturer, course, session).catch(() => ({
              cues: [] as Cue[],
            })),
          ]);
          if (cancelled) return;
          setPayload(sess);
          setCues(cuesFile.cues ?? []);
          setError(null);
          setLoading(false);
          return;
        } catch (e) {
          if (local) {
            if (cancelled) return;
            setPayload(local.session);
            setCues(local.cues);
            setError(null);
            setLoading(false);
            return;
          }
          if (!cancelled) {
            setError(e instanceof Error ? e.message : "خطا");
            setLoading(false);
          }
          return;
        }
      }

      // No lecturer in memory (e.g. cold start offline) — use local pack if any.
      if (local) {
        setPayload(local.session);
        setCues(local.cues);
        setError(null);
        setLoading(false);
        return;
      }

      setError("استاد پیدا نشد.");
      setLoading(false);
    })();

    return () => {
      cancelled = true;
    };
  }, [lecturer, course, session, lecturerSlug]);

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
        <View style={[styles.center, { paddingTop: insets.top }]}>
          <AppText variant="title">جلسه بارگذاری نشد</AppText>
          <AppText tone="mist">{error || "خطا"}</AppText>
          <Pressable onPress={goBack} style={styles.retry} hitSlop={12}>
            <AppText tone="ink">بازگشت</AppText>
          </Pressable>
        </View>
      </Screen>
    );
  }

  const remoteAudioUrl = lecturer
    ? resolveMediaUrl(payload.audio?.url, lecturer.mediaBase)
    : "";
  const audioUrl = offlinePaths?.audioUri || remoteAudioUrl;
  const resolvedDataBase = lecturer?.dataBase ?? "";

  const displayCourseTitle = courseTitle;
  const displayLecturerName = lecturer?.name;

  return (
    <View
      style={[
        styles.root,
        { paddingTop: insets.top, backgroundColor: colors.parchment },
      ]}
    >
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
              {displayCourseTitle}
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
            audioUrl={remoteAudioUrl || audioUrl}
            dataBase={resolvedDataBase}
            lecturerSlug={lecturerSlug}
            courseSlug={course}
            site={lecturer?.site ?? "portal"}
            lecturerName={displayLecturerName}
            courseTitle={displayCourseTitle}
            initialOfflinePaths={offlinePaths}
            onOfflineChange={setOfflinePaths}
            saved={isSaved}
            onToggleSave={() =>
              toggleSaved({
                lecturerSlug: lecturerSlug,
                courseSlug: course,
                sessionId: session,
                title: payload.title,
                courseTitle: displayCourseTitle,
                lecturerName: displayLecturerName || "",
                site: lecturer?.site ?? "portal",
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
  root: { flex: 1 },
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
