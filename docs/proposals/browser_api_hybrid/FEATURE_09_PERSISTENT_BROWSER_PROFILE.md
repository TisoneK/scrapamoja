# Feature Proposal: Persistent Browser Profile
**Project:** Scrapamoja  
**Feature ID:** SCR-009  
**Status:** Proposed  
**Author:** TisoneK  
**Date:** March 2026  

---

## 1. Summary

Add support for a persistent browser profile in Scrapamoja — one that retains cookies, session tokens, login state, cached data, and browser fingerprint across multiple runs, exactly as a real user's browser does. Instead of starting every session from scratch in an isolated, incognito-like context, Scrapamoja would maintain a living browser profile on disk that accumulates trust and history over time.

---

## 2. Problem

Playwright, by default, launches browsers in a clean, isolated context. Every session starts with:

- No cookies
- No cached data
- No login state
- No browsing history
- A fresh, unseen browser fingerprint

This is intentional for test isolation, but it is a significant disadvantage for scraping. From a bot detection perspective, a browser that arrives with zero history, zero cookies, and a brand new fingerprint on every visit looks exactly like what it is — an automated tool, not a real user.

Real browsers accumulate trust signals over time:

- Cookies that persist across visits
- A fingerprint that sites have seen before
- Login sessions that do not expire between runs
- Cached assets that reduce cold-start behaviour
- A browsing history that makes traffic patterns look organic

When Scrapamoja visits a protected site in a fresh context, it is presenting itself as a first-time visitor with no history — the highest-suspicion profile possible. Even when Cloudflare is bypassed in the moment, more sophisticated bot detection systems track fingerprint consistency over time and will eventually flag a fingerprint that appears, disappears, and reappears as a clean slate on every visit.

Additionally, for sites that require login — members-only data, subscription sports platforms, authenticated betting APIs — there is currently no way to maintain a logged-in state between Scrapamoja runs. Every session would require re-logging in, which often triggers additional security checks.

---

## 3. Opportunity

Playwright supports **persistent browser contexts** — a mode where the browser profile is stored in a directory on disk and reused across sessions. This means cookies, local storage, session tokens, and cached data all survive between Scrapamoja runs, exactly as they would in a real browser.

Combined with careful fingerprint consistency — using the same user agent, screen resolution, timezone, and language settings on every run — a persistent profile builds a genuine browsing history that makes Scrapamoja look like a returning human user rather than a new bot on every visit.

Over time, a persistent profile:

- Accumulates trusted cookies that are increasingly difficult to invalidate
- Builds a fingerprint history that passes time-based bot detection
- Maintains login sessions without re-authentication on every run
- Reduces the frequency of Cloudflare challenges as the profile becomes recognised
- Mirrors the actual behaviour of the human users these platforms are designed for

---

## 4. What This Feature Adds

- **Persistent browser context** — browser profile stored in a configurable directory and reused across all Scrapamoja runs
- **Profile isolation per site** — each target site can have its own profile directory, preventing cross-site cookie contamination
- **Fingerprint locking** — user agent, screen resolution, timezone, language, and other fingerprint signals are fixed per profile and never randomised between sessions
- **Login state preservation** — once a user logs into a site manually or via automation, that login persists until the site expires it naturally
- **Profile warm-up** — an optional initial browsing sequence that builds organic-looking history before the first data extraction
- **Profile health monitoring** — detection of profile invalidation (e.g. when a site logs out the session or resets cookies) with automatic alerts
- **Manual profile seeding** — a mode where a developer can manually browse a site in the Scrapamoja-managed browser to establish a natural history before automated extraction begins
- **Profile backup and restore** — snapshot a known-good profile state and restore it if the profile becomes compromised

---

## 5. Who Benefits

- Any site module targeting a platform with sophisticated, time-based bot detection that tracks fingerprint consistency
- Any use case requiring authenticated access to members-only or subscription-gated data
- Long-running deployments where Scrapamoja operates continuously and needs to look like a consistent returning user
- The AiScore module — a persistent profile would reduce the frequency of Cloudflare challenges over time as the profile builds trust
- Future modules targeting login-gated sports platforms, subscription betting data providers, or authenticated APIs

---

## 6. Discovery Context

This need was identified while analysing the AiScore Cloudflare bypass. While Playwright successfully passes the challenge in a fresh context today, the observation was made that every Scrapamoja run presents a clean-slate browser — which is the highest-risk profile for detection over time.

The question asked was: *"What happens when we need to run this every day, and the site starts noticing that the same data is being accessed by a browser that has no history?"*

The answer is persistent profiles. This is the difference between a scraper that works once and a data extraction tool that works reliably over months and years.

---

## 7. How This Differs from Session Harvesting

Session Harvesting (SCR-006) extracts credentials from a browser session for reuse in direct HTTP calls. It solves a performance problem — avoiding repeated browser launches.

Persistent Browser Profile solves a different problem — **identity consistency**. It ensures that when the browser does launch, it presents a coherent, trusted, history-bearing identity rather than a suspicious blank slate.

The two features are complementary:

- Persistent Profile makes the browser look human over time
- Session Harvesting reduces how often the browser needs to launch at all

---

## 8. Success Criteria

- A browser profile is created on first run and reused on all subsequent runs without manual intervention
- Cookies set during one Scrapamoja run are present and valid on the next run
- A site that was logged into during one run remains logged in on the next run (subject to site-side session expiry)
- The fingerprint (user agent, resolution, timezone) is identical across all runs using the same profile
- Profile isolation ensures cookies from Site A are never sent to Site B
- Profile corruption or invalidation is detected and reported clearly
- A developer can manually browse using the Scrapamoja-managed profile to seed history before automated extraction

---

## 9. Out of Scope

- Automated login to sites requiring username and password (a separate authentication feature)
- Proxy rotation or IP address management (a separate feature)
- Profile sharing across multiple machines or distributed deployments (future consideration)
- CAPTCHA solving for sites that challenge returning visitors (separate problem)

---

*Proposal prepared March 2026.*
