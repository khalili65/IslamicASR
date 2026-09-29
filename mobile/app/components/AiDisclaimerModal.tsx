import { useEffect, useState } from "react";
import {
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  View,
} from "react-native";
import AsyncStorage from "@react-native-async-storage/async-storage";
import { AppText } from "@/components/AppText";
import { radii, space } from "@/constants/theme";
import { useColors } from "@/lib/useTheme";

const STORAGE_KEY = "ai-disclaimer-dismissed-v1";

export function AiDisclaimerModal() {
  const colors = useColors();
  const [open, setOpen] = useState(false);

  useEffect(() => {
    let alive = true;
    void (async () => {
      try {
        const dismissed = await AsyncStorage.getItem(STORAGE_KEY);
        if (alive && dismissed !== "1") setOpen(true);
      } catch {
        if (alive) setOpen(true);
      }
    })();
    return () => {
      alive = false;
    };
  }, []);

  const dismiss = () => {
    void AsyncStorage.setItem(STORAGE_KEY, "1").catch(() => undefined);
    setOpen(false);
  };

  return (
    <Modal
      visible={open}
      transparent
      animationType="fade"
      onRequestClose={dismiss}
    >
      <View
        style={[styles.backdrop, { backgroundColor: "rgba(28, 22, 16, 0.45)" }]}
      >
        <Pressable style={StyleSheet.absoluteFill} onPress={dismiss} />
        <View
          style={[
            styles.card,
            {
              backgroundColor: colors.parchment,
              borderColor: colors.line,
            },
          ]}
        >
          <AppText variant="title" style={styles.title}>
            دربارهٔ متن درس‌گفتارها
          </AppText>
          <ScrollView
            style={styles.scroll}
            contentContainerStyle={styles.scrollContent}
            showsVerticalScrollIndicator={false}
          >
            <AppText variant="body" tone="soft" style={styles.body}>
              متن این درس‌گفتارها با بهره‌گیری از فناوری هوش مصنوعی و بر اساس
              فایل‌های صوتی تهیه شده است. از آنجا که دقت پیاده‌سازی به کیفیت
              صدای هر جلسه وابسته است، ممکن است در بخش‌هایی از متن، خطاها یا
              ابهام‌های جزئی وجود داشته باشد.
            </AppText>
            <AppText variant="body" tone="soft" style={styles.body}>
              این متن‌ها با هدف دسترسی آسان‌تر و استفاده بهتر از محتوای
              درس‌گفتارها در اختیار شما قرار گرفته‌اند. می‌توانید پس از شنیدن
              هر جلسه، مطالب را در قالب متن مرور کنید، در میان آن‌ها جستجو کنید،
              نسخه‌ای برای مطالعه یا چاپ تهیه کنید و در صورت نیاز، بخش‌هایی را
              به‌صورت دستی اصلاح نمایید.
            </AppText>
            <AppText variant="body" tone="soft" style={styles.body}>
              همچنین تلاش می‌کنیم با بهبود فناوری و بازبینی محتوا، به‌مرور
              نسخه‌های دقیق‌تر و کامل‌تری از متن‌ها ارائه کنیم.
            </AppText>
            <AppText variant="body" tone="soft" style={styles.body}>
              امیدواریم این امکان، مطالعه، مرور و بهره‌مندی از محتوای
              درس‌گفتارها را برای شما ساده‌تر و مفیدتر کند.
            </AppText>
          </ScrollView>
          <Pressable
            onPress={dismiss}
            style={[styles.button, { backgroundColor: colors.copper }]}
            accessibilityRole="button"
          >
            <AppText variant="meta" style={styles.buttonLabel}>
              متوجه شدم
            </AppText>
          </Pressable>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    flex: 1,
    justifyContent: "flex-end",
    padding: space.lg,
  },
  card: {
    borderRadius: radii.lg,
    borderWidth: StyleSheet.hairlineWidth,
    padding: space.lg,
    maxHeight: "78%",
    gap: space.md,
  },
  title: {
    textAlign: "right",
    writingDirection: "rtl",
  },
  scroll: {
    flexGrow: 0,
  },
  scrollContent: {
    gap: space.sm,
    paddingBottom: 4,
  },
  body: {
    textAlign: "right",
    writingDirection: "rtl",
    lineHeight: 26,
  },
  button: {
    alignSelf: "flex-start",
    borderRadius: radii.md,
    paddingHorizontal: space.lg,
    paddingVertical: 12,
  },
  buttonLabel: {
    color: "#fff",
    fontWeight: "700",
  },
});
