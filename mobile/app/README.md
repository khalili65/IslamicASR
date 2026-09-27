# تذکار — mobile app

Expo (React Native) client for iOS and Android. Reads the same published
JSON + audio as the websites (Arvan), all lecturers in one library.

**تذکار** = reminder / bringing knowledge to mind (Islamic Persian).

## Design

Courtyard dusk: parchment stone, green ink, copper accent, Amiri + Vazirmatn,
RTL Persian. Quiet list layout — not a SaaS card grid.

## Run

```bash
cd mobile/app
npm install
npx expo start
```

Physical iPhone (USB, same Apple ID / trusted):

```bash
cd mobile/app
npx expo run:ios --device
```

Or install **Expo Go**, then `npx expo start` and scan the QR (same Wi‑Fi).

## Structure

```
app/                 Expo Router screens
components/          UI + LecturePlayer
constants/theme.ts   Design tokens + site CDN bases
lib/                 types, api, format, store (shared with web ideas)
```
