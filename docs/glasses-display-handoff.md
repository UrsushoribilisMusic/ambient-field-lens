# Glasses display handoff — mock validation (no glasses hardware)

Same iPhone binary is the glasses host. No separate glasses binary.
Mock path uses a display-capable mock (`.metaRayBanDisplay`).

> Simulator limit (verified 2026-11-02): `Wearables.configure()` throws
> on the iOS Simulator (no Bluetooth transport) and any access to
> `Wearables.shared` traps. The app now degrades gracefully there —
> phone-camera Ask works, glasses features report "unavailable". Mock
> validation below needs a physical iPhone (no glasses needed); the
> Simulator build only proves compilation.

## Manual validation (5 min, physical iPhone, no glasses)

1. Launch → Setup opens automatically on first run: `enableMock()` pairs
   the mock, `startSession()` creates + starts the session.
   Fallback (Setup sheet): Mock glasses → Start session.
2. Camera input: Start glasses preview. Toggle Phone/Glass in the ask bar.
   Glass viewfinder shows `currentFrame`; "No glasses frame" means the
   session or stream is not up.
3. Device state: mock is already powered + unfolded + donned with the
   phone camera as feed. Folding/doffing is hardware-only (see below).
4. Display: Setup → Attach display → Ask → Glasses button on the quote
   card (or Setup → Send current answer to glasses). The card sent is
   `AmberDisplayCard`: heading + query + first 140 chars of the amber
   detail + "Amber only — evidence on phone." Mock preview renders in
   Setup. Each send replaces the previous glasses content.
5. Teardown order (session-lifecycle): stop camera preview, stop display,
   then stop the session. `endSession()` does this. Never restart while
   paused — wait for `started` or `stopped`.

## What this proves

Pairing, session start, camera stream, display attach/send, and teardown
all run against the mock with the same `DeviceSession.addDisplay()` API
used on hardware. The phone UI shows WORLD/COV chips; the glasses show
only the amber quotation.

## Hardware-only (cannot validate on mock)

- Real registration via Meta AI app + `Wearables.shared.startRegistration()`.
- `META_APP_ID` / Client Token attestation (mock runs in Developer Mode).
- Bluetooth Classic / Wi-Fi link leases, thermal/battery session interrupts.
- `don/doff/fold` sensor transitions and pause/resume on real hinges.
- On-glass legibility, tap handling (`sendClick` only simulates taps).
- Camera permission prompt on the companion phone (`MockPermissions` only
  simulates grant/deny).
