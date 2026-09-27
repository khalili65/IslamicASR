import { useEffect, useMemo, useRef } from "react";
import {
  View,
  StyleSheet,
  Pressable,
  FlatList,
  ActivityIndicator,
} from "react-native";
import {
  useAudioPlayer,
  useAudioPlayerStatus,
  setAudioModeAsync,
} from "expo-audio";
import { AppText } from "./AppText";
import { colors, radii, space, type } from "@/constants/theme";
import { findCueIndex, formatClock } from "@/lib/format";
import type { Cue, SessionPayload } from "@/lib/types";

type Props = {
  session: SessionPayload;
  cues: Cue[];
  audioUrl: string;
  onToggleSave?: () => void;
  saved?: boolean;
};

export function LecturePlayer({
  session,
  cues,
  audioUrl,
  onToggleSave,
  saved,
}: Props) {
  const player = useAudioPlayer(audioUrl, { updateInterval: 100 });
  const status = useAudioPlayerStatus(player);
  const listRef = useRef<FlatList<Cue>>(null);
  const lastCue = useRef(-1);

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
  const active = cueIndex >= 0 ? cues[cueIndex] : null;

  useEffect(() => {
    setAudioModeAsync({
      playsInSilentMode: true,
      shouldPlayInBackground: true,
      interruptionMode: "doNotMix",
    }).catch(() => {});
  }, []);

  useEffect(() => {
    if (cueIndex < 0 || cueIndex === lastCue.current) return;
    lastCue.current = cueIndex;
    listRef.current?.scrollToIndex({
      index: cueIndex,
      animated: true,
      viewPosition: 0.35,
    });
  }, [cueIndex]);

  function toggle() {
    if (!ready) return;
    if (playing) player.pause();
    else player.play();
  }

  function seekBy(delta: number) {
    if (!ready) return;
    const next = Math.max(0, Math.min(position + delta, duration || position + delta));
    player.seekTo(next);
  }

  function seekTo(seconds: number) {
    if (!ready) return;
    player.seekTo(Math.max(0, seconds));
    player.play();
  }

  const progress = duration > 0 ? Math.min(1, position / duration) : 0;

  return (
    <View style={styles.root}>
      <View style={styles.stage}>
        <AppText variant="caption" tone="stageMuted" style={styles.stageLabel}>
          {session.title}
        </AppText>
        <AppText
          variant="display"
          tone="stage"
          style={styles.stageText}
          numberOfLines={4}
        >
          {active?.text ?? "﷽"}
        </AppText>
      </View>

      <View style={styles.controls}>
        <View style={styles.track}>
          <View style={[styles.fill, { width: `${progress * 100}%` }]} />
        </View>
        <View style={styles.times}>
          <AppText variant="caption" tone="mist">
            {formatClock(duration)}
          </AppText>
          <AppText variant="caption" tone="mist">
            {formatClock(position)}
          </AppText>
        </View>

        <View style={styles.buttons}>
          <Pressable
            onPress={() => seekBy(15)}
            style={styles.sideBtn}
            accessibilityLabel="پانزده ثانیه جلو"
          >
            <AppText variant="meta" tone="copper">
              ۱۵+
            </AppText>
          </Pressable>

          <Pressable
            onPress={toggle}
            disabled={!ready}
            style={({ pressed }) => [
              styles.play,
              pressed && { opacity: 0.85 },
              !ready && { opacity: 0.5 },
            ]}
            accessibilityRole="button"
            accessibilityLabel={playing ? "توقف" : "پخش"}
          >
            {!ready ? (
              <ActivityIndicator color={colors.parchment} />
            ) : (
              <AppText style={styles.playLabel}>
                {playing ? "❚❚" : "▶"}
              </AppText>
            )}
          </Pressable>

          <Pressable
            onPress={() => seekBy(-15)}
            style={styles.sideBtn}
            accessibilityLabel="پانزده ثانیه عقب"
          >
            <AppText variant="meta" tone="copper">
              −۱۵
            </AppText>
          </Pressable>
        </View>

        {onToggleSave ? (
          <Pressable onPress={onToggleSave} style={styles.save}>
            <AppText variant="meta" tone="copper">
              {saved ? "در فهرست من" : "افزودن به فهرست من"}
            </AppText>
          </Pressable>
        ) : null}
      </View>

      <FlatList
        ref={listRef}
        data={cues}
        keyExtractor={(c) => String(c.i)}
        contentContainerStyle={styles.list}
        onScrollToIndexFailed={() => {}}
        renderItem={({ item, index }) => {
          const on = index === cueIndex;
          return (
            <Pressable
              onPress={() => seekTo(item.start)}
              style={[styles.cue, on && styles.cueOn]}
            >
              <AppText
                variant="body"
                tone={on ? "ink" : "soft"}
                style={on ? styles.cueTextOn : undefined}
              >
                {item.text}
              </AppText>
              <AppText variant="caption" tone="mist">
                {formatClock(item.start)}
              </AppText>
            </Pressable>
          );
        }}
        ListHeaderComponent={
          <AppText variant="meta" tone="mist" style={styles.listHead}>
            متن جلسه
          </AppText>
        }
      />
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1 },
  stage: {
    backgroundColor: colors.stage,
    paddingHorizontal: space.lg,
    paddingTop: space.lg,
    paddingBottom: space.xl,
    minHeight: 168,
    justifyContent: "center",
  },
  stageLabel: { textAlign: "center", marginBottom: space.sm },
  stageText: {
    textAlign: "center",
    fontSize: 26,
    lineHeight: 40,
  },
  controls: {
    paddingHorizontal: space.lg,
    paddingTop: space.md,
    paddingBottom: space.sm,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.line,
    backgroundColor: "rgba(233,230,220,0.92)",
  },
  track: {
    height: 3,
    backgroundColor: colors.parchmentDeep,
    borderRadius: radii.pill,
    overflow: "hidden",
  },
  fill: {
    height: "100%",
    backgroundColor: colors.copper,
  },
  times: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginTop: 6,
  },
  buttons: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: space.xl,
    marginTop: space.md,
    marginBottom: space.sm,
  },
  sideBtn: {
    minWidth: 48,
    minHeight: 48,
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
  playLabel: {
    color: colors.parchment,
    fontSize: 22,
    fontFamily: type.bold,
  },
  save: {
    alignSelf: "center",
    paddingVertical: space.sm,
    minHeight: 44,
    justifyContent: "center",
  },
  list: { paddingHorizontal: space.lg, paddingBottom: space.xxl },
  listHead: { marginTop: space.md, marginBottom: space.sm },
  cue: {
    paddingVertical: 12,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.line,
    gap: 4,
  },
  cueOn: {
    backgroundColor: "rgba(154, 107, 63, 0.08)",
    marginHorizontal: -space.sm,
    paddingHorizontal: space.sm,
    borderRadius: radii.sm,
  },
  cueTextOn: { fontFamily: type.bold },
});
