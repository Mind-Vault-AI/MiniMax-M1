# VAULT TV Feed Checking Guide

This guide explains how to verify the latest **VAULT TV** release for the Mind-Vault-AI shop. The goal is to make sure the most recent drop reflects the brand identity for **CraveChain — "Your World of Cravings, Delivered on the Chain."**

## 1. Prepare the feed data

1. Copy `data/vault_tv_feed.sample.json` to `data/vault_tv_feed.json` when you're ready to go live. (The checker will fall back to the sample file if the production feed doesn't exist yet.)
2. Replace the sample entries with your real VAULT TV release metadata. Each entry should be a JSON object containing at least:
   - `title`: Human readable release title (for example, *"CraveChain Vault TV // Global Launch"*).
   - `date`: ISO 8601 timestamp (e.g. `2025-03-18T19:30:00+00:00`).
   - Optional additional fields such as `host`, `theme`, or `link`.

Keep the file encoded in UTF-8 and ensure the entire payload is a JSON array.

## 2. Run the checker utility

Use the helper script to report the most recent entry:

```bash
python tools/check_vault_tv.py
```

You can point to a different feed file if required:

```bash
python tools/check_vault_tv.py --feed /path/to/custom_feed.json
```

To keep the drops fresh, add the optional `--stale-after` flag to raise a warning when the newest release is older than the number of days you specify. The checker now also displays how long it has been since the release date so you can evaluate freshness at a glance:

```bash
python tools/check_vault_tv.py --stale-after 14
```

If the report should cause automations to fail when the release is stale, include `--fail-on-stale` alongside the threshold:

```bash
python tools/check_vault_tv.py --stale-after 14 --fail-on-stale
```

The command prints a summary similar to:

```
Latest VAULT TV release detected:
  Title: CraveChain Vault TV // Global Launch
  Date:  2025-03-18T19:30:00+00:00
  Age:   18d 4h (as of 2025-04-05T23:30:00+00:00)
  Additional metadata:
    host: Mind-Vault-AI
    link: https://example.com/vault-tv/launch
Total releases in feed: 12
⚠️  Latest release is older than the configured staleness window (18 days > 14 days).
```

If the feed is missing or malformed, the script reports a detailed error so you can correct the data quickly.

## 3. Operational checklist

- Ensure the most recent VAULT TV entry aligns with CraveChain's visual and tonal guidelines (modern, trustworthy, globally-minded).
- Confirm the associated assets (stream links, cover art, promotional copy) reference the minimalist `C` logo concept and the slogan *"Your World of Cravings, Delivered on the Chain."*
- Update the shop front and any partner integrations once the latest VAULT TV date is verified.

## 4. Lean assurance loop

Apply a rapid continuous-improvement lens so the feed never drifts from expectations:

- **PDCA (Plan-Do-Check-Act):** Plan the next VAULT TV release update, publish the metadata, run the checker to verify freshness, then act on the findings (for example, promote or refresh content).
- **Poka-Yoke (error-proofing):** Use the `--fail-on-stale` flag in CI or scheduled jobs so outdated drops are caught automatically before they reach the audience.
- **Six Sigma mindset:** Track the age output to keep variation in release cadence within the tolerance your team sets.
- **1W5H review:** For every release confirm the *what, why, who, where, when,* and *how* metadata fields inside the feed to avoid missing contextual details.

Maintaining an accurate feed allows the Mind-Vault-AI shop to surface the correct VAULT TV experience to the community while reinforcing CraveChain's promise of reliable, on-chain delivery.
