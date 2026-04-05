# D.D. Companion -- Mobile App Architecture

## 1. Tech Stack

| Layer | Technology | Version |
|---|---|---|
| Framework | React Native | 0.84.1 |
| Language | TypeScript | 5.8.3 |
| Runtime | React | 19.2.3 |
| JS Engine | Hermes (New Architecture enabled) | -- |
| Navigation | React Navigation (bottom-tabs + native-stack) | 7.x |
| Auth | Firebase Auth (`@react-native-firebase/auth`) | 24.0.0 |
| Push Notifications | Firebase Cloud Messaging (`@react-native-firebase/messaging`) | 24.0.0 |
| Google Sign-In | `@react-native-google-signin/google-signin` | 16.1.2 |
| Image Picker | `react-native-image-picker` | 8.2.1 |
| Storage | `@react-native-async-storage/async-storage` | 2.2.0 |
| Safe Area | `react-native-safe-area-context` + `react-native-screens` | 5.7.0 / 4.24.0 |
| Node requirement | >= 22.11.0 | -- |

The New Architecture (Fabric/TurboModules) is enabled via `RCTNewArchEnabled = true` in `Info.plist`.

## 2. App Structure

### Entry Point

`index.js` registers the background FCM handler, then mounts `App.tsx`:

```
index.js
  -> registerBackgroundHandler()  (FCM background messages)
  -> AppRegistry.registerComponent('CompanionApp', () => App)

App.tsx
  -> SafeAreaProvider
    -> StatusBar (dark-content)
    -> AuthProvider          (Firebase Auth context)
      -> AppNavigator        (routing logic)
```

### Navigation Flow

`AppNavigator` implements a state machine with four possible states:

1. **Loading** -- Firebase auth state resolving (shows nothing)
2. **Unauthenticated** -- renders `LoginScreen` (no NavigationContainer)
3. **Profile incomplete** -- renders `OnboardingScreen` (no NavigationContainer)
4. **Authenticated + profile complete** -- renders the main tab navigator inside `NavigationContainer`

The profile completeness check calls `GET /api/v1/me` and examines whether `first_name` and `last_name` are set (or `profile_complete === true` in the structured response variant).

### Tab Layout

| Tab | Screen Component | Header Title |
|---|---|---|
| Today | `TodayScreen` | "Today" |
| Chat | `ChatScreen` | "D.D." |
| My Stuff | `MyStuffScreen` | "My Stuff" |
| Profile | `ProfileScreen` | "Profile" |

Tab icons are emoji-based text elements (no icon library). Active tabs use `colors.blue` tint and `fontSize: 22`; inactive use `colors.gray400` with `opacity: 0.5`.

Tab bar height is 84pt with 4pt top padding.

## 3. Authentication Flow

### AuthProvider (`src/auth/AuthProvider.tsx`)

Wraps the app in a React context providing:

- `user` -- `FirebaseAuthTypes.User | null`
- `loading` -- boolean (true until first `onAuthStateChanged` fires)
- `signInWithGoogle()` -- Google Sign-In flow
- `signInWithEmail(email, password)` -- email/password sign-in
- `registerWithEmail(email, password)` -- email/password registration
- `signOut()` -- signs out and deactivates the FCM token on the backend

### Google Sign-In

1. `GoogleSignin.configure({ scopes: ['email', 'profile'] })` runs on mount.
2. `GoogleSignin.hasPlayServices()` is checked.
3. `GoogleSignin.signIn()` returns an ID token from `signInResult.data.idToken`.
4. The ID token is exchanged for a Firebase credential via `auth.GoogleAuthProvider.credential(idToken)`.
5. `auth().signInWithCredential(credential)` completes the sign-in.

The iOS URL scheme `com.googleusercontent.apps.381910341082-qsibpjm2chltt1998dpubc52eop27bub` is registered in `Info.plist` to handle the Google OAuth redirect.

### Email/Password Auth

