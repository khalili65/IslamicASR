import { useCallback, useEffect, useMemo, useState } from "react";
import {
  View,
  StyleSheet,
  Pressable,
  ActivityIndicator,
  Modal,
  Alert,
  Share,
  ActionSheetIOS,
  Platform,
  useWindowDimensions,
  type LayoutChangeEvent,
  type GestureResponderEvent,
} from "react-native";
import {
  useAudioPlayer,
  useAudioPlayerStatus,
  setAudioModeAsync,
} from "expo-audio";
import { useFocusEffect } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import { AppText } from "./AppText";
import { DocumentModal } from "./DocumentModal";
import { colors, radii, space, type } from "@/constants/theme";
import { findCueIndex, formatClock, toPersianDigits } from "@/lib/format";
import {
  downloadSessionItem,
  type DownloadItem,
} from "@/lib/sessionDownload";
import type { Cue, SessionPayload } from "@/lib/types";

const RATES = [0.75, 1, 1.25, 1.5, 2] as const;

type DocKind = "full" | "book" | "summary" | null;

type Props = {
  session: SessionPayload;
  cues: Cue[];
  audioUrl: string;
  dataBase: string;
  lecturerName?: string;
  courseTitle?: string;
  onToggleSave?: () => void;
  saved?: boolean;
};

