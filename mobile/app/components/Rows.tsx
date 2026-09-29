import {
  Pressable,
  View,
  Image,
  StyleSheet,
  type StyleProp,
  type ViewStyle,
  type ImageSourcePropType,
} from "react-native";
import { AppText } from "./AppText";
import { colors, radii, space, type } from "@/constants/theme";
import { resolveAssetUrl, toPersianDigits } from "@/lib/format";
import type { CourseSummary, Lecturer } from "@/lib/types";

/** Optional local portraits — drop files here when ready. */
const LOCAL_PORTRAITS: Record<string, ImageSourcePropType | undefined> = {
  bayat: require("../assets/images/lecturers/bayat.png"),
};

function monogram(name: string, slug?: string): string {
  if (slug === "bayat") return "بیات";
  const clean = name.replace(/[()]/g, " ").trim();
  const parts = clean.split(/\s+/).filter(Boolean);
  if (parts.length >= 2) {
    return (parts[0][0] + parts[parts.length - 1][0]).slice(0, 2);
  }
  return clean.slice(0, 2) || "؟";
}

function Portrait({ lecturer }: { lecturer: Lecturer }) {
  const local = LOCAL_PORTRAITS[lecturer.slug];
  const remote = resolveAssetUrl(lecturer.avatar, lecturer.dataBase);

  if (local) {
    return (
      <View style={styles.avatarWrap}>
        <Image source={local} style={styles.avatar} resizeMode="cover" />
      </View>
    );
  }
  if (remote && lecturer.slug !== "bayat") {
    return (
      <View style={styles.avatarWrap}>
        <Image source={{ uri: remote }} style={styles.avatar} resizeMode="cover" />
      </View>
    );
  }

  return (
    <View style={[styles.avatarWrap, styles.avatarFallback]}>
      <AppText variant="meta" tone="mist" style={styles.mono}>
        {monogram(lecturer.name, lecturer.slug)}
      </AppText>
    </View>
  );
}

function listDisplayName(name: string): string {
  return name
    .replace(/حجت[\u200c\u200f\s]*الاسلام[\u200c\u200f\s]*والمسلمین\s*/g, "")
    .replace(/حجت[\u200c\u200f\s]*الاسلام\s*/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

function listDisplayTitle(title: string): string {
  const primary = title.split(/\s*[·•|]\s*/)[0]?.trim();
  return primary || title;
}

/** Flat list row — portrait + text, no card chrome. */
export function LecturerRow({
  lecturer,
  onPress,
  style,
}: {
  lecturer: Lecturer;
  onPress: () => void;
  style?: StyleProp<ViewStyle>;
}) {
  const count = lecturer.courses.length;

  return (
    <Pressable
      onPress={onPress}
      style={({ pressed }) => [
        styles.row,
        pressed && styles.pressed,
        style,
      ]}
      accessibilityRole="button"
      accessibilityLabel={lecturer.name}
    >
      <View style={styles.meta}>
        <AppText
          variant="title"
          numberOfLines={2}
          style={[styles.align, styles.rowName]}
        >
          {listDisplayName(lecturer.name)}
        </AppText>
        <AppText
          variant="meta"
          tone="mist"
          numberOfLines={1}
          style={styles.align}
        >
          {listDisplayTitle(lecturer.title)}
          {"  "}
          {toPersianDigits(count)} دوره
        </AppText>
      </View>
      <Portrait lecturer={lecturer} />
    </Pressable>
  );
}

export function CourseRow({
  course,
  dataBase,
  onPress,
  textOnly = false,
}: {
  course: CourseSummary;
  dataBase: string;
  onPress: () => void;
  textOnly?: boolean;
}) {
  const cover = textOnly ? "" : resolveAssetUrl(course.cover, dataBase);
  return (
    <Pressable
      onPress={onPress}
      style={({ pressed }) => [styles.row, pressed && styles.pressed]}
      accessibilityRole="button"
    >
      <View style={styles.meta}>
        <AppText variant="title" numberOfLines={2} style={styles.align}>
          {course.title}
        </AppText>
        <AppText variant="meta" tone="mist" style={styles.align}>
          {toPersianDigits(course.sessionCount)} جلسه
          {course.totalDurationText
            ? `  ${toPersianDigits(course.totalDurationText)}`
            : ""}
        </AppText>
      </View>
      {!textOnly ? (
        cover ? (
          <Image source={{ uri: cover }} style={styles.cover} />
        ) : (
          <View style={[styles.cover, styles.coverFallback]} />
        )
      ) : null}
    </Pressable>
  );
}

export function SessionRow({
  index,
  title,
  durationText,
  onPress,
}: {
  index: number;
  title: string;
  durationText: string | null;
  onPress: () => void;
}) {
  return (
    <Pressable
      onPress={onPress}
      style={({ pressed }) => [styles.session, pressed && styles.pressed]}
      accessibilityRole="button"
    >
      <View style={styles.sessionBody}>
        <AppText variant="body" numberOfLines={2} style={styles.align}>
          {title}
        </AppText>
        {durationText ? (
          <AppText variant="caption" tone="mist" style={styles.align}>
            {toPersianDigits(durationText)}
          </AppText>
        ) : null}
      </View>
      <AppText variant="meta" tone="mist" style={styles.index}>
        {toPersianDigits(index)}
      </AppText>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: "row",
    alignItems: "center",
    gap: 14,
    paddingVertical: 16,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.line,
  },
  pressed: { opacity: 0.65 },
  meta: { flex: 1, gap: 4, minWidth: 0 },
  align: { textAlign: "right", writingDirection: "rtl" },
  rowName: {
    fontSize: 16,
    lineHeight: 25,
    fontFamily: type.medium,
  },
  avatarWrap: {
    width: 52,
    height: 52,
    borderRadius: radii.sm,
    overflow: "hidden",
    backgroundColor: colors.parchmentDeep,
  },
  avatar: { width: "100%", height: "100%" },
  avatarFallback: {
    alignItems: "center",
    justifyContent: "center",
  },
  mono: {
    textAlign: "center",
    fontSize: 13,
  },
  cover: {
    width: 48,
    height: 48,
    borderRadius: radii.sm,
    backgroundColor: colors.parchmentDeep,
  },
  coverFallback: { backgroundColor: colors.parchmentDeep },
  session: {
    flexDirection: "row",
    alignItems: "center",
    gap: space.md,
    paddingVertical: 14,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.line,
    minHeight: 56,
  },
  sessionBody: { flex: 1, gap: 2 },
  index: {
    minWidth: 28,
    textAlign: "center",
  },
});