`LoginScreen` supports two modes toggled by the user: login and register. It provides:
- Email/password fields with validation
- Friendly error messages mapped from Firebase error codes (`auth/user-not-found`, `auth/wrong-password`, `auth/email-already-in-use`, `auth/weak-password`, `auth/invalid-email`)
- Password reset via `auth().sendPasswordResetEmail()`

### Sign-Out

On sign-out, `AuthProvider.signOut()`:
1. Calls `DELETE /api/v1/me/devices` with the current FCM token to deactivate push notifications.
2. Calls `auth().signOut()`.

### Email Verification

`VerifyEmailScreen` exists in `src/auth/VerifyEmailScreen.tsx` but is not currently wired into the navigation flow in `AppNavigator`. It provides resend-verification and manual reload of `emailVerified` status.

### Onboarding

After first sign-in, users without a backend profile land on `OnboardingScreen`, a two-step flow:

1. **Profile** -- first name (required), last name, preferred name, phone number. Calls `POST /api/v1/auth/complete-profile`.
2. **Invite caregiver** -- uses the shared `InviteCaregiverForm` component. Can be skipped.

Step indicators (dots) show progress.

## 4. API Integration

### Client (`src/api/client.ts`)

A single generic `api<T>()` function wraps `fetch`:

```typescript
export async function api<T>(path: string, options?: RequestInit): Promise<T>
```

**Base URL:**
```
https://companion-staging-backend-381910341082.us-central1.run.app
```
(Same URL for both `__DEV__` and production -- currently pointing at the staging Cloud Run service.)

**Auth headers:** On every request, the current Firebase user's ID token is fetched via `user.getIdToken()` and attached as `Authorization: Bearer <token>`. All requests include `Content-Type: application/json`.

**Error handling:** Non-2xx responses throw `Error(`API error: ${status}`)`. 204 responses return `{}` without parsing JSON.

**API endpoints used by the app:**

| Method | Path | Used By |
|---|---|---|
| GET | `/api/v1/me` | AppNavigator (profile check), ProfileScreen |
| POST | `/api/v1/auth/complete-profile` | OnboardingScreen |
| GET | `/api/v1/medications` | TodayScreen, MyStuffScreen |
| GET | `/api/v1/appointments` | TodayScreen, MyStuffScreen |
| GET | `/api/v1/bills` | TodayScreen, MyStuffScreen |
| GET | `/api/v1/todos` | TodayScreen, MyStuffScreen |
| POST | `/api/v1/todos/{id}/complete` | TodayScreen, MyStuffScreen |
| GET | `/api/v1/reviews/pending` | TodayScreen |
| GET | `/api/v1/sections/today` | TodayScreen |
| POST | `/api/v1/conversation/start` | ChatScreen |
| POST | `/api/v1/conversation/message` | ChatScreen |
| POST | `/api/v1/documents/scan` | ScanButton (multipart form) |
| POST | `/api/v1/documents/scan/analyze` | useImageAnalysis hook (multipart form) |
| GET | `/api/v1/me/caregivers` | ProfileScreen |
| POST | `/api/v1/invitations` | InviteCaregiverForm |
| DELETE | `/api/v1/contacts/{id}` | ProfileScreen |
| POST | `/api/v1/me/devices` | usePushNotifications (token registration) |
| DELETE | `/api/v1/me/devices` | AuthProvider (sign-out) |
| POST | `/api/v1/me/request-deletion` | ProfileScreen |

## 5. Push Notifications

### FCM Setup

**Native side (`AppDelegate.swift`):**
- `FirebaseApp.configure()` on launch
- `application.registerForRemoteNotifications()` on launch
- `UNUserNotificationCenter.current().delegate = self` for foreground display
- APNS token forwarded to `Messaging.messaging().apnsToken`
- Foreground notifications displayed as banner + badge + sound

**Background handler (`src/notifications/backgroundHandler.ts`):**
- Registered in `index.js` before `AppRegistry.registerComponent` (required by Firebase)
- Logs message ID; no further processing

**JS-side hook (`src/hooks/usePushNotifications.ts`):**

The `usePushNotifications(isAuthenticated)` hook is activated once the user has a complete profile:

