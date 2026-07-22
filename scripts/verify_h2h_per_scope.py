"""Match-by-match H2H breakdown per scope — verify the engine's predictions."""
import json, os, sqlite3
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.sites.betb2b.export.scorewise import event_to_predict_requests, _h2h_for_scope, _nearest_185_total

DB_PATH = "data/betb2b/odds.db"
EVENT_ID = "737904396"

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# ── 1. Event info ──
c.execute("SELECT e.home_name, e.away_name, e.sport_id, l.name FROM events e JOIN leagues l ON e.league_id = l.league_id WHERE e.event_id = ?", (EVENT_ID,))
home, away, sport_id, league = c.fetchone()

# ── 2. Markets ──
c.execute("""
    SELECT m.name AS market_name, os.scope,
           os.selection_name, os.line, os.price
    FROM odds_snapshots os
    JOIN markets m ON os.market_id = m.market_id
    WHERE os.event_id = ? AND os.run_id = (
        SELECT MAX(run_id) FROM odds_snapshots WHERE event_id = ?
    )
    ORDER BY os.scope, m.name, os.line
""", (EVENT_ID, EVENT_ID))
rows = c.fetchall()

markets_by_key = {}
for r in rows:
    mname, scope, sel_name, line, price = r
    key = (mname, scope)
    if key not in markets_by_key:
        markets_by_key[key] = {"name": mname, "scope": scope or "FULL_MATCH", "selections": []}
    markets_by_key[key]["selections"].append({"name": sel_name, "price": price, "line": line})
markets = list(markets_by_key.values())

# ── 3. H2H ──
c.execute("SELECT t.backend_id, t.name FROM teams t WHERE t.sport_id = ? OR t.team_id IN (SELECT home_team_id FROM events WHERE event_id = ? UNION SELECT away_team_id FROM events WHERE event_id = ?)", (sport_id, EVENT_ID, EVENT_ID))
teams_list = [{"id": r[0], "title": r[1]} for r in c.fetchall()]

c.execute("""
    SELECT h.id, h.game_id, h.team1_backend_id, h.team2_backend_id,
           h.date_start, h.score1, h.score2, h.winner, h.status
    FROM h2h_games h
    WHERE h.event_id = ? AND h.run_id = (SELECT MAX(run_id) FROM h2h_games WHERE event_id = ?)
    ORDER BY h.date_start DESC
""", (EVENT_ID, EVENT_ID))
h2h_rows = c.fetchall()

game_shorts = []
for hr in h2h_rows:
    h_id, game_id, t1_id, t2_id, date_start, s1, s2, winner, status = hr
    c.execute("SELECT period_key, home_score, away_score FROM h2h_period_scores WHERE h2h_game_id = ? ORDER BY period_key", (h_id,))
    periods = [{"period_key": p[0], "home_score": p[1], "away_score": p[2]} for p in c.fetchall()]
    game_shorts.append({
        "game_id": game_id, "team1_id": t1_id, "team2_id": t2_id,
        "date_start": date_start[:10] if date_start else None,
        "score1": s1, "score2": s2, "winner": winner, "status": status,
        "periods": periods,
    })

h2h_data = {"teams": teams_list, "game_shorts": game_shorts, "sport_id": sport_id}

event_dict = {
    "event_id": EVENT_ID, "sport": "Basketball", "competition": league or "",
    "home": home, "away": away, "status": "not_started",
    "markets": markets, "h2h_data": h2h_data,
}

conn.close()

# ── 4. Team name mapping ──
names = {str(t["id"]): t["title"] for t in teams_list}
hset = {home.strip().lower(), away.strip().lower()}

