# Scrapamoja — New Features Backlog
> Discovered during AiScore/ScoreWise integration sprint, March 2026.
> Each feature is independent and can be built and merged separately.

---

## Feature 1: Direct API Mode
**Summary:** Allow Scrapamoja to make direct HTTP calls to known API endpoints without launching a browser at all.  
**Trigger:** Attempting to call `api.aiscore.com` directly with `httpx`.  
**Value:** Fastest possible data retrieval when no bot protection exists.

---

## Feature 2: Network Response Interception
**Summary:** While a Playwright browser navigates a page, listen to all network traffic and capture API responses mid-flight — before they reach the DOM.  
**Trigger:** Discovering that AiScore's data never appears in the HTML — it lives in XHR responses.  
**Value:** Extracts clean structured data from SPAs without fragile DOM selectors.

---

## Feature 3: Cloudflare-Protected SPA Support
**Summary:** Enable Scrapamoja to successfully access sites protected by Cloudflare bot detection by using a real Playwright browser to satisfy the challenge automatically.  
**Trigger:** Getting a 403 block on every direct HTTP attempt to AiScore.  
**Value:** Unlocks the majority of modern sports, betting, and financial data platforms.

---

## Feature 4: Auto Encoding Detection
**Summary:** Automatically detect the encoding of a captured API response — whether it is JSON, gzip-compressed, Brotli, protobuf binary, or plain text — and route it to the correct decoder without manual configuration.  
**Trigger:** Response claiming to be `gzip` but failing all standard decompression attempts.  
**Value:** Site modules no longer need to hardcode encoding handling — the engine figures it out.

---

## Feature 5: Protobuf Binary Decoding
**Summary:** Decode Protocol Buffer (protobuf) binary responses from API endpoints into readable, structured Python data.  
**Trigger:** Discovering that `api.aiscore.com` returns `application/octet-stream` protobuf data, not JSON.  
**Value:** Unlocks data from Google-backed and enterprise platforms that use protobuf instead of JSON.

---

## Feature 6: Session Harvesting
**Summary:** After a Playwright browser establishes a valid session on a protected site, extract the resulting cookies, tokens, and headers and package them for reuse in direct HTTP calls — so the browser only needs to run once.  
**Trigger:** Realising that launching a full browser for every data request is slow and unnecessary once the session is established.  
**Value:** Dramatically improves performance for high-frequency polling use cases like ScoreWise.

---

## Feature 7: Hybrid Mode (Browser → Direct HTTP)
**Summary:** A combined extraction mode where the browser is used once to unlock access and harvest session credentials, then all subsequent data requests are made directly via lightweight HTTP — no browser involved.  
**Trigger:** The full AiScore flow: browser needed for Cloudflare, but direct HTTP preferred for speed once unlocked.  
**Value:** Best of both worlds — security bypass capability with direct API performance.

---

## Feature 8: AiScore Site Module
**Summary:** A fully working Scrapamoja site module for `m.aiscore.com` that extracts upcoming basketball fixtures, leagues, team names, match IDs, and odds markets including Total Points (Over/Under) lines — using the Hybrid Engine.  
**Trigger:** The ScoreWise basketball prediction algorithm needing structured odds data.  
**Value:** First real-world proof of the Hybrid Engine; delivers the ScoreWise data pipeline.

---

*Each feature above maps to a separate branch, PR, and milestone in the Scrapamoja repo.*
