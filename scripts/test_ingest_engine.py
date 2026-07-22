"""End-to-end test: Reconstruct event from DB, export to engine PredictRequests, POST live."""
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone

# --- Add src to path so we can import the exporter ---
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.sites.betb2b.export.scorewise import event_to_predict_requests, build_ingest_matches, post_ingest

# ── Config ──────────────────────────────────────────────────────────────────
EVENT_ID = "737904396"            # LA Sparks vs Phoenix Mercury
SKIN = "linebet"
DB_PATH = "data/betb2b/odds.db"
ENGINE_URL = os.environ.get("SCOREWISE_ENGINE_URL", "https://scorewise-engine.up.railway.app")
API_KEY = os.environ.get("SCOREWISE_API_KEY", "")
DRY_RUN = "--dry-run" in sys.argv   # just print, don't POST

# ── 1. Read event from DB ──────────────────────────────────────────────────
import sqlite3

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# Event
c.execute("""
    SELECT e.event_id, e.home_name, e.away_name, e.sport_id,
           l.name AS league_name, s.name AS sport_name
    FROM events e
    LEFT JOIN leagues l ON e.league_id = l.league_id
    LEFT JOIN sports s ON e.sport_id = s.sport_id
    WHERE e.event_id = ?
""", (EVENT_ID,))
ev = c.fetchone()
if not ev:
    print(f"Event {EVENT_ID} not found in DB!")
    sys.exit(1)

eid, home, away, sport_id, league_name, sport_name = ev
print(f"Event: {home} vs {away}  ({league_name})")

# ── 2. Reconstruct markets from odds_snapshots ──────────────────────────────

# Group: (market_name, scope) → list of selection dicts
# We need to merge odds_snapshots rows into market dicts
c.execute("""
    SELECT m.name AS market_name, os.scope,
           os.selection_name, os.line, os.price, os.raw_t
    FROM odds_snapshots os
    JOIN markets m ON os.market_id = m.market_id
    WHERE os.event_id = ? AND os.run_id = (
        SELECT MAX(run_id) FROM odds_snapshots WHERE event_id = ?
    )
    ORDER BY os.scope, m.name, os.line
""", (EVENT_ID, EVENT_ID))
rows = c.fetchall()
print(f"Odds rows: {len(rows)}")

# Build market dicts
markets_by_key = {}  # (market_name, scope) -> market dict
for r in rows:
    mname, scope, sel_name, line, price, raw_t = r
    key = (mname, scope)
    if key not in markets_by_key:
        markets_by_key[key] = {
            "name": mname,
            "scope": scope or "FULL_MATCH",
            "selections": [],
        }
    markets_by_key[key]["selections"].append({
        "name": sel_name,
        "price": price,
        "line": line,
    })

markets = list(markets_by_key.values())
print(f"Reconstructed {len(markets)} market groups")

# Show what total markets we have (the ones the exporter needs)
for m in markets:
    if "total" in m["name"].lower():
        lines = [s["line"] for s in m["selections"] if s["line"] is not None]
        print(f"  {m['name']} [{m['scope']}]: {len(m['selections'])} sels, lines={lines[:3]}...")

# ── 3. Reconstruct H2H data ────────────────────────────────────────────────

# Teams mapping from DB
c.execute("""
    SELECT DISTINCT t.backend_id, t.name
    FROM teams t
    WHERE t.sport_id = ? OR t.team_id IN (
        SELECT home_team_id FROM events WHERE event_id = ?
        UNION
        SELECT away_team_id FROM events WHERE event_id = ?
    )
""", (sport_id, EVENT_ID, EVENT_ID))
teams_list = [{"id": r[0], "title": r[1]} for r in c.fetchall()]
print(f"Teams in mapping: {len(teams_list)}")