export function LecturePlayer({
  session,
  cues,
  audioUrl,
  dataBase,
  lecturerName,
  courseTitle,
  onToggleSave,
  saved,
}: Props) {
  const player = useAudioPlayer(audioUrl, { updateInterval: 100 });
  const status = useAudioPlayerStatus(player);
  const insets = useSafeAreaInsets();
  const { width: windowWidth, height: windowHeight } = useWindowDimensions();
  const compact = windowHeight < 740;
  const panelMax = Math.min(windowWidth, 520);
  const actionsBottomPad = Math.max(insets.bottom, space.sm) + space.md;

  const [rate, setRate] = useState(1);
  const [subtitlesOn, setSubtitlesOn] = useState(true);
  const [speedOpen, setSpeedOpen] = useState(false);
  const [downloadOpen, setDownloadOpen] = useState(false);
  const [docKind, setDocKind] = useState<DocKind>(null);
  const [busyDownload, setBusyDownload] = useState(false);
  const [trackWidth, setTrackWidth] = useState(0);

  const position = status.currentTime ?? 0;
  const duration =
    status.duration > 0
      ? status.duration
      : (session.audio?.duration ?? 0);
  const playing = status.playing;
  const ready = status.isLoaded;

  const cueIndex = useMemo(
    () => findCueIndex(cues, position),
    [cues, position],
  );
  const currentCue = cueIndex >= 0 ? cues[cueIndex] : null;
  const prevCue = cueIndex > 0 ? cues[cueIndex - 1] : null;
  const nextCue =
    cueIndex >= 0 && cueIndex < cues.length - 1 ? cues[cueIndex + 1] : null;

  useEffect(() => {
    setAudioModeAsync({
      playsInSilentMode: true,
      shouldPlayInBackground: true,
      interruptionMode: "doNotMix",
    }).catch(() => {});
  }, []);

  // Leaving the player (back / another session) must stop audio so streams don't overlap.
  useFocusEffect(
    useCallback(() => {
      return () => {
        try {
          player.pause();
        } catch {
          /* already released */
        }
      };
    }, [player]),
  );

  useEffect(() => {
    if (!ready) return;
    try {
      player.setPlaybackRate(rate);
    } catch {
      /* ignore */
    }
  }, [rate, ready, player]);

  useEffect(() => {
    return () => {
      try {
        player.pause();
      } catch {
        /* ignore */
      }
    };
  }, [player]);

  function toggle() {
    if (!ready) return;
    if (playing) player.pause();
    else player.play();
  }

  function seekBy(delta: number) {
    if (!ready) return;
    const next = Math.max(
      0,
      Math.min(position + delta, duration || position + delta),
    );
    player.seekTo(next);
  }

  function seekTo(seconds: number) {
    if (!ready) return;
    player.seekTo(Math.max(0, seconds));
    player.play();
  }

  const preferRaw =
    Boolean(session.hasRawTranscript) || session.subtitleSource === "raw";
  const dataRoot = `${dataBase.replace(/\/$/, "")}/data/${session.lecturer}/${session.course}/${session.id}`;

  const hasFullText = Boolean(session.hasFullText ?? session.hasTranscript);
  const hasBook = Boolean(session.hasBook);
  const hasSummary = Boolean(session.hasSummary ?? session.summary);

  const downloadItems = useMemo(() => {
    const items: DownloadItem[] = [];
    const fullUrl = preferRaw
      ? `${dataRoot}.raw.txt`
      : `${dataRoot}.corrected.md`;
    if (hasFullText) {
      items.push({
        key: "full-txt",
        label: preferRaw ? "متن خام ASR (TXT)" : "متن کامل (TXT)",
        url: fullUrl,
        filename: preferRaw
          ? `${session.id}-متن-خام-asr.txt`
          : `${session.id}-متن-کامل.txt`,
        format: "txt",
      });
      items.push({
        key: "full-pdf",
        label: "متن کامل (PDF)",
        url: fullUrl,
        filename: `${session.id}-متن-کامل.pdf`,
        format: "pdf",
      });
    }
    if (hasBook) {
      const bookUrl = `${dataRoot}.book.md`;
      items.push({
        key: "book-txt",
        label: "نسخه کتابی (TXT)",
        url: bookUrl,
        filename: `${session.id}-نسخه-کتابی.txt`,
        format: "txt",
      });
      items.push({
        key: "book-pdf",
        label: "نسخه کتابی (PDF)",
        url: bookUrl,
        filename: `${session.id}-نسخه-کتابی.pdf`,
        format: "pdf",
      });
    }
    if (hasSummary) {
      const summaryUrl = `${dataRoot}.summary.md`;
      items.push({
        key: "summary-txt",
        label: "خلاصه (TXT)",
        url: summaryUrl,
        filename: `${session.id}-خلاصه.txt`,
        format: "txt",
      });
      items.push({
        key: "summary-pdf",
        label: "خلاصه (PDF)",
        url: summaryUrl,
        filename: `${session.id}-خلاصه.pdf`,
        format: "pdf",
      });
    }
    if (audioUrl) {
      items.push({
        key: "audio",
        label: "صوت",
        url: audioUrl,
        filename: session.audio?.filename || `${session.id}.m4a`,
        format: "audio",
      });
    }
    return items;
  }, [
    audioUrl,
    dataRoot,
    hasBook,
    hasFullText,
    hasSummary,
    preferRaw,
    session.audio?.filename,
    session.id,
  ]);

  async function shareSession() {
    try {
      const lines: string[] = [];
      if (courseTitle) lines.push(`دوره: ${courseTitle}`);
      lines.push(`جلسه: ${session.title}`);
      if (lecturerName) lines.push(`استاد: ${lecturerName}`);
      if (session.topic && session.topic !== session.title) {
        lines.push(`موضوع: ${session.topic}`);
      }
      const summary = session.summary?.trim();
      if (summary) {
        const clipped =
          summary.length > 280 ? `${summary.slice(0, 277).trim()}…` : summary;
        lines.push("", clipped);
      }
      await Share.share({
        title: session.title,
        message: lines.join("\n"),
      });
    } catch {
      /* dismissed */
    }
  }

  /** Builds a local TXT/PDF/audio file, then opens Save to Files via share sheet. */
  async function downloadFile(item: DownloadItem) {
    setDownloadOpen(false);
    setBusyDownload(true);
    try {
      await downloadSessionItem(item, { title: session.title });
    } catch {
      Alert.alert("خطا", "دانلود انجام نشد. اتصال را بررسی کنید.");
    } finally {
      setBusyDownload(false);
    }
  }

  function seekFromTrack(event: GestureResponderEvent) {
    if (!ready || !duration || trackWidth <= 0) return;
    const x = event.nativeEvent.locationX;
    // RTL bar: fill grows from the right (same as website), so left = end.
    const ratio = Math.max(0, Math.min(1, 1 - x / trackWidth));
    seekTo(ratio * duration);
  }

  function onTrackLayout(event: LayoutChangeEvent) {
    setTrackWidth(event.nativeEvent.layout.width);
  }

  function openDownloadMenu() {
    if (!downloadItems.length) return;
    if (Platform.OS === "ios") {
      ActionSheetIOS.showActionSheetWithOptions(
        {
          options: [...downloadItems.map((i) => i.label), "انصراف"],
          cancelButtonIndex: downloadItems.length,
          title: "دانلود",
        },
        (index) => {
          if (index >= downloadItems.length) return;
          void downloadFile(downloadItems[index]);
        },
      );
      return;
    }
    setDownloadOpen(true);
  }

  const docUrl =
    docKind === "full"
      ? preferRaw
        ? `${dataRoot}.raw.txt`
        : `${dataRoot}.corrected.md`
      : docKind === "book"
        ? `${dataRoot}.book.md`
        : docKind === "summary"
          ? `${dataRoot}.summary.md`
          : null;

  const docTitle =
    docKind === "full"
      ? "متن کامل"
      : docKind === "book"
        ? "نسخه کتابی"
        : docKind === "summary"
          ? "خلاصه"
          : "";

  return (
    <View style={styles.root}>
      {/* Subtitles — inset so it breathes on every phone */}
      <View style={styles.stageWrap}>
        <View style={[styles.stage, compact && styles.stageCompact]}>
          {subtitlesOn && currentCue ? (
            <>
              {!compact ? (
                <AppText
                  key={`prev-${cueIndex}`}
                  variant="caption"
                  tone="stageMuted"
                  style={styles.ghost}
                  numberOfLines={1}
                >
                  {prevCue?.text || " "}
                </AppText>
              ) : null}
              <AppText
                key={`cue-${cueIndex}`}
                variant="display"
                tone="stage"
                style={[styles.stageText, compact && styles.stageTextCompact]}
                numberOfLines={compact ? 3 : 4}
              >
                {currentCue.text}
              </AppText>
              {!compact ? (
                <AppText
                  key={`next-${cueIndex}`}
                  variant="caption"
                  tone="stageMuted"
                  style={styles.ghost}
                  numberOfLines={1}
                >
                  {nextCue?.text || " "}
                </AppText>
              ) : null}
            </>
          ) : (
            <AppText variant="body" tone="stageMuted" style={styles.stageIdle}>
              {!session.hasTranscript
                ? "متن این جلسه هنوز آماده نشده است"
                : subtitlesOn
                  ? "در انتظار شروع گفتار…"
                  : "زیرنویس خاموش است"}
            </AppText>
          )}
        </View>
      </View>

      <View
        style={[
          styles.panel,
          { paddingBottom: actionsBottomPad, maxWidth: panelMax },
        ]}
      >
        <Pressable
          onLayout={onTrackLayout}
          onPress={seekFromTrack}
          style={styles.trackHit}
          accessibilityLabel="جابجایی"
        >
          <View style={styles.track}>
            <View
              style={[
                styles.fill,
                {
                  width: `${duration > 0 ? Math.min(100, (position / duration) * 100) : 0}%`,
                },
              ]}
            />
          </View>
        </Pressable>
        <View style={styles.times}>
          <AppText variant="caption" tone="mist">
            {formatClock(duration)}
          </AppText>
          <AppText variant="caption" tone="mist">
            {formatClock(position)}
          </AppText>
        </View>

        {/* Classic transport — not a grid cell */}
        <View style={styles.transportRow}>
          <Pressable
            onPress={() =>
              session.hasTranscript && setSubtitlesOn((v) => !v)
            }
            disabled={!session.hasTranscript}
            style={[
              styles.metaChip,
              subtitlesOn && session.hasTranscript && styles.metaChipOn,
              !session.hasTranscript && { opacity: 0.35 },
            ]}
            accessibilityLabel="زیرنویس"
          >
            <AppText
              variant="meta"
              tone={subtitlesOn ? "ink" : "mist"}
              style={{ fontFamily: type.medium }}
            >
              CC
            </AppText>
          </Pressable>

          <View style={styles.transport}>
            {/* RTL timeline: left = toward end, right = toward start (same as website). */}
            <Pressable
              onPress={() => seekBy(15)}
              style={styles.sideBtn}
              accessibilityLabel="پانزده ثانیه جلو"
            >
              <Ionicons name="play-back-outline" size={26} color={colors.ink} />
            </Pressable>
            <Pressable
              onPress={toggle}
              disabled={!ready}
              style={({ pressed }) => [
                styles.play,
                compact && styles.playCompact,
                pressed && { opacity: 0.85 },
                !ready && { opacity: 0.5 },
              ]}
              accessibilityRole="button"
              accessibilityLabel={playing ? "توقف" : "پخش"}
            >
              {!ready ? (
                <ActivityIndicator color={colors.parchment} />
              ) : (
                <Ionicons
                  name={playing ? "pause" : "play"}
                  size={compact ? 24 : 28}
                  color={colors.parchment}
                  style={!playing ? { marginLeft: 3 } : undefined}
                />
              )}
            </Pressable>
            <Pressable
              onPress={() => seekBy(-15)}
              style={styles.sideBtn}
              accessibilityLabel="پانزده ثانیه عقب"
            >
              <Ionicons
                name="play-forward-outline"
                size={26}
                color={colors.ink}
              />
            </Pressable>
          </View>

          <Pressable
            onPress={() => setSpeedOpen(true)}
            style={[styles.metaChip, rate !== 1 && styles.metaChipOn]}
            accessibilityLabel="سرعت پخش"
          >
            <AppText variant="meta" tone={rate !== 1 ? "ink" : "mist"}>
              {toPersianDigits(rate)}×
            </AppText>
          </Pressable>
        </View>

        {/* Soft action strip — wraps on narrow phones */}
        <View style={styles.actions}>
          <ActionChip
            icon={saved ? "bookmark" : "bookmark-outline"}
            label={saved ? "ذخیره" : "فهرست"}
            active={saved}
            onPress={onToggleSave}
          />
          <ActionChip
            icon="share-outline"
            label="اشتراک"
            onPress={() => void shareSession()}
          />
          <ActionChip
            icon="download-outline"
            label={busyDownload ? "…" : "دانلود"}
            onPress={openDownloadMenu}
            disabled={!downloadItems.length || busyDownload}
          />
          {hasFullText ? (
            <ActionChip
              icon="document-text-outline"
              label="متن"
              onPress={() => setDocKind("full")}
            />
          ) : null}
          {hasBook ? (
            <ActionChip
              icon="book-outline"
              label="کتاب"
              onPress={() => setDocKind("book")}
            />
          ) : null}
          {hasSummary ? (
            <ActionChip
              icon="list-outline"
              label="خلاصه"
              onPress={() => setDocKind("summary")}
            />
          ) : null}
        </View>
      </View>

      <Modal
        visible={speedOpen}
        transparent
        animationType="fade"
        onRequestClose={() => setSpeedOpen(false)}
      >
        <Pressable style={styles.sheetBackdrop} onPress={() => setSpeedOpen(false)}>
          <View style={styles.sheet}>
            <AppText variant="meta" tone="mist" style={styles.sheetTitle}>
              سرعت پخش
            </AppText>
            {RATES.map((r) => (
              <Pressable
                key={r}
                style={[styles.sheetRow, rate === r && styles.sheetRowOn]}
                onPress={() => {
                  setRate(r);
                  setSpeedOpen(false);
                }}
              >
                <AppText variant="body">{toPersianDigits(r)}×</AppText>
              </Pressable>
            ))}
          </View>
        </Pressable>
      </Modal>

      <Modal
        visible={downloadOpen}
        transparent
        animationType="fade"
        onRequestClose={() => setDownloadOpen(false)}
      >
        <Pressable
          style={styles.sheetBackdrop}
          onPress={() => setDownloadOpen(false)}
        >
          <View style={styles.sheet}>
            <AppText variant="meta" tone="mist" style={styles.sheetTitle}>
              دانلود
            </AppText>
            {downloadItems.map((item) => (
              <Pressable
                key={item.key}
                style={styles.sheetRow}
                onPress={() => void downloadFile(item)}
              >
                <AppText variant="body">{item.label}</AppText>
              </Pressable>
            ))}
          </View>
        </Pressable>
      </Modal>

      <DocumentModal
        visible={docKind !== null}
        title={docTitle}
        url={docUrl}
        inlineText={docKind === "summary" ? session.summary : null}
        onClose={() => setDocKind(null)}
      />
    </View>
  );
}

