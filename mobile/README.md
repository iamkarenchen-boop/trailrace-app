# TrailRace Mobile (iPhone first)

Native React Native + Expo app. The existing GitHub Pages website stays unchanged.

## Run on Mac

1. Install Node.js LTS from https://nodejs.org/ (if needed).
2. Open Terminal and run:

```bash
cd ~/trailrace-app/mobile
npm install
npx expo start --tunnel
```

3. Open Expo Go on iPhone and scan the QR code. Expo Go alone does not host the app; the Mac development server must be running.

If the repository is not on the Mac yet, clone it first using GitHub Desktop or `git clone https://github.com/iamkarenchen-boop/trailrace-app.git`.

The app currently loads public catalog JSON from GitHub Pages. Personal saved races are stored **only on this device**, not synchronized. Notifications, accounts, App Store builds, and verification of the iOS runtime are not yet implemented.