1. Requests notification permission via `messaging().requestPermission()`
2. Registers for remote messages if not already registered
3. Gets FCM token and sends it to `POST /api/v1/me/devices` with `{ fcm_token, platform }`
4. Listens for token refresh and re-registers
5. Foreground messages shown via `Alert.alert(title, body)`
6. Cleanup unsubscribes refresh and message listeners

### Info.plist Configuration

- `UIBackgroundModes` includes `remote-notification`
- GCM is enabled in `GoogleService-Info.plist` (`IS_GCM_ENABLED = true`)

## 6. Document Scanning

### VisionKit Native Module (`ios/CompanionApp/DocumentScannerModule.swift`)

A native iOS module exposing Apple's `VNDocumentCameraViewController` to React Native.

**Bridge file** (`DocumentScannerModule.m`): Standard Objective-C bridge using `RCT_EXTERN_MODULE` and `RCT_EXTERN_METHOD`.

**JS interface:**
```typescript
NativeModules.DocumentScannerModule.scanDocument(): Promise<string[]>
```
Returns an array of `file://` URIs, one per scanned page.

**Behavior:**
1. Checks `VNDocumentCameraViewController.isSupported`
2. Presents the scanner modally on the main queue
3. On success, iterates all pages from `VNDocumentCameraScan`
4. Each page image is resized (max dimension 2048px) and saved as JPEG (quality 0.8) to a temp directory
5. Returns array of file URIs
6. On cancel, returns empty array
7. On failure, rejects with `SCAN_FAILED` error code

**Multi-page support:** Fully supported. The scanner captures `scan.pageCount` pages and returns all URIs.

### ScanButton Component (`src/components/ScanButton.tsx`)

A floating action button (FAB) positioned at bottom-right of the screen. Present on `TodayScreen` and `MyStuffScreen`.

**Flow:**
1. On press, shows an action sheet: "Scan Document" or "Choose from Library"
2. "Scan Document" invokes `DocumentScannerModule.scanDocument()` (VisionKit)
3. "Choose from Library" uses `react-native-image-picker` with `selectionLimit: 0` (multi-select)
4. Selected images are uploaded as multipart form data to `POST /api/v1/documents/scan`
5. Upload status is shown via a badge above the FAB: Uploading / Processing / Done / Failed

### Image Analysis Hook (`src/hooks/useImageAnalysis.ts`)

A hook for analyzing scanned image quality. Sends images to `POST /api/v1/documents/scan/analyze` as multipart form data. Returns:
- `status`: 'good' | 'poor' | 'error'
- `feedback`: string description
- `has_text`: boolean
- `brightness`: number

## 7. Screen Inventory

### LoginScreen (`src/auth/LoginScreen.tsx`)
Card-centered layout with brand emoji and name. Offers Google Sign-In button, email/password fields, login/register toggle, and forgot-password flow.

### OnboardingScreen (`src/auth/OnboardingScreen.tsx`)
Two-step onboarding: profile creation (name, phone) then caregiver invitation. Step indicator dots at bottom.

### VerifyEmailScreen (`src/auth/VerifyEmailScreen.tsx`)
Email verification prompt with resend and manual check buttons. Not currently active in navigation.

### TodayScreen (`src/screens/TodayScreen.tsx`)
The home screen. Time-based greeting with user's first name. Loads data from five endpoints in parallel. Displays cards for:
- **Mail** -- pending document reviews with badge count, urgent items highlighted in amber. Tapping navigates to Chat with `reviewId`.
- **Medications** -- active medications with dosage and frequency.
- **Appointments** -- next 3 upcoming appointments with date/time.
- **To Do** -- up to 5 pending todos with checkbox toggle (optimistic updates).
- **Bills** -- up to 3 bills with amount and due date.
- Empty state message when nothing is pending.

Includes `ScanButton` FAB. Data refreshes on every screen focus via `useFocusEffect`.