function ActionChip({
  icon,
  label,
  onPress,
  active,
  disabled,
}: {
  icon: keyof typeof Ionicons.glyphMap;
  label: string;
  onPress?: () => void;
  active?: boolean;
  disabled?: boolean;
}) {
  return (
    <Pressable
      onPress={onPress}
      disabled={disabled || !onPress}
      style={({ pressed }) => [
        styles.chip,
        active && styles.chipOn,
        (disabled || !onPress) && { opacity: 0.4 },
        pressed && { opacity: 0.75 },
      ]}
    >
      <Ionicons
        name={icon}
        size={16}
        color={active ? colors.ink : colors.inkSoft}
      />
      <AppText
        variant="caption"
        tone={active ? "ink" : "mist"}
        numberOfLines={1}
      >
        {label}
      </AppText>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1 },
  stageWrap: {
    flex: 1,
    minHeight: 120,
    paddingHorizontal: space.md,
    paddingTop: space.xs,
  },
  stage: {
    flex: 1,
    backgroundColor: colors.stage,
    borderRadius: radii.lg,
    paddingHorizontal: space.lg,
    paddingVertical: space.lg,
    justifyContent: "center",
    gap: 8,
  },
  stageCompact: {
    paddingVertical: space.md,
    gap: 4,
  },
  ghost: {
    textAlign: "center",
    writingDirection: "rtl",
    opacity: 0.55,
    letterSpacing: 0,
  },
  stageText: {
    textAlign: "center",
    writingDirection: "rtl",
    fontSize: 22,
    lineHeight: 36,
    letterSpacing: 0,
  },
  stageTextCompact: {
    fontSize: 18,
    lineHeight: 30,
    letterSpacing: 0,
  },
  stageIdle: { textAlign: "center" },
  panel: {
    width: "100%",
    alignSelf: "center",
    paddingHorizontal: space.md,
    paddingTop: space.md,
    gap: space.md,
  },
  trackHit: {
    width: "100%",
    height: 28,
    justifyContent: "center",
  },
  track: {
    height: 3,
    backgroundColor: colors.parchmentDeep,
    borderRadius: radii.pill,
    overflow: "hidden",
    flexDirection: "row-reverse",
  },
  fill: {
    height: "100%",
    backgroundColor: colors.ink,
    borderRadius: radii.pill,
    alignSelf: "stretch",
  },
  times: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginTop: -10,
  },
  transportRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: space.xs,
  },
  transport: {
    flexDirection: "row",
    alignItems: "center",
    gap: space.lg,
  },
  metaChip: {
    minWidth: 52,
    minHeight: 40,
    paddingHorizontal: 12,
    borderRadius: radii.pill,
    backgroundColor: colors.parchmentDeep,
    alignItems: "center",
    justifyContent: "center",
  },
  metaChipOn: {
    backgroundColor: "rgba(26, 36, 32, 0.1)",
  },
  sideBtn: {
    width: 48,
    height: 48,
    alignItems: "center",
    justifyContent: "center",
  },
  play: {
    width: 64,
    height: 64,
    borderRadius: radii.pill,
    backgroundColor: colors.ink,
    alignItems: "center",
    justifyContent: "center",
  },
  playCompact: {
    width: 56,
    height: 56,
  },
  actions: {
    flexDirection: "row",
    flexWrap: "wrap",
    justifyContent: "center",
    gap: 8,
    paddingTop: space.xs,
  },
  chip: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderRadius: radii.pill,
    backgroundColor: colors.parchmentDeep,
    minHeight: 40,
  },
  chipOn: {
    backgroundColor: "rgba(26, 36, 32, 0.1)",
  },
  sheetBackdrop: {
    flex: 1,
    backgroundColor: "rgba(26,36,32,0.35)",
    justifyContent: "flex-end",
  },
  sheet: {
    backgroundColor: colors.card,
    borderTopLeftRadius: radii.lg,
    borderTopRightRadius: radii.lg,
    padding: space.md,
    paddingBottom: space.xl,
  },
  sheetTitle: { textAlign: "center", marginBottom: space.sm },
  sheetRow: {
    paddingVertical: 14,
    paddingHorizontal: space.md,
    borderRadius: radii.sm,
  },
  sheetRowOn: {
    backgroundColor: "rgba(26, 36, 32, 0.08)",
  },
});
