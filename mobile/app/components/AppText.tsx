import { Text as RNText, type TextProps, StyleSheet } from "react-native";
import { colors, type } from "@/constants/theme";

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
  return (
    <RNText
      {...rest}
      style={[styles.base, styles[variant], tones[tone], style]}
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
    letterSpacing: -0.4,
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

const tones = StyleSheet.create({
  ink: { color: colors.ink },
  soft: { color: colors.inkSoft },
  mist: { color: colors.mist },
  copper: { color: colors.copper },
  stage: { color: colors.stageFg },
  stageMuted: { color: colors.stageMuted },
});
