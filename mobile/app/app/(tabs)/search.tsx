import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  FlatList,
  Modal,
  Pressable,
  StyleSheet,
  TextInput,
  View,
} from "react-native";
import { useRouter } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import { Screen } from "@/components/Screen";
import { AppText } from "@/components/AppText";
import { radii, space, type, type ThemeColors } from "@/constants/theme";
import { useColors } from "@/lib/useTheme";
import { formatClock, toPersianDigits } from "@/lib/format";
import {
  loadLecturerSearchIndex,
  loadSearchCatalog,
  runTokenSearch,
  shortLecturerName,
  type LecturerSearchIndex,
  type SearchCatalog,
  type SearchHit,
} from "@/lib/search";

const PAGE_SIZE = 40;

type SelectOption = {
  key: string;
  label: string;
  /** When picking a course under "all lecturers", also set lecturer slug. */
  lecturer?: string;
};

export default function SearchScreen() {
  const colors = useColors();
  const styles = useMemo(() => makeStyles(colors), [colors]);
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const [catalog, setCatalog] = useState<SearchCatalog | null>(null);
  const [indexes, setIndexes] = useState<Record<string, LecturerSearchIndex>>(
    {},
  );
  const [draft, setDraft] = useState("");
  const [query, setQuery] = useState("");
  const [lecturerFilter, setLecturerFilter] = useState("all");
  const [courseFilter, setCourseFilter] = useState("all");
  const [loadingCatalog, setLoadingCatalog] = useState(true);
  const [loadingIndex, setLoadingIndex] = useState(false);
  const [loadError, setLoadError] = useState(false);
  const [searching, setSearching] = useState(false);
  const [visible, setVisible] = useState(PAGE_SIZE);
  const [picker, setPicker] = useState<"lecturer" | "course" | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoadingCatalog(true);
    loadSearchCatalog()
      .then((c) => {
        if (!cancelled) {
          setCatalog(c);
          setLoadError(false);
        }
      })
      .catch(() => {
        if (!cancelled) setLoadError(true);
      })
      .finally(() => {
        if (!cancelled) setLoadingCatalog(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const coursesForLecturer = useMemo(() => {
    if (!catalog) return [];
    if (lecturerFilter === "all") {
      return catalog.lecturers.flatMap((l) =>
        l.courses.map((c) => ({
          ...c,
          lecturer: l.slug,
          lecturerName: l.name,
        })),
      );
    }
    const lecturer = catalog.lecturers.find((l) => l.slug === lecturerFilter);
    return (lecturer?.courses || []).map((c) => ({
      ...c,
      lecturer: lecturer!.slug,
      lecturerName: lecturer!.name,
    }));
  }, [catalog, lecturerFilter]);

  useEffect(() => {
    if (courseFilter === "all") return;
    const ok = coursesForLecturer.some((c) => c.slug === courseFilter);
    if (!ok) setCourseFilter("all");
  }, [lecturerFilter, coursesForLecturer, courseFilter]);

  const neededLecturers = useMemo(() => {
    if (!catalog) return [];
    if (lecturerFilter !== "all") {
      return catalog.lecturers.filter((l) => l.slug === lecturerFilter);
    }
    return catalog.lecturers;
  }, [catalog, lecturerFilter]);

  useEffect(() => {
    let cancelled = false;
    const missing = neededLecturers.filter((l) => !indexes[l.slug]);
    if (!missing.length) return;

    setLoadingIndex(true);
    Promise.all(
      missing.map(async (lecturer) => {
        const data = await loadLecturerSearchIndex(lecturer);
        return [lecturer.slug, data] as const;
      }),
    )
      .then((entries) => {
        if (cancelled) return;
        setIndexes((prev) => {
          const next = { ...prev };
          for (const [slug, data] of entries) next[slug] = data;
          return next;
        });
        setLoadError(false);
      })
      .catch(() => {
        if (!cancelled) setLoadError(true);
      })
      .finally(() => {
        if (!cancelled) setLoadingIndex(false);
      });

    return () => {
      cancelled = true;
    };
  }, [neededLecturers, indexes]);

  useEffect(() => {
    setVisible(PAGE_SIZE);
  }, [query, lecturerFilter, courseFilter]);

  const runSearch = useCallback(() => {
    const next = draft.trim();
    if (next.length < 2) {
      setQuery("");
      return;
    }
    setSearching(true);
    requestAnimationFrame(() => {
      setQuery(next);
      setSearching(false);
    });
  }, [draft]);

  const hits = useMemo(() => {
    if (!catalog || searching) return [] as SearchHit[];
    return runTokenSearch({
      query,
      lecturers: catalog.lecturers,
      indexes,
      lecturerFilter,
      courseFilter,
    });
  }, [catalog, query, indexes, lecturerFilter, courseFilter, searching]);

  const shown = hits.slice(0, visible);
  const hasQuery = query.trim().length >= 2;
  const indexesReady = neededLecturers.every((l) => indexes[l.slug]);

  const lecturerLabel = useMemo(() => {
    if (lecturerFilter === "all") return "همهٔ مدرسان";
    const name = catalog?.lecturers.find((l) => l.slug === lecturerFilter)?.name;
    return name ? shortLecturerName(name) : lecturerFilter;
  }, [catalog, lecturerFilter]);

  const courseLabel = useMemo(() => {
    if (courseFilter === "all") return "همهٔ دوره‌ها";
    const course = coursesForLecturer.find((c) => c.slug === courseFilter);
    if (!course) return courseFilter;
    if (lecturerFilter === "all") {
      return `${course.title} · ${shortLecturerName(course.lecturerName)}`;
    }
    return course.title;
  }, [courseFilter, coursesForLecturer, lecturerFilter]);

  const lecturerOptions: SelectOption[] = useMemo(() => {
    if (!catalog) return [{ key: "all", label: "همهٔ مدرسان" }];
    return [
      { key: "all", label: "همهٔ مدرسان" },
      ...catalog.lecturers.map((l) => ({
        key: l.slug,
        label: shortLecturerName(l.name),
      })),
    ];
  }, [catalog]);

  const courseOptions: SelectOption[] = useMemo(() => {
    const all: SelectOption[] = [{ key: "all", label: "همهٔ دوره‌ها" }];
    for (const c of coursesForLecturer) {
      all.push({
        key: c.slug,
        label:
          lecturerFilter === "all"
            ? `${c.title} · ${shortLecturerName(c.lecturerName)}`
            : c.title,
        lecturer: c.lecturer,
      });
    }
    return all;
  }, [coursesForLecturer, lecturerFilter]);

  function openHit(hit: SearchHit) {
    router.push({
      pathname: "/player/[lecturer]/[course]/[session]",
      params: {
        lecturer: hit.lecturer,
        course: hit.course,
        session: hit.sessionId,
        ...(hit.kind === "cue" && hit.start != null
          ? { t: String(Math.floor(hit.start)) }
          : {}),
      },
    });
  }

  return (
    <Screen>
      <FlatList
        data={shown}
        keyExtractor={(hit) =>
          `${hit.lecturer}-${hit.course}-${hit.sessionId}-${hit.paraIndex}-${hit.start ?? "x"}`
        }
        contentContainerStyle={[
          styles.content,
          { paddingBottom: insets.bottom + space.xl },
        ]}
        keyboardShouldPersistTaps="handled"
        ListHeaderComponent={
          <View style={styles.header}>
            <AppText variant="display">جستجو</AppText>
            <AppText variant="body" tone="mist">
              جستجوی واژه‌ای در متن همگام جلسات
            </AppText>

            <View style={styles.searchRow}>
              <TextInput
                value={draft}
                onChangeText={setDraft}
                placeholder="واژه یا عبارت فارسی…"
                placeholderTextColor={colors.mist}
                style={styles.input}
                returnKeyType="search"
                onSubmitEditing={runSearch}
                textAlign="right"
                autoCorrect={false}
                autoCapitalize="none"
              />
              <Pressable
                onPress={runSearch}
                style={({ pressed }) => [
                  styles.searchBtn,
                  pressed && { opacity: 0.85 },
                ]}
                accessibilityLabel="جستجو"
              >
                <Ionicons name="search" size={20} color={colors.parchment} />
              </Pressable>
            </View>

            <View style={styles.filters}>
              {catalog && catalog.lecturers.length > 1 ? (
                <SelectField
                  label="مدرس"
                  value={lecturerLabel}
                  onPress={() => setPicker("lecturer")}
                />
              ) : null}
              <SelectField
                label="دوره"
                value={courseLabel}
                onPress={() => setPicker("course")}
                disabled={!catalog}
              />
            </View>

            {loadingCatalog || loadingIndex ? (
              <AppText variant="caption" tone="mist">
                در حال بارگذاری نمایهٔ جستجو…
              </AppText>
            ) : null}
            {loadError ? (
              <AppText variant="caption" tone="copper">
                بارگذاری نمایهٔ جستجو ناموفق بود.
              </AppText>
            ) : null}
            {searching || (hasQuery && !indexesReady) ? (
              <View style={styles.searchingRow}>
                <ActivityIndicator color={colors.ink} size="small" />
                <AppText variant="caption" tone="mist">
                  در حال جستجو…
                </AppText>
              </View>
            ) : hasQuery ? (
              <AppText variant="caption" tone="mist">
                {toPersianDigits(hits.length)} نتیجه
                {hits.length > visible
                  ? ` · نمایش ${toPersianDigits(visible)} مورد`
                  : ""}
              </AppText>
            ) : (
              <AppText variant="caption" tone="mist">
                حداقل دو حرف بنویسید و جستجو را بزنید.
              </AppText>
            )}
          </View>
        }
        ListEmptyComponent={
          hasQuery && !searching && indexesReady ? (
            <View style={styles.empty}>
              <AppText variant="body" tone="mist" style={styles.center}>
                نتیجه‌ای پیدا نشد.
              </AppText>
            </View>
          ) : null
        }
        renderItem={({ item }) => (
          <Pressable
            style={({ pressed }) => [styles.hit, pressed && { opacity: 0.75 }]}
            onPress={() => openHit(item)}
          >
            <View style={styles.hitMeta}>
              <AppText
                variant="caption"
                tone="mist"
                numberOfLines={1}
                style={styles.hitMetaText}
              >
                {item.lecturerName} · {item.courseTitle} · {item.sessionTitle}
              </AppText>
              {item.start != null ? (
                <AppText variant="caption" tone="copper">
                  {formatClock(item.start)}
                </AppText>
              ) : null}
            </View>
            <AppText variant="body" numberOfLines={3}>
              {item.text}
            </AppText>
          </Pressable>
        )}
        ListFooterComponent={
          hasQuery && hits.length > visible ? (
            <Pressable
              onPress={() => setVisible((n) => n + PAGE_SIZE)}
              style={styles.moreBtn}
            >
              <AppText variant="meta" tone="ink">
                نمایش نتایج بیشتر (
                {toPersianDigits(hits.length - visible)} باقی‌مانده)
              </AppText>
            </Pressable>
          ) : null
        }
      />

      <OptionPicker
        visible={picker === "lecturer"}
        title="انتخاب مدرس"
        options={lecturerOptions}
        selectedKey={lecturerFilter}
        searchable={lecturerOptions.length > 8}
        onClose={() => setPicker(null)}
        onSelect={(opt) => {
          setLecturerFilter(opt.key);
          setCourseFilter("all");
          setPicker(null);
        }}
      />
      <OptionPicker
        visible={picker === "course"}
        title="انتخاب دوره"
        options={courseOptions}
        selectedKey={courseFilter}
        searchable={courseOptions.length > 8}
        onClose={() => setPicker(null)}
        onSelect={(opt) => {
          if (opt.key !== "all" && opt.lecturer) {
            setLecturerFilter(opt.lecturer);
          }
          setCourseFilter(opt.key);
          setPicker(null);
        }}
      />
    </Screen>
  );
}

function SelectField({
  label,
  value,
  onPress,
  disabled,
}: {
  label: string;
  value: string;
  onPress: () => void;
  disabled?: boolean;
}) {
  const colors = useColors();
  const styles = useMemo(() => makeStyles(colors), [colors]);
  return (
    <Pressable
      onPress={onPress}
      disabled={disabled}
      style={({ pressed }) => [
        styles.selectField,
        pressed && !disabled && { opacity: 0.85 },
        disabled && { opacity: 0.45 },
      ]}
      accessibilityRole="button"
      accessibilityLabel={label}
    >
      <Ionicons name="chevron-down" size={18} color={colors.mist} />
      <View style={styles.selectText}>
        <AppText variant="caption" tone="mist">
          {label}
        </AppText>
        <AppText variant="meta" numberOfLines={1} style={styles.selectValue}>
          {value}
        </AppText>
      </View>
    </Pressable>
  );
}

function OptionPicker({
  visible,
  title,
  options,
  selectedKey,
  searchable,
  onClose,
  onSelect,
}: {
  visible: boolean;
  title: string;
  options: SelectOption[];
  selectedKey: string;
  searchable: boolean;
  onClose: () => void;
  onSelect: (opt: SelectOption) => void;
}) {
  const colors = useColors();
  const styles = useMemo(() => makeStyles(colors), [colors]);
  const insets = useSafeAreaInsets();
  const [filter, setFilter] = useState("");

  useEffect(() => {
    if (visible) setFilter("");
  }, [visible]);

  const filtered = useMemo(() => {
    const q = filter.trim();
    if (!q) return options;
    return options.filter((o) => o.label.includes(q) || o.key.includes(q));
  }, [options, filter]);

  return (
    <Modal
      visible={visible}
      animationType="slide"
      transparent
      onRequestClose={onClose}
    >
      <View style={styles.sheetRoot}>
        <Pressable style={styles.sheetBackdrop} onPress={onClose} />
        <View
          style={[
            styles.sheet,
            { paddingBottom: Math.max(insets.bottom, space.md) },
          ]}
        >
          <View style={styles.sheetHandle} />
          <View style={styles.sheetHeader}>
            <Pressable onPress={onClose} hitSlop={12} accessibilityLabel="بستن">
              <AppText variant="meta" tone="mist">
                بستن
              </AppText>
            </Pressable>
            <AppText variant="title">{title}</AppText>
            <View style={{ width: 36 }} />
          </View>

          {searchable ? (
            <TextInput
              value={filter}
              onChangeText={setFilter}
              placeholder="جستجو در فهرست…"
              placeholderTextColor={colors.mist}
              style={styles.sheetSearch}
              textAlign="right"
              autoCorrect={false}
              autoCapitalize="none"
            />
          ) : null}

          <FlatList
            data={filtered}
            keyExtractor={(item) =>
              item.lecturer ? `${item.lecturer}:${item.key}` : item.key
            }
            keyboardShouldPersistTaps="handled"
            style={styles.sheetList}
            renderItem={({ item }) => {
              const active = item.key === selectedKey;
              return (
                <Pressable
                  onPress={() => onSelect(item)}
                  style={[styles.sheetRow, active && styles.sheetRowActive]}
                >
                  {active ? (
                    <Ionicons
                      name="checkmark"
                      size={18}
                      color={colors.copper}
                    />
                  ) : (
                    <View style={{ width: 18 }} />
                  )}
                  <AppText
                    variant="body"
                    tone={active ? "ink" : "soft"}
                    style={styles.sheetRowLabel}
                    numberOfLines={2}
                  >
                    {item.label}
                  </AppText>
                </Pressable>
              );
            }}
            ListEmptyComponent={
              <View style={styles.empty}>
                <AppText variant="body" tone="mist" style={styles.center}>
                  موردی پیدا نشد.
                </AppText>
              </View>
            }
          />
        </View>
      </View>
    </Modal>
  );
}

function makeStyles(colors: ThemeColors) {
  return StyleSheet.create({
  content: {
    paddingHorizontal: space.lg,
    paddingTop: space.lg,
    gap: space.sm,
  },
  header: {
    gap: space.sm,
    marginBottom: space.md,
  },
  searchRow: {
    flexDirection: "row-reverse",
    alignItems: "center",
    gap: 10,
    marginTop: space.sm,
  },
  input: {
    flex: 1,
    fontFamily: type.regular,
    fontSize: 16,
    color: colors.ink,
    backgroundColor: colors.parchmentDeep,
    borderRadius: radii.md,
    paddingHorizontal: 16,
    paddingVertical: 12,
    writingDirection: "rtl",
  },
  searchBtn: {
    width: 48,
    height: 48,
    borderRadius: radii.md,
    backgroundColor: colors.ink,
    alignItems: "center",
    justifyContent: "center",
  },
  filters: {
    gap: 10,
    marginTop: space.xs,
  },
  selectField: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderRadius: radii.md,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: colors.line,
    backgroundColor: colors.parchment,
  },
  selectText: {
    flex: 1,
    alignItems: "flex-end",
    gap: 2,
  },
  selectValue: {
    textAlign: "right",
    writingDirection: "rtl",
  },
  searchingRow: {
    flexDirection: "row-reverse",
    alignItems: "center",
    gap: 8,
  },
  hit: {
    paddingVertical: space.md,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.line,
    gap: 6,
  },
  hitMeta: {
    flexDirection: "row-reverse",
    justifyContent: "space-between",
    alignItems: "center",
    gap: 8,
  },
  hitMetaText: {
    flex: 1,
    textAlign: "right",
  },
  empty: {
    paddingVertical: space.xxl,
  },
  center: { textAlign: "center" },
  moreBtn: {
    alignSelf: "center",
    paddingVertical: space.md,
    marginTop: space.sm,
  },
  sheetRoot: {
    flex: 1,
    justifyContent: "flex-end",
  },
  sheetBackdrop: {
    backgroundColor: "rgba(26, 36, 32, 0.35)",
    ...StyleSheet.absoluteFill,
  },
  sheet: {
    maxHeight: "72%",
    backgroundColor: colors.parchment,
    borderTopLeftRadius: radii.lg,
    borderTopRightRadius: radii.lg,
    paddingHorizontal: space.md,
    paddingTop: space.sm,
  },
  sheetHandle: {
    alignSelf: "center",
    width: 40,
    height: 4,
    borderRadius: 2,
    backgroundColor: colors.line,
    marginBottom: space.sm,
  },
  sheetHeader: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: space.sm,
  },
  sheetSearch: {
    fontFamily: type.regular,
    fontSize: 15,
    color: colors.ink,
    backgroundColor: colors.parchmentDeep,
    borderRadius: radii.md,
    paddingHorizontal: 14,
    paddingVertical: 10,
    writingDirection: "rtl",
    marginBottom: space.sm,
  },
  sheetList: {
    flexGrow: 0,
  },
  sheetRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    paddingVertical: 14,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.line,
  },
  sheetRowActive: {
    backgroundColor: colors.copperWash,
    marginHorizontal: -space.md,
    paddingHorizontal: space.md,
  },
  sheetRowLabel: {
    flex: 1,
    textAlign: "right",
    writingDirection: "rtl",
  },
});
}
