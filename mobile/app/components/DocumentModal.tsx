import { useEffect, useMemo, useState } from "react";
import {
  Modal,
  View,
  ScrollView,
  StyleSheet,
  Pressable,
  ActivityIndicator,
  useWindowDimensions,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import RenderHTML from "react-native-render-html";
import { AppText } from "./AppText";
import { space, type, type ThemeColors } from "@/constants/theme";
import { useColors } from "@/lib/useTheme";
import { markdownToHtml } from "@/lib/markdownToHtml";

type Props = {
  visible: boolean;
  title: string;
  url: string | null;
  inlineText?: string | null;
  onClose: () => void;
};

export function DocumentModal({
  visible,
  title,
  url,
  inlineText,
  onClose,
}: Props) {
  const colors = useColors();
  const styles = useMemo(() => makeStyles(colors), [colors]);
  const insets = useSafeAreaInsets();
  const { width } = useWindowDimensions();
  const [raw, setRaw] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!visible) return;
    let cancelled = false;
    setLoading(true);
    setError(null);

    const apply = (body: string) => {
      if (!cancelled) {
        setRaw(body);
        setLoading(false);
      }
    };

    if (!url) {
      if (inlineText) apply(inlineText);
      else {
        setError("متن در دسترس نیست.");
        setLoading(false);
      }
      return;
    }

    fetch(url)
      .then((r) => {
        if (!r.ok) throw new Error(String(r.status));
        return r.text();
      })
      .then(apply)
      .catch(() => {
        if (inlineText) apply(inlineText);
        else if (!cancelled) {
          setError("بارگذاری متن انجام نشد.");
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [visible, url, inlineText]);

  const html = useMemo(
    () => (raw ? `<article dir="rtl">${markdownToHtml(raw)}</article>` : ""),
    [raw],
  );

  const contentWidth = Math.max(280, width - space.lg * 2);

  const tagsStyles = useMemo(
    () => ({
      body: {
        color: colors.ink,
        fontSize: 15,
        lineHeight: 28,
        textAlign: "right" as const,
        writingDirection: "rtl" as const,
        fontFamily: type.regular,
      },
      p: {
        marginBottom: 14,
        textAlign: "right" as const,
      },
      h1: {
        fontSize: 22,
        lineHeight: 34,
        fontFamily: type.bold,
        marginTop: 8,
        marginBottom: 14,
        textAlign: "right" as const,
        color: colors.ink,
      },
      h2: {
        fontSize: 18,
        lineHeight: 30,
        fontFamily: type.bold,
        marginTop: 20,
        marginBottom: 10,
        textAlign: "right" as const,
        color: colors.ink,
      },
      h3: {
        fontSize: 16,
        lineHeight: 26,
        fontFamily: type.medium,
        marginTop: 16,
        marginBottom: 8,
        textAlign: "right" as const,
      },
      h4: {
        fontSize: 15,
        lineHeight: 24,
        fontFamily: type.medium,
        marginTop: 12,
        marginBottom: 6,
        textAlign: "right" as const,
      },
      strong: {
        fontFamily: type.bold,
        color: colors.ink,
      },
      em: {
        fontFamily: type.medium,
      },
      blockquote: {
        backgroundColor: colors.parchmentDeep,
        borderRightWidth: 3,
        borderRightColor: colors.copper,
        paddingVertical: 10,
        paddingHorizontal: 14,
        marginVertical: 12,
        borderRadius: 8,
      },
      ul: {
        marginBottom: 12,
        paddingRight: 18,
      },
      li: {
        marginBottom: 6,
        textAlign: "right" as const,
      },
      hr: {
        marginVertical: 16,
        borderBottomColor: colors.line,
        borderBottomWidth: StyleSheet.hairlineWidth,
      },
      // Quran / Hadith cards from book.md
      "p.ayah-ar": {
        fontSize: 22,
        lineHeight: 40,
        fontFamily: "Amiri_400Regular",
        textAlign: "center" as const,
        marginVertical: 16,
        color: colors.ink,
      },
      "span.ayah-ref": {
        fontSize: 13,
        fontFamily: type.regular,
        color: colors.mist,
      },
      "p.ayah": {
        fontSize: 20,
        lineHeight: 36,
        fontFamily: "Amiri_400Regular",
        textAlign: "center" as const,
        marginVertical: 14,
      },
    }),
    [],
  );

  const classesStyles = useMemo(
    () => ({
      "ayah-ar": {
        fontSize: 22,
        lineHeight: 40,
        fontFamily: "Amiri_400Regular",
        textAlign: "center" as const,
        marginVertical: 16,
        color: colors.ink,
      },
      "ayah-ref": {
        fontSize: 13,
        fontFamily: type.regular,
        color: colors.mist,
      },
      ayah: {
        fontSize: 20,
        lineHeight: 36,
        fontFamily: "Amiri_400Regular",
        textAlign: "center" as const,
        marginVertical: 14,
      },
    }),
    [],
  );

  return (
    <Modal
      visible={visible}
      animationType="slide"
      presentationStyle="pageSheet"
      onRequestClose={onClose}
    >
      <View
        style={[
          styles.root,
          { paddingTop: insets.top + 8, paddingBottom: insets.bottom + 8 },
        ]}
      >
        <View style={styles.header}>
          <Pressable onPress={onClose} style={styles.close} hitSlop={12}>
            <AppText variant="meta" tone="ink">
              بستن
            </AppText>
          </Pressable>
          <AppText variant="title" numberOfLines={1} style={styles.title}>
            {title}
          </AppText>
          <View style={styles.close} />
        </View>

        {loading ? (
          <View style={styles.center}>
            <ActivityIndicator color={colors.ink} />
          </View>
        ) : error ? (
          <View style={styles.center}>
            <AppText tone="mist">{error}</AppText>
          </View>
        ) : (
          <ScrollView
            contentContainerStyle={styles.body}
            showsVerticalScrollIndicator={false}
          >
            <RenderHTML
              contentWidth={contentWidth}
              source={{ html }}
              tagsStyles={tagsStyles}
              classesStyles={classesStyles}
              defaultTextProps={{
                selectable: true,
              }}
              systemFonts={[
                type.regular,
                type.medium,
                type.bold,
                "Amiri_400Regular",
                "Amiri_700Bold",
              ]}
            />
          </ScrollView>
        )}
      </View>
    </Modal>
  );
}

function makeStyles(colors: ThemeColors) {
  return StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.parchment },
  header: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: space.md,
    paddingBottom: space.sm,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: colors.line,
  },
  close: { minWidth: 56, minHeight: 44, justifyContent: "center" },
  title: { flex: 1, textAlign: "center" },
  center: { flex: 1, alignItems: "center", justifyContent: "center" },
  body: {
    paddingHorizontal: space.lg,
    paddingVertical: space.lg,
    paddingBottom: space.xxl,
  },
});
}