# H2H games with periods
c.execute("""
    SELECT h.id, h.game_id, h.team1_backend_id, h.team2_backend_id,
           h.date_start, h.score1, h.score2, h.winner, h.status
    FROM h2h_games h
    WHERE h.event_id = ? AND h.run_id = (
        SELECT MAX(run_id) FROM h2h_games WHERE event_id = ?
    )
    ORDER BY h.date_start DESC
""", (EVENT_ID, EVENT_ID))
h2h_rows = c.fetchall()
print(f"H2H games: {len(h2h_rows)}")

game_shorts = []
for hr in h2h_rows:
    h_id, game_id, t1_id, t2_id, date_start, s1, s2, winner, status = hr
    
    # Get periods for this game
    c.execute("""
        SELECT period_key, home_score, away_score
        FROM h2h_period_scores
        WHERE h2h_game_id = ?
        ORDER BY period_key
    """, (h_id,))
    periods = [{"period_key": p[0], "home_score": p[1], "away_score": p[2]} for p in c.fetchall()]
    
    game_shorts.append({
        "game_id": game_id,
        "team1_id": t1_id,
        "team2_id": t2_id,
        "date_start": date_start[:10] if date_start else None,
        "score1": s1,
        "score2": s2,
        "winner": winner,
        "status": status,
        "periods": periods,
    })

h2h_data = {
    "teams": teams_list,
    "game_shorts": game_shorts,
    "sport_id": sport_id,
}

# ── 4. Build the event dict ────────────────────────────────────────────────

event_dict = {
    "event_id": eid,
    "sport": sport_name or "Basketball",
    "competition": league_name or "",
    "home": home,
    "away": away,
    "status": "not_started",
    "markets": markets,
    "h2h_data": h2h_data,
}

# ── 5. Run through the exporter ────────────────────────────────────────────

predict_requests = event_to_predict_requests(event_dict)
print(f"\nPredict requests generated: {len(predict_requests)}")
for pr in predict_requests:
    odds = pr.get("odds", {})
    h2h_count = len(pr.get("h2h_matches", []))
    print(f"  scope={pr['scope']:<15} total={odds.get('match_total', 'N/A'):>8}  "
          f"over={odds.get('over_odds', 'N/A')}  "
          f"h2h={h2h_count} matches")

all_matches = build_ingest_matches([event_dict])
print(f"\nTotal ingest matches: {len(all_matches)}")

# ── 6. POST to engine ──────────────────────────────────────────────────────

if DRY_RUN:
    print(f"\n--- DRY RUN — skipping POST ---")
    print(f"Would POST to: {ENGINE_URL}/api/ingest")
    print(f"First match payload:")
    if all_matches:
        print(json.dumps(all_matches[0], indent=2, default=str)[:500])
else:
    import asyncio
    import httpx

    async def do_post():
        source = f"betb2b-scraper-test-{SKIN}"
        scraped_at = datetime.now(timezone.utc).isoformat()
        print(f"\n--- POSTING to {ENGINE_URL}/api/ingest ---")
        url = f"{ENGINE_URL.rstrip('/')}/api/ingest"
        headers = {"x-api-key": API_KEY} if API_KEY else {}
        payload = {"source": source, "scraped_at": scraped_at, "matches": all_matches}
        async with httpx.AsyncClient(timeout=45.0) as c:
            r = await c.post(url, json=payload, headers=headers)
            body = r.json()
            print(f"  status={r.status_code}")
            if isinstance(body, dict):
                print(f"  total={body.get('total')} succeeded={body.get('succeeded')} "
                      f"failed={body.get('failed')} added={body.get('added')} "
                      f"updated={body.get('updated')} store_total={body.get('store_total')}")
                for res in body.get('results', []):
                    print(f"    -> match_id={res.get('match_id')} "
                          f"scope={str(res.get('scope','')):>20} "
                          f"success={res.get('success')} "
                          f"rec={str(res.get('recommendation','?')):>6} "
                          f"line={res.get('bookmaker_line','?')}")
            return body

    asyncio.run(do_post())

conn.close()