### ChatScreen (`src/screens/ChatScreen.tsx`)
Conversational interface with the D.D. assistant. Features:
- Session management via `POST /api/v1/conversation/start` (triggers: `user_initiated`, `document_review`, `morning_checkin`)
- Message exchange via `POST /api/v1/conversation/message`
- Instant static greeting while backend session initializes
- Chat bubbles with user messages (blue, right-aligned) and assistant messages (white, left-aligned with "D.D." label)
- Typing indicator during response
- Keyboard-avoiding input bar with send button
- Accepts `reviewId` and `briefing` params from navigation

### MyStuffScreen (`src/screens/MyStuffScreen.tsx`)
Tabbed data browser with four sub-tabs: Meds, Appts, Bills, To Do. Each tab fetches from its respective API endpoint. Renders items in cards. Todo items have checkbox toggle with optimistic updates. Includes `ScanButton` FAB.

### ProfileScreen (`src/screens/ProfileScreen.tsx`)
User profile display with avatar (initial letter), name, email, phone. Sections:
- **My Caregivers** -- list of connected caregivers with status badges (Active/Pending), relationship type labels, remove button with confirmation. Invite modal using `InviteCaregiverForm`.
- **Settings** -- displays Quiet Hours (9pm-8am), Check-in Time (9:00 AM), Voice (Warm). Currently read-only.
- **Sign Out** button
- **Delete Account** button with confirmation dialog and grace period messaging. Calls `POST /api/v1/me/request-deletion`.
- Version display: "D.D. Companion v1.0.0"

## 8. Theme and Design System

### Colors (`src/theme/colors.ts`)

**Brand colors:**
| Name | Hex | Usage |
|---|---|---|
| `blue` | `#2C5F8A` | Primary action, buttons, active tabs, links |
| `blueMid` | `#3A7BB5` | Mid-tone accent |
| `blueLight` | `#E8F0F8` | Light backgrounds, pill highlights |
| `teal` | `#2A7A6F` | Appointment dots, caregiver avatars |
| `sage` | `#6B8F71` | Secondary accent |
| `cream` | `#FAF7F2` | App background color |
| `rose` | `#D4547A` | Error text, sign-out button |

**Semantic colors:**
| Name | Hex | Usage |
|---|---|---|
| `emerald` | `#059669` | Accepted/active status |
| `amber` | `#D97706` | Pending status |
| `red` | `#DC2626` | Destructive actions |

