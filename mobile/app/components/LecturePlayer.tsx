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
import { radii, space, type ThemeColors } from "@/constants/theme";
import { useColors } from "@/lib/useTheme";
import { findCueIndex, formatClock, toPersianDigits } from "@/lib/format";
import {
  downloadSessionItem,
  type DownloadItem,
} from "@/lib/sessionDownload";
import {
  deleteOfflinePack,
  downloadOfflinePack,
  estimateOfflineBytes,
  formatBytesFa,
  getOfflineManifest,
  resolveOfflinePaths,
  type OfflineLocalPaths,
  type OfflinePackManifest,
} from "@/lib/offlineSession";
import type { Cue, SessionPayload } from "@/lib/types";

const RATES = [0.75, 1, 1.25, 1.5, 2] as const;

type DocKind = "full" | "book" | "summary" | null;

type Props = {
  session: SessionPayload;
  cues: Cue[];
  audioUrl: string;
  dataBase: string;
  lecturerSlug: string;
  courseSlug: string;
  site: "website" | "portal";
  lecturerName?: string;
  courseTitle?: string;
  onToggleSave?: () => void;
  saved?: boolean;
  /** Called after offline pack is added/removed so parent can refresh sources. */
  onOfflineChange?: (paths: OfflineLocalPaths | null) => void;
  initialOfflinePaths?: OfflineLocalPaths | null;
};

