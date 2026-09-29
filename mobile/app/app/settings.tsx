import { Pressable, ScrollView, StyleSheet, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import { Screen } from "@/components/Screen";
import { AppText } from "@/components/AppText";
import { THEMES, type ThemeId, radii, space } from "@/constants/theme";
import { useTheme } from "@/lib/useTheme";

const ORDER: ThemeId[] = ["warm", "night", "cool"];

export default function SettingsScreen() {
  const insets = useSafeAreaInsets();
  const { themeId, colors, setThemeId } = useTheme();

  return (
    <Screen>
      <ScrollView
        contentContainerStyle={[
          styles.content,
          { paddingBottom: insets.bottom + space.xl },
        ]}
      >
        <AppText variant="display">تنظیمات</AppText>
        <AppText variant="body" tone="mist" style={styles.lead}>
          ظاهر برنامه را برای روز یا شب انتخاب کنید. پخش‌کننده زیرنویس همیشه
          پس‌زمینهٔ تیره می‌ماند.
        </AppText>

        <AppText variant="caption" tone="mist" style={styles.sectionLabel}>
          پوسته
        </AppText>

        <View style={styles.cards}>
          {ORDER.map((id) => {
            const meta = THEMES[id];
            const active = themeId === id;
            return (
              <Pressable
                key={id}
                onPress={() => void setThemeId(id)}
                style={[
                  styles.card,
                  {
                    backgroundColor: colors.parchmentDeep,
                    borderColor: active ? colors.copper : colors.line,
                  },
                  active && { backgroundColor: colors.copperWash },
                ]}
                accessibilityRole="button"
                accessibilityState={{ selected: active }}
              >
                <View style={styles.cardTop}>
                  <View style={styles.swatches}>
                    <View
                      style={[
                        styles.swatch,
                        { backgroundColor: meta.colors.parchment },
                      ]}
                    />
                    <View
                      style={[
                        styles.swatch,
                        { backgroundColor: meta.colors.ink },
                      ]}
                    />
                    <View
                      style={[
                        styles.swatch,
                        { backgroundColor: meta.colors.copper },
                      ]}
                    />
                    <View
                      style={[
                        styles.swatch,
                        { backgroundColor: meta.colors.stage },
                      ]}
                    />
                  </View>
                  {active ? (
                    <Ionicons
                      name="checkmark-circle"
                      size={22}
                      color={colors.copper}
                    />
                  ) : (
                    <Ionicons
                      name="ellipse-outline"
                      size={22}
                      color={colors.mist}
                    />
                  )}
                </View>
                <AppText variant="title">{meta.label}</AppText>
                <AppText variant="caption" tone="mist">
                  {meta.hint}
                </AppText>
              </Pressable>
            );
          })}
        </View>
      </ScrollView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  content: {
    paddingHorizontal: space.lg,
    paddingTop: space.lg,
    gap: space.sm,
  },
  lead: {
    marginBottom: space.md,
  },
  sectionLabel: {
    marginTop: space.sm,
    marginBottom: 4,
  },
  cards: {
    gap: 12,
  },
  card: {
    borderRadius: radii.lg,
    borderWidth: StyleSheet.hairlineWidth,
    padding: space.md,
    gap: 6,
  },
  cardTop: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: 4,
  },
  swatches: {
    flexDirection: "row",
    gap: 6,
  },
  swatch: {
    width: 22,
    height: 22,
    borderRadius: 6,
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: "rgba(0,0,0,0.12)",
  },
});