def show_paired_h2h(scope, totals_name):
    """Show ONLY the 6 H2H games that go to the engine for this scope."""
    h2h_list = _h2h_for_scope(event_dict, scope, home, away)
    total_line = _nearest_185_total(markets, scope, totals_name) if totals_name else _nearest_185_total(markets, scope)

    line_val = total_line["match_total"] if total_line else None
    line = f"{line_val}" if line_val is not None else "N/A"
    over_price = total_line.get("over_odds", "N/A") if total_line else "N/A"
    
    print(f"\n{'='*70}")
    print(f"  {scope}")
    print(f"  Line: {line} @ {over_price}")
    print(f"  H2H matches used: {len(h2h_list)}")
    print(f"{'='*70}")
    
    total_scores = []
    for i, m in enumerate(h2h_list, 1):
        hs, as_ = m["home_score"], m["away_score"]
        engine_total = hs + as_  # s02 always sums — after fix, one side is 0 for team totals
        total_scores.append(engine_total)
        
        date = m.get("date", "")
        line_ok = line_val is not None
        print(f"  {i}. {date}  {m['home_team'][:25]:>25} {hs:>3} - {as_:<3} {m['away_team'][:25]:<25}  ", end="")
        if scope == "FULL_MATCH":
            above = engine_total > line_val if line_ok else None
            print(f"tot={engine_total:>3}  {'⬆ OVER' if above else '⬇ UNDER' if above is False else '?'}  (vs {line})")
        elif scope == "HOME_TEAM_TOTAL":
            above = engine_total > line_val if line_ok else None  # engine_total = home_score + 0
            print(f"home={hs:>3}  eng={engine_total:>3}  {'⬆ OVER' if above else '⬇ UNDER' if above is False else '?'}  (vs {line})")
        elif scope == "AWAY_TEAM_TOTAL":
            above = engine_total > line_val if line_ok else None  # engine_total = 0 + away_score
            print(f"away={as_:>3}  eng={engine_total:>3}  {'⬆ OVER' if above else '⬇ UNDER' if above is False else '?'}  (vs {line})")
    
    if total_scores:
        above_count = sum(1 for s in total_scores if line_val is not None and s > line_val)
        below_count = sum(1 for s in total_scores if line_val is not None and s < line_val)
        at_count = len(total_scores) - above_count - below_count
        avg = sum(total_scores) / len(total_scores)
        print(f"\n  ═ Summary: {above_count} above, {below_count} below, {at_count} at line")
        print(f"  ═ Avg engine_total: {avg:.1f} vs line {line}")

# Debug: why are individual totals not matching?
print("\n\n=== DEBUG: Available markets ===")
for m in markets:
    print(f"  market='{m['name']}' scope='{m['scope']}' selections={len(m['selections'])}")
    for s in m['selections'][:3]:
        print(f"    sel={s['name']} line={s['line']} price={s['price']}")

# ── FULL_MATCH ──
show_paired_h2h("FULL_MATCH", "Total")

# ── HOME_TEAM_TOTAL — individual totals use scope FULL_MATCH ──
print("\n\n=== HOME_TEAM_TOTAL ===")
home_line = _nearest_185_total(markets, "FULL_MATCH", "Individual Total Home")
print(f"  Lookup result: {home_line}")
h2h_home = _h2h_for_scope(event_dict, "HOME_TEAM_TOTAL", home, away)
print(f"  H2H games: {len(h2h_home)}")
for m in h2h_home:
    eng_total = m['home_score'] + m['away_score']  # engine sum = home_score + 0
    print(f"  {m['date']}  {m['home_team'][:25]} {m['home_score']} - {m['away_score']} {m['away_team'][:25]}  home={m['home_score']}  eng={eng_total}  {'⬆ OVER' if home_line and eng_total > home_line['match_total'] else '⬇ UNDER' if home_line else '?'}")

# ── AWAY_TEAM_TOTAL ──
print("\n=== AWAY_TEAM_TOTAL ===")
away_line = _nearest_185_total(markets, "FULL_MATCH", "Individual Total Away")
print(f"  Lookup result: {away_line}")
h2h_away = _h2h_for_scope(event_dict, "AWAY_TEAM_TOTAL", home, away)
print(f"  H2H games: {len(h2h_away)}")
for m in h2h_away:
    eng_total = m['home_score'] + m['away_score']  # engine sum = 0 + away_score
    print(f"  {m['date']}  {m['home_team'][:25]} {m['home_score']} - {m['away_score']} {m['away_team'][:25]}  away={m['away_score']}  eng={eng_total}  {'⬆ OVER' if away_line and eng_total > away_line['match_total'] else '⬇ UNDER' if away_line else '?'}")