**Gray scale:** Full range from `gray50` (#F9FAFB) through `gray900` (#111827).

### Brand Constants

```typescript
export const brand = {
  name: 'D.D. Companion',
  short: 'D.D.',
  emoji: '\u{1F31F}',  // star emoji
}
```

### Design Patterns

- **Cards**: White backgrounds, 16px border radius, subtle shadow (`shadowOpacity: 0.05`)
- **Buttons**: Blue fill, 12px border radius, 14px vertical padding, 600 weight text
- **Inputs**: 2px gray border, 12px border radius, 15px font size
- **Section titles**: 13px, 700 weight, uppercase, 0.5 letter spacing, gray500
- **Screen backgrounds**: `colors.cream` throughout
- **No icon library**: All icons are emoji characters

## 9. Native Modules

### DocumentScannerModule

The only custom native module in the app.

**Files:**
- `ios/CompanionApp/DocumentScannerModule.swift` -- Swift implementation using VisionKit
- `ios/CompanionApp/DocumentScannerModule.m` -- Objective-C bridge header

**Bridge interface:**
```objc
@interface RCT_EXTERN_MODULE(DocumentScannerModule, NSObject)
RCT_EXTERN_METHOD(scanDocument:
                  (RCTPromiseResolveBlock)resolve
                  rejecter:(RCTPromiseRejectBlock)reject)
@end
```

**Error codes:**
- `UNSUPPORTED` -- device does not support VNDocumentCameraViewController
- `NO_ROOT_VC` -- unable to find root view controller for modal presentation
- `CANCELLED` -- user cancelled the scan (handled silently in JS)
- `SCAN_FAILED` -- VisionKit scanner encountered an error

**Image processing:**
- Max dimension: 2048px (maintains aspect ratio)
- Format: JPEG at 0.8 quality
- Storage: NSTemporaryDirectory with UUID filenames

## 10. Build and Deployment

### Xcode Configuration

| Setting | Value |
|---|---|
| Bundle Identifier | `com.mydailydignity.companion` |
| Marketing Version | 1.0 |
| Current Project Version | 1 |
| iOS Deployment Target | 15.1 |
| Targeted Device Family | 1,2 (iPhone + iPad) |
| Xcode Version | 26.3 (per scheme `LastUpgradeVersion`) |
| Architecture | arm64 required |

### Orientation

- **iPhone**: Portrait only
- **iPad**: All orientations

### Permissions (Info.plist)

| Key | Description |
|---|---|
| `NSCameraUsageDescription` | "D.D. Companion needs camera access to scan documents and mail" |
| `NSPhotoLibraryUsageDescription` | "D.D. Companion needs photo library access to select documents" |
| `NSLocationWhenInUseUsageDescription` | "D.D. Companion uses your location to help caregivers find nearby services" |

### App Transport Security

- `NSAllowsArbitraryLoads`: false (secure by default)
- `NSAllowsLocalNetworking`: true (for Metro bundler in development)

### Firebase Configuration

From `GoogleService-Info.plist`:
- **Project ID**: `companion-staging-491606`
- **GCM Sender ID**: `381910341082`
- **Storage Bucket**: `companion-staging-491606.firebasestorage.app`
- **Google Sign-In enabled**: yes
- **GCM enabled**: yes
- **Analytics enabled**: no
- **Ads enabled**: no

### Build Commands

```bash
# Start Metro bundler
cd companion-app && npm start

# Run on iOS simulator
cd companion-app && npm run ios

# Run on Android
cd companion-app && npm run android

# Run tests
cd companion-app && npm test

# Install iOS pods (required after dependency changes)
cd companion-app/ios && pod install
```

### Bundle URL Resolution (AppDelegate.swift)

- **Debug**: Metro bundler via `RCTBundleURLProvider.sharedSettings().jsBundleURL(forBundleRoot: "index")`
- **Release**: Pre-bundled `main.jsbundle` from app bundle

### File Structure

```
companion-app/
  App.tsx                          # Root component
  index.js                         # Entry point + FCM background handler
  app.json                         # App name config
  package.json                     # Dependencies
  tsconfig.json                    # TypeScript config (extends @react-native)
  babel.config.js
  metro.config.js
  jest.config.js
  src/
    api/
      client.ts                    # API client with Firebase auth headers
    auth/
      AuthProvider.tsx             # Firebase Auth context provider
      LoginScreen.tsx              # Login/register screen
      OnboardingScreen.tsx         # Post-signup profile + caregiver invite
      VerifyEmailScreen.tsx        # Email verification (not active)
    components/
      InviteCaregiverForm.tsx      # Caregiver invitation form
      ScanButton.tsx               # FAB for document scanning/upload
      TodoCheckbox.tsx             # Reusable checkbox component
    hooks/
      useImageAnalysis.ts          # Image quality analysis hook
      usePushNotifications.ts      # FCM permission, token, foreground handler
    navigation/
      AppNavigator.tsx             # Auth gate + tab navigator
    notifications/
      backgroundHandler.ts         # FCM background message handler
    screens/
      TodayScreen.tsx              # Home dashboard
      ChatScreen.tsx               # Conversational AI interface
      MyStuffScreen.tsx            # Tabbed data browser
      ProfileScreen.tsx            # User profile + caregivers + settings
    theme/
      colors.ts                    # Color palette + brand constants
  ios/
    CompanionApp/
      AppDelegate.swift            # Firebase init, APNS, React Native factory
      DocumentScannerModule.swift  # VisionKit document scanner
      DocumentScannerModule.m      # Obj-C bridge for scanner module
      Info.plist                   # Permissions, URL schemes, capabilities
      GoogleService-Info.plist     # Firebase project config
    CompanionApp.xcodeproj/        # Xcode project
```
