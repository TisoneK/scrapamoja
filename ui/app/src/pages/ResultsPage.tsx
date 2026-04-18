import { useState, useMemo } from "react";

interface ResultRow {
  id: string;
  home_team: string;
  away_team: string;
  score: string;
  status: string;
  stage: string;
  match_url: string;
  scraped_at: string;
}

// Demo data
const DEMO_RESULTS: ResultRow[] = Array.from({ length: 24 }, (_, i) => ({
  id: `row-${i}`,
  home_team: ["Boston Celtics","LA Lakers","Golden State Warriors","Miami Heat","Chicago Bulls","NY Knicks"][i % 6],
  away_team: ["Dallas Mavericks","Phoenix Suns","Denver Nuggets","Milwaukee Bucks","Cleveland Cavaliers","Atlanta Hawks"][i % 6],
  score: `${Math.floor(Math.random()*40)+70}–${Math.floor(Math.random()*40)+70}`,
  status: ["LIVE","FT","SCH"][i % 3],
  stage: ["Q1","Q2","Q3","Q4","FT","—"][i % 6],
  match_url: `https://www.flashscore.com/match/abc${i}`,
  scraped_at: new Date(Date.now() - i * 120000).toISOString(),
}));

type SortKey = keyof ResultRow;

function formatTime(iso: string) {
  return new Date(iso).toLocaleTimeString("en-GB", { hour12:false, hour:"2-digit", minute:"2-digit" });
}

