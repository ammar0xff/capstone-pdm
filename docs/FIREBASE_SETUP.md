# Firebase setup — current configuration and audit

This document records the Firebase setup that exists in the repository and on
the Pi. It does not invent credentials and it does not silently change auth.

## 1. Current configuration

| Item | Value |
|---|---|
| Firebase project | `castpone2026` (`.firebaserc`) |
| Hosting site | `castpone2026` (`firebase.json`) |
| Hosting public directory | `public/` |
| RTDB mirror URL | `https://castpone2026-default-rtdb.firebaseio.com/motor1.json` |
| Mirror writer | `edge/firebase_mirror.py` via HTTPS `PUT` |
| Pi service | `pdm-cloud.service` |
| Config file | `edge/cloud_config.json` |
| Sync interval | 5.0 s configured in `cloud_config.json` |
| Daily write cap | 15,000 configured guard |
| Offline queue | `edge/cloud_backlog.json` |

The mirror writes only the latest state packet. It is not a time-series
database and the hosted dashboard is a presentation client, not an engineering
control surface.

## 2. Recreate the setup

1. Create or select the Firebase project `castpone2026`.
2. Create Realtime Database in the project; the URL above must match
   `edge/cloud_config.json` and the dashboard's `FIREBASE_RTDB_URL`.
3. Keep the database path `motor1`. Do not rename it without updating both
   `edge/cloud_config.json` and `public/index.html`.
4. Confirm the Pi service:

```bash
sudo systemctl status pdm-cloud.service
journalctl -u pdm-cloud.service -n 50 --no-pager
cat ~/pdm/edge/cloud_config.json
```

5. Deploy the presentation site:

```bash
firebase login
firebase use castpone2026
firebase deploy --only hosting
```

6. Verify `https://castpone2026.web.app/` and
   `https://castpone2026-default-rtdb.firebaseio.com/motor1.json`.

## 3. Security reality — read before changing rules

The tutorial and the current deployment use public Realtime Database rules:

```json
{
  "rules": {
    ".read": true,
    ".write": true
  }
}
```

This means **anyone with the URL can read or overwrite `motor1`**. It was kept
for zero-cost exhibition telemetry, but it is not acceptable for a deployed
industrial system. No auth change was made during this cleanup because it would
change client behavior and needs an explicit decision.

Recommended next step, requiring approval:

1. Enable Firebase Authentication with a named operator account or anonymous
   auth plus device-level rules.
2. Replace the rules with least-privilege access, for example authenticated
   read for the dashboard and write restricted to the Pi's uid/path.
3. Add an RTDB security-rules test that denies unauthenticated write.
4. Update `edge/firebase_mirror.py` with an ID token source read from the
   environment; never commit a token.
5. Verify both the Pi writer and hosted dashboard after the rule change.

`[NEED: decision on Firebase auth model and operator identities]`.

## 4. Secrets policy

- No API keys, tokens or passwords are stored in this repository.
- `.firebase/` is a local Firebase CLI cache and is ignored by git.
- Tokens must come from environment variables or a Pi-local credentials file
  outside the repo if auth is enabled.
- Before committing: `git diff --staged | grep -iE "secret|password|api[_-]?key|token"`.

## 5. Verification checklist

- [ ] `cloud_config.json` URL matches the Firebase console.
- [ ] `pdm-cloud.service` is active and journal shows successful PUTs.
- [ ] `cloud_backlog.json` empties after connectivity returns.
- [ ] Hosting serves `index.html`, `guide.html` and `calibration.html`.
- [ ] Rule change, if any, has a passing deny-write test and Pi writer test.
