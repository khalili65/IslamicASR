import { useLayoutEffect } from "react";
import { FlatList, View, StyleSheet, Image } from "react-native";
import { useLocalSearchParams, useNavigation, useRouter } from "expo-router";
import { Screen } from "@/components/Screen";
import { AppText } from "@/components/AppText";
import { CourseRow } from "@/components/Rows";
import { radii, space } from "@/constants/theme";
import { useColors } from "@/lib/useTheme";
import { useLibraryStore } from "@/lib/store";
import { resolveAssetUrl } from "@/lib/format";

export default function LecturerScreen() {
  const colors = useColors();
  const { slug } = useLocalSearchParams<{ slug: string }>();
  const lecturer = useLibraryStore((s) => s.findLecturer(slug));
  const navigation = useNavigation();
  const router = useRouter();

  useLayoutEffect(() => {
    navigation.setOptions({ title: lecturer?.name ?? "استاد" });
  }, [navigation, lecturer?.name]);

  if (!lecturer) {
    return (
      <Screen>
        <View style={styles.missing}>
          <AppText variant="body" tone="mist" style={styles.center}>
            استاد پیدا نشد. از کتابخانه دوباره وارد شوید.
          </AppText>
        </View>
      </Screen>
    );
  }

  const isBayat = lecturer.slug === "bayat";
  const avatar =
    !isBayat ? resolveAssetUrl(lecturer.avatar, lecturer.dataBase) : "";

  return (
    <Screen>
      <FlatList
        data={lecturer.courses}
        keyExtractor={(c) => c.slug}
        contentContainerStyle={styles.content}
        ListHeaderComponent={
          <View style={styles.hero}>
            {avatar ? (
              <Image source={{ uri: avatar }} style={styles.avatar} />
            ) : isBayat ? (
              <View
                style={[
                  styles.avatar,
                  styles.avatarFallback,
                  { backgroundColor: colors.parchmentDeep },
                ]}
              >
                <AppText variant="title" tone="mist">
                  بیات
                </AppText>
              </View>
            ) : null}
            <AppText variant="display" style={styles.name}>
              {lecturer.name}
            </AppText>
            <AppText variant="meta" tone="mist" style={styles.center}>
              {lecturer.title}
            </AppText>
            {lecturer.bio ? (
              <AppText variant="body" tone="soft" style={styles.bio}>
                {lecturer.bio}
              </AppText>
            ) : null}
          </View>
        }
        renderItem={({ item }) => (
          <CourseRow
            course={item}
            dataBase={lecturer.dataBase}
            textOnly={isBayat}
            onPress={() =>
              router.push({
                pathname: "/course/[lecturer]/[course]",
                params: { lecturer: lecturer.slug, course: item.slug },
              })
            }
          />
        )}
      />
    </Screen>
  );
}

const styles = StyleSheet.create({
  content: {
    paddingHorizontal: space.xxl,
    paddingBottom: space.xxl,
  },
  missing: { padding: space.lg },
  hero: {
    alignItems: "center",
    paddingTop: space.md,
    paddingBottom: space.xl,
  },
  avatar: {
    width: 72,
    height: 72,
    borderRadius: radii.md,
    marginBottom: space.md,
  },
  avatarFallback: {
    
    alignItems: "center",
    justifyContent: "center",
  },
  name: { textAlign: "center", writingDirection: "rtl", fontSize: 24 },
  center: { textAlign: "center", writingDirection: "rtl" },
  bio: {
    textAlign: "center",
    writingDirection: "rtl",
    marginTop: space.sm,
    maxWidth: 340,
  },
});
