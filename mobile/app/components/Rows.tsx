import {
  Pressable,
  View,
  Image,
  StyleSheet,
  type StyleProp,
  type ViewStyle,
  type ImageSourcePropType,
} from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { AppText } from "./AppText";
import { colors, radii, space } from "@/constants/theme";
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

function Portrait({
  lecturer,
}: {
  lecturer: Lecturer;
}) {
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
      <AppText variant="meta" tone="copper" style={styles.mono}>
        {monogram(lecturer.name, lecturer.slug)}
      </AppText>
    </View>
  );
}

/**
 * Card row: portrait on the right (RTL reading), soft surface, count pill.
 */
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
        styles.card,
        pressed && styles.pressed,
        style,
      ]}
      accessibilityRole="button"
      accessibilityLabel={lecturer.name}
    >
      <Ionicons
        name="chevron-back"
        size={18}
        color={colors.copperSoft}
        style={styles.chevron}
      />
      <View style={styles.meta}>
        <AppText variant="title" numberOfLines={2} style={styles.align}>
          {lecturer.name}
        </AppText>
        <AppText
          variant="meta"
          tone="mist"
          numberOfLines={1}
          style={styles.align}
        >
          {lecturer.title}
        </AppText>
        <View style={styles.badgeRow}>
          <View style={styles.pill}>
            <AppText variant="caption" tone="copper">
              {toPersianDigits(count)} درس‌گفتار
            </AppText>
          </View>
        </View>
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
      style={({ pressed }) => [styles.courseCard, pressed && styles.pressed]}
      accessibilityRole="button"
    >
      <View style={styles.meta}>
        <AppText variant="title" numberOfLines={2} style={styles.align}>
          {course.title}
        </AppText>
        <AppText
          variant="meta"
          tone="mist"
          style={[styles.courseMeta, styles.align]}
        >
          {toPersianDigits(course.sessionCount)} جلسه
          {course.totalDurationText
            ? ` · ${toPersianDigits(course.totalDurationText)}`
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
      <View style={styles.indexBadge}>
        <AppText variant="meta" tone="copper">
          {toPersianDigits(index)}
        </AppText>
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  card: {
    flexDirection: "row",
    alignItems: "center",
    gap: 14,
    paddingHorizontal: 16,
    paddingVertical: 16,
    marginBottom: 10,
    backgroundColor: colors.card,
    borderRadius: radii.md,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.line,
  },
  pressed: { opacity: 0.85 },
  chevron: { marginLeft: 2 },
  meta: { flex: 1, gap: 4, minWidth: 0 },
  align: { textAlign: "right", writingDirection: "rtl" },
  badgeRow: {
    marginTop: 6,
    flexDirection: "row",
    justifyContent: "flex-end",
  },
  pill: {
    backgroundColor: colors.copperWash,
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: radii.pill,
  },
  avatarWrap: {
    width: 64,
    height: 64,
    borderRadius: radii.md,
    overflow: "hidden",
    backgroundColor: colors.parchmentDeep,
  },
  avatar: { width: "100%", height: "100%" },
  avatarFallback: {
    alignItems: "center",
    justifyContent: "center",
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.copperSoft,
    backgroundColor: colors.copperWash,
  },
  mono: {
    textAlign: "center",
    fontSize: 15,
  },
  courseCard: {
    flexDirection: "row",
    alignItems: "center",
    gap: 14,
    paddingHorizontal: 16,
    paddingVertical: 14,
    marginBottom: 10,
    backgroundColor: colors.card,
    borderRadius: radii.md,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.line,
  },
  cover: {
    width: 56,
    height: 56,
    borderRadius: radii.sm,
    backgroundColor: colors.parchmentDeep,
  },
  coverFallback: { backgroundColor: colors.sage },
  courseMeta: { marginTop: 2 },
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
  indexBadge: {
    width: 36,
    height: 36,
    borderRadius: radii.pill,
    borderWidth: 1,
    borderColor: colors.copperSoft,
    alignItems: "center",
    justifyContent: "center",
  },
});
