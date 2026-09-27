# Mobile app (iOS + Android)

| Doc | Purpose |
| --- | --- |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | Stack + how mobile sits on the platform |
| [SYNC.md](./SYNC.md) | Unified catalog + incremental sync design |
| [DATA_CONTRACT.md](./DATA_CONTRACT.md) | JSON shapes (same as web) |
| [app/](./app/) | **Expo app** — run this |

## App

**تذکار** — Persian RTL lecture library + synced player. Loads **all lecturers** from both
Arvan sites (Bayat + portal) at runtime — no app release needed for new courses.

```bash
cd mobile/app
npm install
npx expo start
```

- **Simulator:** `npx expo run:ios`
- **Physical iPhone (Expo Go):** install Expo Go, same Wi‑Fi, open the `exp://` URL from the terminal
- **Native install:** needs a valid Xcode Apple ID login + provisioning for `ir.islamasr.tazkar`
