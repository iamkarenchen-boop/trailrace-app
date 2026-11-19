# TrailRace — iPhone App Store launch checklist

## Build readiness
- [x] Expo project and unique iOS bundle ID configured.
- [x] EAS preview and production profiles committed.
- [x] Public privacy policy drafted and hosted by GitHub Pages after deployment.
- [ ] Create/confirm Apple Developer Program membership (annual fee applies).
- [ ] Confirm the bundle ID `com.trailrace.app` is available and owned by this team; change before first production build if necessary.
- [ ] Sign in to Expo account; link project with `eas init` to populate `extra.eas.projectId`.
- [ ] Create production app icon (1024×1024 PNG), launch screen assets and required screenshots; test on physical iPhone.
- [ ] Validate iOS release build and app functionality without Expo Go.
- [ ] Add app in App Store Connect, select age rating, category, support URL, privacy policy URL, privacy nutrition labels, review contact, screenshots and description.
- [ ] Complete TestFlight testing, review data correctness, accessibility, offline/error behavior, external link behavior.
- [ ] Submit for Apple review. Approval is not guaranteed.

## Commands (Mac, inside mobile/)
```bash
npm install
npx expo-doctor
npx eas-cli login
npx eas-cli init
npx eas-cli build --platform ios --profile preview
npx eas-cli build --platform ios --profile production
npx eas-cli submit --platform ios --profile production
```

The Apple Developer team must authenticate and authorize certificates, identifiers, and submission. Never commit Apple credentials or Expo access tokens.

## Current data behavior
- Catalog data fetched from public GitHub Pages JSON, so it needs an internet connection.
- Personal race calendar, following, and participation status are saved locally on device via AsyncStorage; they are not uploaded to TrailRace servers.
- Export backup uses the iOS share sheet only when the user requests it. Restoring a backup overwrites local records after confirmation.
- No account login, push notifications, analytics, advertising, or purchase flow currently.
- Source page checks do not guarantee that race dates, fees, availability, or rules are up to date. Do not advertise real-time official sync before it is implemented and validated.

## App Review concerns
- Provide working demo and stable production data; no placeholder claims of fully verified listings.
- Ensure legal right to use names/logos/brand assets; do not imply affiliation with UTMB or any race organizer.
- Link to official race pages for confirmation.
- Verify privacy policy against actual app dependencies and any later SDK integrations.
- If adding accounts, analytics, notifications, or payments, update privacy disclosures and app review answers before release.
