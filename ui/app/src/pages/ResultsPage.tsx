import { useState, useMemo } from "react";

const D = {
  bg0:"#0e0f14", bg1:"#111318", bg2:"#171820", bg3:"#1c1d27",
  border0:"#1a1b22", border1:"#22232e",
  text0:"#e2e2e8", text1:"#a0a0b4", text2:"#565668", text3:"#32333e",
  accent:"#4f46e5", green:"#1D9E75", greenBg:"#0a2018", greenBorder:"rgba(29,158,117,0.25)",
  amber:"#EF9F27", amberBg:"#1a1200",
  blue:"#378ADD", blueBg:"#081828", blueBorder:"rgba(55,138,221,0.25)",
};

interface ResultRow {
  id:string; home_team:string; away_team:string;
  score:string; status:string; stage:string;
  match_url:string; scraped_at:string;
}

const DEMO:ResultRow[] = Array.from({length:24},(_,i)=>({
  id:`row-${i}`,
  home_team:["Boston Celtics","LA Lakers","Golden State Warriors","Miami Heat","Chicago Bulls","NY Knicks"][i%6],
  away_team:["Dallas Mavericks","Phoenix Suns","Denver Nuggets","Milwaukee Bucks","Cleveland Cavaliers","Atlanta Hawks"][i%6],
  score:`${Math.floor(Math.random()*40)+70}–${Math.floor(Math.random()*40)+70}`,
  status:["LIVE","FT","SCH"][i%3], stage:["Q1","Q2","Q3","Q4","FT","—"][i%6],
  match_url:`https://flashscore.com/match/abc${i}`,
  scraped_at:new Date(Date.now()-i*120000).toISOString(),
}));

type SortKey=keyof ResultRow;