export function LecturePlayer({
  session,
  cues,
  audioUrl,
  dataBase,
  lecturerSlug,
  courseSlug,
  site,
  lecturerName,
  courseTitle,
  onToggleSave,
  saved,
  onOfflineChange,
  initialOfflinePaths = null,
}: Props) {
  const colors = useColors();
  const styles = useMemo(() => makeStyles(colors), [colors]);
  const [playbackUrl, setPlaybackUrl] = useState(
    initialOfflinePaths?.audioUri || audioUrl,
  );
  const player = useAudioPlayer(playbackUrl, { updateInterval: 100 });
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
  const [offlineManifest, setOfflineManifest] =
    useState<OfflinePackManifest | null>(null);
  const [offlinePaths, setOfflinePaths] = useState<OfflineLocalPaths | null>(
    initialOfflinePaths,
  );
  const [offlineBusy, setOfflineBusy] = useState(false);
  const [offlineProgress, setOfflineProgress] = useState(0);
  const [confirmDialog, setConfirmDialog] = useState<{
    title: string;
    body: string;
    confirmLabel: string;
    destructive?: boolean;
    onConfirm: () => void;
  } | null>(null);
  const [noticeDialog, setNoticeDialog] = useState<{
    title: string;
    body: string;
  } | null>(null);

  const offlineKey = useMemo(
    () => ({
      lecturerSlug,
      courseSlug,
      sessionId: session.id,
    }),
    [lecturerSlug, courseSlug, session.id],
  );

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

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const [manifest, paths] = await Promise.all([
        getOfflineManifest(offlineKey),
        resolveOfflinePaths(offlineKey),
      ]);
      if (cancelled) return;
      setOfflineManifest(manifest);
      if (paths) {
        setOfflinePaths(paths);
        if (paths.audioUri && paths.audioUri !== playbackUrl) {
          setPlaybackUrl(paths.audioUri);
          try {
            player.replace(paths.audioUri);
          } catch {
            /* ignore */
          }
        }
      }
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- refresh when session identity changes
  }, [offlineKey.lecturerSlug, offlineKey.courseSlug, offlineKey.sessionId]);

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
    return () => {
      try {
        player.pause();
      } catch {
        /* ignore */
      }
    };
  }, [player]);

  useEffect(() => {
    if (!ready) return;
    try {
      player.setPlaybackRate(rate);
    } catch {
      /* ignore */
    }
  }, [rate, ready, player]);

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

  const fullRemoteUrl = preferRaw
    ? `${dataRoot}.raw.txt`
    : `${dataRoot}.corrected.md`;
  const bookRemoteUrl = `${dataRoot}.book.md`;
  const summaryRemoteUrl = `${dataRoot}.summary.md`;

  const downloadItems = useMemo(() => {
    const items: DownloadItem[] = [];
    if (hasFullText) {
      items.push({
        key: "full-txt",
        label: preferRaw ? "متن خام ASR (TXT)" : "متن کامل (TXT)",
        url: fullRemoteUrl,
        filename: preferRaw
          ? `${session.id}-متن-خام-asr.txt`
          : `${session.id}-متن-کامل.txt`,
        format: "txt",
      });
      items.push({
        key: "full-pdf",
        label: "متن کامل (PDF)",
        url: fullRemoteUrl,
        filename: `${session.id}-متن-کامل.pdf`,
        format: "pdf",
      });
    }
    if (hasBook) {
      items.push({
        key: "book-txt",
        label: "نسخه کتابی (TXT)",
        url: bookRemoteUrl,
        filename: `${session.id}-نسخه-کتابی.txt`,
        format: "txt",
      });
      items.push({
        key: "book-pdf",
        label: "نسخه کتابی (PDF)",
        url: bookRemoteUrl,
        filename: `${session.id}-نسخه-کتابی.pdf`,
        format: "pdf",
      });
    }
    if (hasSummary) {
      items.push({
        key: "summary-txt",
        label: "خلاصه (TXT)",
        url: summaryRemoteUrl,
        filename: `${session.id}-خلاصه.txt`,
        format: "txt",
      });
      items.push({
        key: "summary-pdf",
        label: "خلاصه (PDF)",
        url: summaryRemoteUrl,
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
    bookRemoteUrl,
    fullRemoteUrl,
    hasBook,
    hasFullText,
    hasSummary,
    preferRaw,
    session.audio?.filename,
    session.id,
    summaryRemoteUrl,
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
    const ratio = Math.max(0, Math.min(1, x / trackWidth));
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
          title: "خروجی فایل",
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

  async function runOfflineDownload() {
    setOfflineBusy(true);
    setOfflineProgress(0);
    try {
      const manifest = await downloadOfflinePack({
        ...offlineKey,
        site,
        title: session.title,
        courseTitle,
        lecturerName,
        session,
        cues,
        audioUrl,
        fullUrl: hasFullText ? fullRemoteUrl : null,
        bookUrl: hasBook ? bookRemoteUrl : null,
        summaryUrl: hasSummary ? summaryRemoteUrl : null,
        onProgress: setOfflineProgress,
      });
      const paths = await resolveOfflinePaths(offlineKey);
      setOfflineManifest(manifest);
      setOfflinePaths(paths);
      onOfflineChange?.(paths);
      if (paths?.audioUri) {
        setPlaybackUrl(paths.audioUri);
        try {
          player.replace(paths.audioUri);
        } catch {
          /* ignore */
        }
      }
      setNoticeDialog({
        title: "ذخیره شد",
        body: "این جلسه روی گوشی ذخیره شد و بدون اینترنت در برنامه قابل استفاده است.",
      });
    } catch {
      setNoticeDialog({
        title: "خطا",
        body: "ذخیره آفلاین انجام نشد. اتصال را بررسی کنید.",
      });
    } finally {
      setOfflineBusy(false);
      setOfflineProgress(0);
    }
  }

  function confirmOfflineDownload() {
    if (!audioUrl || offlineBusy) return;
    const sizeLabel = formatBytesFa(estimateOfflineBytes(session));
    setConfirmDialog({
      title: "ذخیره برای آفلاین",
      body: `این جلسه برای استفاده آفلاین روی گوشی ذخیره می‌شود (حدود ${sizeLabel}). در صورت نیاز بعداً می‌توانید آن را از داخل برنامه حذف کنید.`,
      confirmLabel: "ذخیره",
      onConfirm: () => void runOfflineDownload(),
    });
  }

  function confirmDeleteOffline() {
    setConfirmDialog({
      title: "حذف نسخه آفلاین",
      body: "فایل‌های ذخیره‌شده این جلسه از حافظه گوشی پاک می‌شوند.",
      confirmLabel: "حذف",
      destructive: true,
      onConfirm: () => void runDeleteOffline(),
    });
  }

  async function runDeleteOffline() {
    setOfflineBusy(true);
    try {
      await deleteOfflinePack(offlineKey);
      setOfflineManifest(null);
      setOfflinePaths(null);
      onOfflineChange?.(null);
      setPlaybackUrl(audioUrl);
      try {
        player.replace(audioUrl);
      } catch {
        /* ignore */
      }
    } catch {
      Alert.alert("خطا", "حذف دانلود انجام نشد.");
    } finally {
      setOfflineBusy(false);
    }
  }

  const docUrl =
    docKind === "full"
      ? offlinePaths?.fullUri || fullRemoteUrl
      : docKind === "book"
        ? offlinePaths?.bookUri || bookRemoteUrl
        : docKind === "summary"
          ? offlinePaths?.summaryUri || summaryRemoteUrl
          : null;

  const docTitle =
    docKind === "full"
      ? "متن کامل"
      : docKind === "book"
        ? "نسخه کتابی"
        : docKind === "summary"
          ? "خلاصه"
          : "";

  const offlineLabel = offlineBusy
    ? offlineProgress > 0
      ? `${toPersianDigits(Math.round(offlineProgress * 100))}٪`
      : "…"
    : offlineManifest
      ? "آفلاین"
      : "آفلاین";

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
          { maxWidth: panelMax, paddingBottom: actionsBottomPad },
        ]}
      >
        {/* Transport */}
        <View style={styles.transport}>
          <Pressable
            onPress={() => seekBy(-15)}
            style={styles.seekBtn}
            accessibilityLabel="۱۵ ثانیه عقب"
            hitSlop={8}
          >
            <Ionicons name="play-back" size={22} color={colors.inkSoft} />
            <AppText variant="meta" tone="mist">
              {toPersianDigits(15)}
            </AppText>
          </Pressable>

          <Pressable
            onPress={toggle}
            style={styles.playBtn}
            accessibilityLabel={playing ? "توقف" : "پخش"}
          >
            {!ready ? (
              <ActivityIndicator color={colors.parchment} />
            ) : (
              <Ionicons
                name={playing ? "pause" : "play"}
                size={28}
                color={colors.parchment}
                style={!playing ? { marginLeft: 3 } : undefined}
              />
            )}
          </Pressable>

          <Pressable
            onPress={() => seekBy(15)}
            style={styles.seekBtn}
            accessibilityLabel="۱۵ ثانیه جلو"
            hitSlop={8}
          >
            <Ionicons name="play-forward" size={22} color={colors.inkSoft} />
            <AppText variant="meta" tone="mist">
              {toPersianDigits(15)}
            </AppText>
          </Pressable>
        </View>

        {/* Scrubber */}
        <Pressable
          onLayout={onTrackLayout}
          onPress={seekFromTrack}
          style={styles.trackHit}
          accessibilityLabel="نوار پیشرفت"
        >
          <View style={styles.track}>
            <View
              style={[
                styles.trackFill,
                {
                  width:
                    duration > 0
                      ? `${Math.min(100, (position / duration) * 100)}%`
                      : "0%",
                },
              ]}
            />
          </View>
        </Pressable>

        <View style={styles.times}>
          <AppText variant="meta" tone="mist">
            {formatClock(position)}
          </AppText>
          <AppText variant="meta" tone="mist">
            {formatClock(duration)}
          </AppText>
        </View>

        {/* Meta row */}
        <View style={styles.metaRow}>
          <Pressable
            onPress={() => setSubtitlesOn((v) => !v)}
            style={[styles.metaChip, subtitlesOn && styles.metaChipOn]}
            accessibilityLabel="زیرنویس"
          >
            <Ionicons
              name={subtitlesOn ? "text" : "text-outline"}
              size={16}
              color={subtitlesOn ? colors.ink : colors.mist}
            />
          </Pressable>
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
            icon={offlineManifest ? "phone-portrait-outline" : "cloud-offline-outline"}
            label={
              offlineBusy
                ? offlineLabel
                : offlineManifest
                  ? "حذف"
                  : "آفلاین"
            }
            active={Boolean(offlineManifest)}
            onPress={
              offlineBusy
                ? undefined
                : offlineManifest
                  ? confirmDeleteOffline
                  : confirmOfflineDownload
            }
            disabled={!audioUrl || offlineBusy}
          />
          <ActionChip
            icon="folder-outline"
            label={busyDownload ? "…" : "خروجی"}
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
        {offlineManifest ? (
          <Pressable
            onPress={confirmDeleteOffline}
            disabled={offlineBusy}
            hitSlop={8}
            style={styles.offlineHint}
          >
            <AppText variant="meta" tone="mist" style={styles.offlineHintText}>
              {`ذخیره آفلاین (${formatBytesFa(offlineManifest.bytes)}) · حذف دانلود`}
            </AppText>
          </Pressable>
        ) : null}
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
              خروجی فایل
            </AppText>
            {downloadItems.map((item) => (
              <Pressable
                key={item.key}
                style={styles.sheetRow}
                onPress={() => void downloadFile(item)}
              >
                <AppText variant="body" style={styles.sheetRowText}>
                  {item.label}
                </AppText>
              </Pressable>
            ))}
          </View>
        </Pressable>
      </Modal>

      <Modal
        visible={confirmDialog !== null}
        transparent
        animationType="fade"
        onRequestClose={() => setConfirmDialog(null)}
      >
        <Pressable
          style={styles.dialogBackdrop}
          onPress={() => setConfirmDialog(null)}
        >
          <Pressable style={styles.dialogCard} onPress={(e) => e.stopPropagation()}>
            <AppText variant="title" style={styles.dialogTitle}>
              {confirmDialog?.title}
            </AppText>
            <AppText variant="body" tone="soft" style={styles.dialogBody}>
              {confirmDialog?.body}
            </AppText>
            <View style={styles.dialogActions}>
              <Pressable
                style={styles.dialogBtn}
                onPress={() => setConfirmDialog(null)}
                hitSlop={8}
              >
                <AppText variant="body" tone="mist">
                  انصراف
                </AppText>
              </Pressable>
              <Pressable
                style={[
                  styles.dialogBtn,
                  styles.dialogBtnPrimary,
                  confirmDialog?.destructive && styles.dialogBtnDanger,
                ]}
                onPress={() => {
                  const action = confirmDialog?.onConfirm;
                  setConfirmDialog(null);
                  action?.();
                }}
                hitSlop={8}
              >
                <AppText
                  variant="body"
                  tone={confirmDialog?.destructive ? undefined : "ink"}
                  style={
                    confirmDialog?.destructive
                      ? styles.dialogDangerText
                      : undefined
                  }
                >
                  {confirmDialog?.confirmLabel}
                </AppText>
              </Pressable>
            </View>
          </Pressable>
        </Pressable>
      </Modal>

      <Modal
        visible={noticeDialog !== null}
        transparent
        animationType="fade"
        onRequestClose={() => setNoticeDialog(null)}
      >
        <Pressable
          style={styles.dialogBackdrop}
          onPress={() => setNoticeDialog(null)}
        >
          <Pressable style={styles.dialogCard} onPress={(e) => e.stopPropagation()}>
            <AppText variant="title" style={styles.dialogTitle}>
              {noticeDialog?.title}
            </AppText>
            <AppText variant="body" tone="soft" style={styles.dialogBody}>
              {noticeDialog?.body}
            </AppText>
            <View style={styles.dialogActions}>
              <Pressable
                style={[styles.dialogBtn, styles.dialogBtnPrimary]}
                onPress={() => setNoticeDialog(null)}
                hitSlop={8}
              >
                <AppText variant="body" tone="ink">
                  باشه
                </AppText>
              </Pressable>
            </View>
          </Pressable>
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
  const colors = useColors();
  const styles = useMemo(() => makeStyles(colors), [colors]);
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

function makeStyles(colors: ThemeColors) {
  return StyleSheet.create({
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
    paddingTop: space.sm,
    gap: space.sm,
  },
  transport: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: space.xl,
  },
  seekBtn: { alignItems: "center", gap: 2, minWidth: 44 },
  playBtn: {
    width: 64,
    height: 64,
    borderRadius: 32,
    backgroundColor: colors.ink,
    alignItems: "center",
    justifyContent: "center",
  },
  trackHit: { paddingVertical: 8 },
  track: {
    height: 4,
    borderRadius: 2,
    backgroundColor: colors.line,
    overflow: "hidden",
  },
  trackFill: {
    height: "100%",
    backgroundColor: colors.copper,
    borderRadius: 2,
  },
  times: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginTop: -4,
  },
  metaRow: {
    flexDirection: "row",
    justifyContent: "center",
    gap: space.sm,
  },
  metaChip: {
    minHeight: 36,
    minWidth: 44,
    paddingHorizontal: 12,
    borderRadius: radii.pill,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.line,
    alignItems: "center",
    justifyContent: "center",
  },
  metaChipOn: {
    backgroundColor: colors.copperWash,
    borderColor: colors.copperSoft,
  },
  actions: {
    flexDirection: "row",
    flexWrap: "wrap",
    justifyContent: "center",
    gap: 8,
  },
  chip: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: radii.pill,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.line,
    backgroundColor: colors.parchmentDeep,
  },
  chipOn: {
    backgroundColor: colors.copperWash,
    borderColor: colors.copperSoft,
  },
  offlineHint: {
    alignItems: "center",
    paddingTop: 2,
  },
  offlineHintText: {
    textAlign: "center",
    writingDirection: "rtl",
  },
  sheetBackdrop: {
    flex: 1,
    backgroundColor: "rgba(0,0,0,0.35)",
    justifyContent: "flex-end",
  },
  sheet: {
    backgroundColor: colors.parchment,
    borderTopLeftRadius: radii.lg,
    borderTopRightRadius: radii.lg,
    padding: space.lg,
    paddingBottom: space.xxl,
    gap: 4,
  },
  sheetTitle: {
    textAlign: "center",
    marginBottom: space.sm,
    writingDirection: "rtl",
  },
  sheetRow: {
    paddingVertical: 14,
    paddingHorizontal: space.md,
    borderRadius: radii.md,
  },
  sheetRowText: {
    textAlign: "right",
    writingDirection: "rtl",
  },
  sheetRowOn: {
    backgroundColor: colors.copperWash,
  },
  dialogBackdrop: {
    flex: 1,
    backgroundColor: "rgba(0,0,0,0.4)",
    justifyContent: "center",
    paddingHorizontal: space.lg,
  },
  dialogCard: {
    backgroundColor: colors.parchment,
    borderRadius: radii.lg,
    padding: space.lg,
    gap: space.md,
  },
  dialogTitle: {
    textAlign: "right",
    writingDirection: "rtl",
  },
  dialogBody: {
    textAlign: "right",
    writingDirection: "rtl",
    lineHeight: 26,
  },
  dialogActions: {
    flexDirection: "row-reverse",
    justifyContent: "flex-start",
    gap: space.sm,
    marginTop: space.xs,
  },
  dialogBtn: {
    minHeight: 44,
    minWidth: 72,
    paddingHorizontal: space.md,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: radii.md,
  },
  dialogBtnPrimary: {
    backgroundColor: colors.copperWash,
  },
  dialogBtnDanger: {
    backgroundColor: "rgba(139, 58, 58, 0.12)",
  },
  dialogDangerText: {
    color: colors.danger,
    textAlign: "right",
    writingDirection: "rtl",
  },
  });
}
