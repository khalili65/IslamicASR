import { Text as RNText, type TextProps, StyleSheet } from "react-native";
import { type } from "@/constants/theme";
import { useColors } from "@/lib/useTheme";

type Props = TextProps & {
  variant?: "display" | "title" | "body" | "meta" | "caption";
  tone?: "ink" | "soft" | "mist" | "copper" | "stage" | "stageMuted";
};

export function AppText({
  variant = "body",
  tone = "ink",
  style,
  ...rest
}: Props) {
  const colors = useColors();
  const toneColor =
    tone === "soft"
      ? colors.inkSoft
      : tone === "mist"
        ? colors.mist
        : tone === "copper"
          ? colors.copper
          : tone === "stage"
            ? colors.stageFg
            : tone === "stageMuted"
              ? colors.stageMuted
              : colors.ink;

  return (
    <RNText
      {...rest}
      style={[styles.base, styles[variant], { color: toneColor }, style]}
    />
  );
}

const styles = StyleSheet.create({
  base: {
    writingDirection: "rtl",
    textAlign: "right",
  },
  display: {
    fontFamily: type.bold,
    fontSize: 30,
    lineHeight: 42,
    letterSpacing: 0,
  },
  title: {
    fontFamily: type.medium,
    fontSize: 17,
    lineHeight: 26,
  },
  body: {
    fontFamily: type.regular,
    fontSize: 15,
    lineHeight: 24,
  },
  meta: {
    fontFamily: type.regular,
    fontSize: 13,
    lineHeight: 20,
  },
  caption: {
    fontFamily: type.medium,
    fontSize: 12,
    lineHeight: 18,
  },
});