export function ResultsPage() {
  const [search,setSearch]=useState("");
  const [sortKey,setSortKey]=useState<SortKey>("scraped_at");
  const [sortDir,setSortDir]=useState<"asc"|"desc">("desc");
  const [selected,setSelected]=useState<Set<string>>(new Set());
  const [fmt,setFmt]=useState<"json"|"csv">("json");

  const filtered=useMemo(()=>{
    const q=search.toLowerCase();
    return DEMO.filter(r=>!q||r.home_team.toLowerCase().includes(q)||r.away_team.toLowerCase().includes(q))
      .sort((a,b)=>{const va=a[sortKey],vb=b[sortKey];const c=va<vb?-1:va>vb?1:0;return sortDir==="asc"?c:-c;});
  },[search,sortKey,sortDir]);

  const toggleSort=(k:SortKey)=>{if(sortKey===k)setSortDir(d=>d==="asc"?"desc":"asc");else{setSortKey(k);setSortDir("desc");}};
  const toggleRow=(id:string)=>setSelected(p=>{const n=new Set(p);n.has(id)?n.delete(id):n.add(id);return n;});
  const toggleAll=()=>setSelected(p=>p.size===filtered.length?new Set():new Set(filtered.map(r=>r.id)));

  const handleExport=()=>{
    const rows=filtered.filter(r=>selected.size===0||selected.has(r.id));
    const keys=Object.keys(rows[0]??{}) as SortKey[];
    const content=fmt==="json"
      ?JSON.stringify(rows,null,2)
      :[keys.join(","),...rows.map(r=>keys.map(k=>`"${r[k]}"`).join(","))].join("\n");
    const a=document.createElement("a");
    a.href=URL.createObjectURL(new Blob([content],{type:fmt==="json"?"application/json":"text/csv"}));
    a.download=`scrapamoja-results.${fmt}`; a.click();
  };

  const SortIcon=({col}:{col:SortKey})=>(
    <span style={{ fontSize:9,marginLeft:4,color:sortKey===col?D.accent:D.text3 }}>
      {sortKey===col?(sortDir==="asc"?"↑":"↓"):"⇅"}
    </span>
  );

  return (
    <div style={{ display:"flex",flexDirection:"column",height:"100%",overflow:"hidden",
      background:D.bg0,fontFamily:"system-ui, sans-serif",color:D.text0 }}>

      {/* Topbar */}
      <div style={{ height:50,background:D.bg1,borderBottom:`1px solid ${D.border1}`,
        display:"flex",alignItems:"center",padding:"0 16px",gap:12,flexShrink:0 }}>
        <span style={{ fontSize:13,fontWeight:600,color:D.text0 }}>Results</span>
        <span style={{ fontSize:10,color:D.text3,fontFamily:"monospace" }}>
          {filtered.length} rows{selected.size>0?` · ${selected.size} selected`:""}
        </span>
        <input value={search} onChange={e=>setSearch(e.target.value)} placeholder="Filter rows…"
          style={{ background:D.bg3,border:`1px solid ${D.border1}`,borderRadius:7,
            padding:"4px 10px",fontSize:11,color:D.text0,fontFamily:"monospace",outline:"none",width:200 }}/>
        <div style={{ marginLeft:"auto",display:"flex",gap:8,alignItems:"center" }}>
          <select value={fmt} onChange={e=>setFmt(e.target.value as any)}
            style={{ background:D.bg3,border:`1px solid ${D.border1}`,borderRadius:7,
              padding:"4px 8px",fontSize:11,color:D.text1,outline:"none",cursor:"pointer" }}>
            <option value="json">JSON</option>
            <option value="csv">CSV</option>
          </select>
          <button onClick={handleExport}
            style={{ padding:"6px 14px",fontSize:12,fontWeight:600,border:"none",
              borderRadius:8,background:D.accent,color:"white",cursor:"pointer" }}>
            Export {selected.size>0?`(${selected.size})`:"all"}
          </button>
        </div>
      </div>

      {/* Table */}
      <div style={{ flex:1,overflowY:"auto" }}>
        <table style={{ width:"100%",borderCollapse:"collapse",fontSize:12 }}>
          <thead>
            <tr style={{ background:D.bg2 }}>
              <th style={{ width:36,padding:"8px 12px",textAlign:"left",
                borderBottom:`1px solid ${D.border1}`,position:"sticky",top:0,background:D.bg2 }}>
                <input type="checkbox"
                  checked={selected.size===filtered.length&&filtered.length>0}
                  onChange={toggleAll} style={{ cursor:"pointer" }}/>
              </th>
              {[["home_team","Home"],["away_team","Away"],["score","Score"],
                ["status","Status"],["stage","Stage"],["scraped_at","Time"]].map(([key,label])=>(
                <th key={key} onClick={()=>toggleSort(key as SortKey)}
                  style={{ padding:"8px 12px",textAlign:"left",cursor:"pointer",
                    fontSize:10,fontWeight:600,letterSpacing:"0.06em",textTransform:"uppercase",
                    color:D.text2,borderBottom:`1px solid ${D.border1}`,
                    position:"sticky",top:0,background:D.bg2 }}>
                  {label}<SortIcon col={key as SortKey}/>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filtered.map(row=>(
              <tr key={row.id} onClick={()=>toggleRow(row.id)}
                style={{ cursor:"pointer",
                  background:selected.has(row.id)?"rgba(99,102,241,0.06)":"transparent" }}>
                <td style={{ padding:"8px 12px",borderBottom:`1px solid ${D.border0}` }}
                  onClick={e=>e.stopPropagation()}>
                  <input type="checkbox" checked={selected.has(row.id)}
                    onChange={()=>toggleRow(row.id)} style={{ cursor:"pointer" }}/>
                </td>
                <td style={{ padding:"8px 12px",borderBottom:`1px solid ${D.border0}`,
                  color:D.text0,fontWeight:500 }}>{row.home_team}</td>
                <td style={{ padding:"8px 12px",borderBottom:`1px solid ${D.border0}`,
                  color:D.text1,fontFamily:"monospace" }}>{row.away_team}</td>
                <td style={{ padding:"8px 12px",borderBottom:`1px solid ${D.border0}`,
                  fontWeight:600,color:D.text0,fontFamily:"monospace" }}>{row.score}</td>
                <td style={{ padding:"8px 12px",borderBottom:`1px solid ${D.border0}` }}>
                  <span style={{ fontSize:9,fontWeight:700,padding:"2px 7px",borderRadius:4,
                    background:row.status==="LIVE"?D.greenBg:row.status==="FT"?D.bg3:D.blueBg,
                    color:row.status==="LIVE"?D.green:row.status==="FT"?D.text2:D.blue,
                    border:`1px solid ${row.status==="LIVE"?D.greenBorder:row.status==="FT"?"rgba(255,255,255,0.06)":D.blueBorder}`,
                  }}>{row.status}</span>
                </td>
                <td style={{ padding:"8px 12px",borderBottom:`1px solid ${D.border0}`,color:D.text2 }}>
                  {row.stage}
                </td>
                <td style={{ padding:"8px 12px",borderBottom:`1px solid ${D.border0}`,
                  color:D.text3,fontFamily:"monospace" }}>
                  {new Date(row.scraped_at).toLocaleTimeString("en-GB",{hour12:false,hour:"2-digit",minute:"2-digit"})}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
