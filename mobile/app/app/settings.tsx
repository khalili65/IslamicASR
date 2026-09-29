import { Linking, Pressable, ScrollView, StyleSheet, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { Ionicons } from "@expo/vector-icons";
import { Screen } from "@/components/Screen";
import { AppText } from "@/components/AppText";
import { THEMES, type ThemeId, radii, space } from "@/constants/theme";
import { useTheme } from "@/lib/useTheme";

const ORDER: ThemeId[] = ["warm", "night", "cool"];
const CONTACT_EMAIL = "m.khalilishoja@gmail.com";

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

        <AppText variant="caption" tone="mist" style={styles.sectionLabel}>
          تماس با ما
        </AppText>
        <View
          style={[
            styles.infoCard,
            {
              backgroundColor: colors.parchmentDeep,
              borderColor: colors.line,
            },
          ]}
        >
          <AppText variant="body" tone="soft" style={styles.infoBody}>
            اگر پرسشی دارید، پیشنهادی دربارهٔ برنامه، یا نیاز به اطلاعات بیشتر،
            می‌توانید از طریق ایمیل زیر پیام بفرستید.
          </AppText>
          <Pressable
            onPress={() => void Linking.openURL(`mailto:${CONTACT_EMAIL}`)}
            style={styles.emailRow}
            accessibilityRole="link"
            accessibilityLabel={CONTACT_EMAIL}
          >
            <Ionicons name="mail-outline" size={18} color={colors.copper} />
            <AppText variant="meta" tone="copper" style={styles.email}>
              {CONTACT_EMAIL}
            </AppText>
          </Pressable>
        </View>

        <AppText variant="caption" tone="mist" style={styles.sectionLabel}>
          دربارهٔ متن درس‌گفتارها
        </AppText>
        <View
          style={[
            styles.infoCard,
            {
              backgroundColor: colors.parchmentDeep,
              borderColor: colors.line,
            },
          ]}
        >
          <AppText variant="body" tone="soft" style={styles.infoBody}>
            متن این درس‌گفتارها با بهره‌گیری از فناوری هوش مصنوعی و بر اساس
            فایل‌های صوتی تهیه شده است. از آنجا که دقت پیاده‌سازی به کیفیت صدای
            هر جلسه وابسته است، ممکن است در بخش‌هایی از متن، خطاها یا ابهام‌های
            جزئی وجود داشته باشد.
          </AppText>
          <AppText variant="body" tone="soft" style={styles.infoBody}>
            این متن‌ها با هدف دسترسی آسان‌تر و استفاده بهتر از محتوای
            درس‌گفتارها در اختیار شما قرار گرفته‌اند. می‌توانید پس از شنیدن هر
            جلسه، مطالب را در قالب متن مرور کنید، در میان آن‌ها جستجو کنید،
            نسخه‌ای برای مطالعه یا چاپ تهیه کنید و در صورت نیاز، بخش‌هایی را
            به‌صورت دستی اصلاح نمایید.
          </AppText>
          <AppText variant="body" tone="soft" style={styles.infoBody}>
            همچنین تلاش می‌کنیم با بهبود فناوری و بازبینی محتوا، به‌مرور
            نسخه‌های دقیق‌تر و کامل‌تری از متن‌ها ارائه کنیم.
          </AppText>
          <AppText variant="body" tone="soft" style={styles.infoBody}>
            امیدواریم این امکان، مطالعه، مرور و بهره‌مندی از محتوای درس‌گفتارها
            را برای شما ساده‌تر و مفیدتر کند.
          </AppText>
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
    marginTop: space.md,
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
  infoCard: {
    borderRadius: radii.lg,
    borderWidth: StyleSheet.hairlineWidth,
    padding: space.md,
    gap: space.sm,
  },
  infoBody: {
    textAlign: "right",
    writingDirection: "rtl",
    lineHeight: 26,
  },
  emailRow: {
    flexDirection: "row-reverse",
    alignItems: "center",
    gap: 8,
    paddingTop: 4,
  },
  email: {
    writingDirection: "ltr",
    textAlign: "left",
  },
});
