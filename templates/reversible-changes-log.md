<!-- Copy into evidence/. One row per change, so any change can be undone. -->
# Reversible-changes log (ordinary menus)

Rule: one change at a time, retest, record the way back BEFORE proceeding
(§12.2). Never bundle ten interventions into one "optimization".

| Date | Change (menu path) | Previous value | New value | Rollback path | Retested? | Effect observed |
|---|---|---|---|---|---|---|
| | Cold restart (unplug ~1 min) | n/a | n/a | n/a — non-erasing | | |
| | Smart Hub auto-start OFF | | | same menu | | |
| | Auto-start last app OFF | | | same menu | | |
| | Cache cleared: <app> | n/a | n/a | regenerates (not restore) | | |
| | App data cleared: <app> | logged in | logged out | re-login: <how> | | |
| | Removed optional app: <name> | installed | removed | reinstall: <verified?> | | |

**Menu paths (German, from the photos):**
- Storage: Einstellungen → Unterstützung → Gerätepflege → Speicher verwalten
- Remove app: Home → Apps → Einstellungen → <app> → Löschen
- Smart Hub startup: Einstellungen → Allgemein → Smart-Funktionen
- Smart Hub reset: Unterstützung → Eigendiagnose → Smart Hub zurücksetzen (PIN, default 0000)
