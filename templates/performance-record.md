<!-- Copy into evidence/ per intervention. Record median + range, and count failures. -->
# Performance record

Protocol (research doc §3.2): same remote, source, network and test order.
Note whether the TV was freshly restarted or had been on for hours.
A phone recording of remote-press → screen response is adequate. Report the
**median and range**, not a 95th percentile from a handful of trials. An app
that fails to load is a FAILURE, not a fast response.

| State | Operation | Trials | Median | Range | Failures | Notes |
|---|---|---:|---|---|---:|---|
| Baseline | Open Settings (warm) | | | | | |
| Baseline | Change volume (warm) | | | | | |
| Baseline | Open Home (warm) | | | | | |
| Baseline | Switch HDMI source | | | | | |
| Baseline | Launch problem app (cold) | | | | | |
| Baseline | Launch problem app (warm) | | | | | |
| Cold restart | Open Home | | | | | |
| TV offline | Open Home | | | | | |
| After 1 change | (relevant op) | | | | | |
| Restored baseline (A-B-A) | (same op) | | | | | |

**Interpretation (§3.4):** if only Home/streaming is slow → focus on app data,
network dependency, bypassing Smart Hub. If Settings/volume/HDMI are also slow →
deletion likely won't fix it; simplify the config and diagnose further before
any destructive change.