export function ResultsPage() {
  const [search, setSearch] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>("scraped_at");
  const [sortDir, setSortDir] = useState<"asc"|"desc">("desc");
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [exportFmt, setExportFmt] = useState<"json"|"csv">("json");

  const filtered = useMemo(() => {
    const q = search.toLowerCase();
    return DEMO_RESULTS
      .filter(r => !q || r.home_team.toLowerCase().includes(q) || r.away_team.toLowerCase().includes(q))
      .sort((a, b) => {
        const va = a[sortKey], vb = b[sortKey];
        const cmp = va < vb ? -1 : va > vb ? 1 : 0;
        return sortDir === "asc" ? cmp : -cmp;
      });
  }, [search, sortKey, sortDir]);

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) setSortDir(d => d === "asc" ? "desc" : "asc");
    else { setSortKey(key); setSortDir("desc"); }
  };

  const toggleRow = (id: string) => {
    setSelectedIds(prev => {
      const n = new Set(prev);
      n.has(id) ? n.delete(id) : n.add(id);
      return n;
    });
  };

  const toggleAll = () => {
    setSelectedIds(prev => prev.size === filtered.length ? new Set() : new Set(filtered.map(r => r.id)));
  };

  const handleExport = () => {
    const rows = filtered.filter(r => selectedIds.size === 0 || selectedIds.has(r.id));
    let content: string;
    let mime: string;
    let ext: string;
    if (exportFmt === "json") {
      content = JSON.stringify(rows, null, 2);
      mime = "application/json"; ext = "json";
    } else {
      const keys = Object.keys(rows[0] ?? {}) as SortKey[];
      content = [keys.join(","), ...rows.map(r => keys.map(k => `"${r[k]}"`).join(","))].join("\n");
      mime = "text/csv"; ext = "csv";
    }
    const blob = new Blob([content], { type: mime });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `scrapamoja-results.${ext}`;
    a.click();
  };

  const SortIcon = ({ col }: { col: SortKey }) => (
    <span style={{ fontSize:9, marginLeft:4, color: sortKey === col ? "var(--accent)" : "var(--text-3)" }}>
      {sortKey === col ? (sortDir === "asc" ? "↑" : "↓") : "⇅"}
    </span>
  );

  return (
    <div style={{ display:"flex", flexDirection:"column", height:"100%", overflow:"hidden" }}>
      {/* Topbar */}
      <div style={{ height:44, background:"var(--bg-1)", borderBottom:"1px solid var(--border-1)",
        display:"flex", alignItems:"center", padding:"0 16px", gap:12, flexShrink:0 }}>
        <span style={{ fontSize:11, fontWeight:600, color:"var(--text-2)",
          letterSpacing:"0.08em", textTransform:"uppercase" }}>
          Results
        </span>
        <span style={{ fontSize:10, color:"var(--text-3)", fontFamily:"var(--font-mono)" }}>
          {filtered.length} rows · {selectedIds.size > 0 ? `${selectedIds.size} selected` : "all"}
        </span>
        <input value={search} onChange={e => setSearch(e.target.value)}
          placeholder="Filter rows…"
          style={{ background:"var(--bg-3)", border:"1px solid var(--border-1)", borderRadius:6,
            padding:"4px 10px", fontSize:11, color:"var(--text-0)", fontFamily:"var(--font-mono)",
            outline:"none", width:200 }}/>
        <div style={{ marginLeft:"auto", display:"flex", gap:8, alignItems:"center" }}>
          <select value={exportFmt} onChange={e => setExportFmt(e.target.value as any)}
            style={{ background:"var(--bg-3)", border:"1px solid var(--border-1)", borderRadius:6,
              padding:"4px 8px", fontSize:11, color:"var(--text-1)", outline:"none" }}>
            <option value="json">JSON</option>
            <option value="csv">CSV</option>
          </select>
          <button className="btn btn-primary btn-sm" onClick={handleExport}>
            Export {selectedIds.size > 0 ? `(${selectedIds.size})` : "all"}
          </button>
        </div>
      </div>

      {/* Table */}
      <div style={{ flex:1, overflowY:"auto", background:"var(--bg-0)" }}>
        <table className="data-table">
          <thead>
            <tr>
              <th style={{ width:36 }}>
                <input type="checkbox" checked={selectedIds.size === filtered.length && filtered.length > 0}
                  onChange={toggleAll} style={{ cursor:"pointer" }}/>
              </th>
              {[
                ["home_team","Home"],["away_team","Away"],
                ["score","Score"],["status","Status"],
                ["stage","Stage"],["scraped_at","Time"],
              ].map(([key, label]) => (
                <th key={key} onClick={() => toggleSort(key as SortKey)} style={{ cursor:"pointer" }}>
                  {label}<SortIcon col={key as SortKey}/>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filtered.map(row => (
              <tr key={row.id} onClick={() => toggleRow(row.id)}
                style={{ cursor:"pointer", background: selectedIds.has(row.id) ? "var(--accent-bg)" : undefined }}>
                <td onClick={e => e.stopPropagation()}>
                  <input type="checkbox" checked={selectedIds.has(row.id)}
                    onChange={() => toggleRow(row.id)} style={{ cursor:"pointer" }}/>
                </td>
                <td style={{ color:"var(--text-0)", fontFamily:"var(--font-ui)", fontWeight:500 }}>
                  {row.home_team}
                </td>
                <td style={{ color:"var(--text-1)", fontFamily:"var(--font-ui)" }}>
                  {row.away_team}
                </td>
                <td style={{ fontWeight:600, color:"var(--text-0)" }}>{row.score}</td>
                <td>
                  <span style={{
                    fontSize:9, fontWeight:600, padding:"2px 6px", borderRadius:4,
                    background: row.status === "LIVE" ? "var(--green-bg)" : row.status === "FT" ? "var(--bg-3)" : "var(--blue-bg)",
                    color: row.status === "LIVE" ? "var(--green)" : row.status === "FT" ? "var(--text-2)" : "var(--blue)",
                    border: `1px solid ${row.status === "LIVE" ? "rgba(29,158,117,.3)" : row.status === "FT" ? "var(--border-1)" : "rgba(55,138,221,.3)"}`,
                  }}>
                    {row.status}
                  </span>
                </td>
                <td>{row.stage}</td>
                <td style={{ color:"var(--text-3)" }}>{formatTime(row.scraped_at)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
