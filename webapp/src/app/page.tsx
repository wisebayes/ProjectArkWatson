"use client";
import { useEffect, useRef, useState } from "react";
import dynamic from "next/dynamic";
import { ResponsiveContainer, ScatterChart, Scatter, XAxis, YAxis, ZAxis, Tooltip, CartesianGrid, BarChart, Bar, RadialBarChart, RadialBar, PieChart, Pie, Cell, AreaChart, Area } from "recharts";
import { Tabs } from "@/components/Tabs";
import { MapView } from "@/components/MapView";

type DetectionSummary = {
  event_detected?: boolean;
  classification?: any;
  severity?: any;
  monitoring?: any;
};

type OrchestratorResult = {
  management_phase: string;
  planning_triggered: boolean;
  detection_summary?: DetectionSummary;
  planning_summary?: any;
  planning_result?: any;
  session_id?: string;
  timestamp?: string;
  watsonx_summary?: string;
};

const API_BASE = process.env.NEXT_PUBLIC_ARKWATSON_API || "http://localhost:8080";

export default function Home() {
  const [latest, setLatest] = useState<OrchestratorResult | null>(null);
  const [autoRefresh, setAutoRefresh] = useState<boolean>(true);
  const [intervalSec, setIntervalSec] = useState<number>(10);
  const [wx, setWx] = useState<{ apiKey: string; url: string; projectId: string; modelId: string}>(
    { apiKey: "", url: "https://us-south.ml.cloud.ibm.com", projectId: "", modelId: "ibm/granite-3-3-8b-instruct" }
  );
  const [toastMsg, setToastMsg] = useState<string | null>(null);
  const toastTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  

  const classification = latest?.detection_summary?.classification || {};
  const severity = latest?.detection_summary?.severity || {};
  const planning = latest?.planning_result || {};

  async function fetchLatest() {
    try {
      const res = await fetch(`${API_BASE}/latest`, { cache: "no-store" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = (await res.json()) as OrchestratorResult;
      setLatest(data);
    } catch {}
  }

  useEffect(() => {
    fetchLatest();
  }, []);

  useEffect(() => {
    if (!autoRefresh) return;
    const id = setInterval(fetchLatest, intervalSec * 1000);
    return () => clearInterval(id);
  }, [autoRefresh, intervalSec]);

  function showToast(msg: string) {
    setToastMsg(msg);
    if (toastTimerRef.current) clearTimeout(toastTimerRef.current);
    toastTimerRef.current = setTimeout(() => setToastMsg(null), 5000);
  }

  function handleRunComplete(data: OrchestratorResult) {
    setLatest(data);
    const threat = Boolean(data?.detection_summary?.classification?.threat_detected);
    if (threat) {
      showToast("Sending Data for Planning Agents");
    }
  }

  return (
    <div className="space-y-6">
      {toastMsg && (
        <div className="fixed top-4 right-4 z-50">
          <div className="rounded-lg shadow-lg border border-white/10 bg-emerald-600/90 text-white px-4 py-3 text-sm font-semibold">
            {toastMsg}
          </div>
        </div>
      )}
      <Header latest={latest} />
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Stat label="Phase" value={latest?.management_phase || "unknown"} />
        <Stat label="Threat" value={(classification?.threat_detected ? "YES" : "NO").toString()} delta={`conf ${Math.round((classification?.confidence_score || 0) * 100)}%`} />
        <Stat label="Severity" value={(severity?.severity_level || "low").toString().toUpperCase()} delta={`score ${Math.round((Number(severity?.severity_score || 0) * 100))}%`} />
        <Stat label="Operations" value={`${latest?.planning_summary?.deployments_created ?? latest?.planning_result?.deployments?.deployments?.length ?? 0} deploy | ${latest?.planning_summary?.routes ?? latest?.planning_result?.evacuation?.routes?.routes?.length ?? 0} routes`} />
      </div>

      <DashboardTabs
        latest={latest}
        planning={planning}
        severity={severity}
        autoRefresh={autoRefresh}
        intervalSec={intervalSec}
        onAutoRefresh={setAutoRefresh}
        onIntervalSec={setIntervalSec}
        onRefresh={fetchLatest}
        onRunComplete={handleRunComplete}
        onApplySummary={(txt) => latest && setLatest({ ...latest, watsonx_summary: txt })}
        watsonx={wx}
        setWatsonx={setWx}
      />
    </div>
  );
}

function TwitterSentimentSimulation() {
  const [points, setPoints] = useState<{ t: number; pos: number; neg: number }[]>([]);
  const [tick, setTick] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setTick(t => t + 1), 1200);
    return () => clearInterval(id);
  }, []);
  useEffect(() => {
    const last = points[points.length - 1];
    const baseT = last ? last.t + 1 : 0;
    const pos = Math.max(0, Math.min(100, (last?.pos ?? 55) + (Math.random() * 6 - 3)));
    const neg = Math.max(0, Math.min(100, 100 - pos + (Math.random() * 4 - 2)));
    const next = [...points, { t: baseT, pos: Number(pos.toFixed(1)), neg: Number(neg.toFixed(1)) }].slice(-30);
    setPoints(next);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tick]);
  const data = points.map(p => ({ time: p.t, Positive: p.pos, Negative: p.neg }));
  return (
    <div>
      <div className="text-xs text-zinc-400 mb-2">Simulated social sentiment trend (Twitter-like stream)</div>
      <div className="h-[220px]">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#2b3445" />
            <XAxis dataKey="time" tick={{ fill: "#9aa4b2" }} stroke="#596375" />
            <YAxis tick={{ fill: "#9aa4b2" }} stroke="#596375" domain={[0, 100]} />
            <Tooltip cursor={{ strokeDasharray: "3 3" }} />
            <Area type="monotone" dataKey="Positive" stroke="#10b981" fill="#10b98133" />
            <Area type="monotone" dataKey="Negative" stroke="#ef4444" fill="#ef444433" />
          </AreaChart>
        </ResponsiveContainer>
      </div>
      <div className="mt-3 grid grid-cols-3 gap-3 text-sm">
        <div className="rounded bg-black/20 border border-white/10 p-3">
          <div className="text-xs text-zinc-400">Sample volume (min)</div>
          <div className="text-xl font-semibold">{(500 + Math.floor(Math.random()*150)).toLocaleString()}</div>
        </div>
        <div className="rounded bg-black/20 border border-white/10 p-3">
          <div className="text-xs text-zinc-400">Top hashtag</div>
          <div className="text-xl font-semibold">#SFEarthquake2025</div>
        </div>
        <div className="rounded bg-black/20 border border-white/10 p-3">
          <div className="text-xs text-zinc-400">Geo focus</div>
          <div className="text-xl font-semibold">San Francisco</div>
        </div>
      </div>
    </div>
  );
}

function NewsSimulationPanel() {
  const [items, setItems] = useState<{ id: number; title: string; ts: string }[]>([]);
  useEffect(() => {
    const seed: string[] = [
      "M6.9 earthquake shakes Bay Area; aftershocks expected",
      "City officials: Partial bridge closures for structural checks",
      "Hospitals report surge; emergency rooms near capacity",
      "BART service delays; shuttle buses activated",
      "Shelter locations opening across SF and Oakland",
      "Emergency alert: Avoid waterfront due to potential tsunami advisory",
    ];
    let counter = 0;
    setItems(seed.slice(0, 3).map((t, i) => ({ id: i, title: t, ts: new Date().toLocaleTimeString() })));
    const id = setInterval(() => {
      const next = seed[(counter++) % seed.length];
      setItems(prev => [{ id: Date.now(), title: next, ts: new Date().toLocaleTimeString() }, ...prev].slice(0, 8));
    }, 2500);
    return () => clearInterval(id);
  }, []);
  return (
    <div className="space-y-2 max-h-[280px] overflow-auto">
      {items.map(n => (
        <div key={n.id} className="rounded border border-white/10 bg-black/20 p-3">
          <div className="text-sm font-semibold">{n.title}</div>
          <div className="text-xs text-zinc-500">{n.ts}</div>
        </div>
      ))}
      {items.length === 0 && <div className="text-sm text-zinc-400">Waiting for updates…</div>}
    </div>
  );
}

function ZonesMap() {
  const [zones, setZones] = useState<any[]>([]);
  const [center, setCenter] = useState<{ lat: number; lon: number } | undefined>(undefined);
  useEffect(() => {
    fetch(`${API_BASE}/geo/population_zones`).then(async r => {
      const data = await r.json();
      const items = Array.isArray(data?.zones) ? data.zones : [];
      setZones(items);
      if (items.length) setCenter({ lat: Number(items[0].center_lat), lon: Number(items[0].center_lon) });
    });
  }, []);
  return <MapView zones={zones} center={center} />;
}

function Header({ latest }: { latest: OrchestratorResult | null }) {
  const ds = latest?.detection_summary || {};
  const c = ds.classification || {};
  const s = ds.severity || {};
  return (
    <div className="hero rounded-xl p-6 border border-white/10 shadow-xl">
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-2xl font-semibold mr-3">ArkWatson Situation Overview</h1>
        <Badge text={`Type: ${(c?.disaster_type || "Unknown").toString().toUpperCase()}`} tone="blue" />
        <Badge text={`Severity: ${(s?.severity_level || "unknown").toString().toUpperCase()}`} tone="red" />
        <Badge text={`Threat: ${c?.threat_detected ? "YES" : "NO"}`} tone="green" />
        <Badge text={`Session: ${latest?.session_id || "n/a"}`} tone="purple" />
      </div>
    </div>
  );
}

function Stat({ label, value, delta }: { label: string; value: string | number; delta?: string }) {
  return (
    <div className="glass rounded-xl p-4">
      <div className="text-sm text-zinc-300">{label}</div>
      <div className="mt-1 text-2xl font-semibold">{value}</div>
      {delta ? <div className="mt-1 text-xs text-zinc-400">{delta}</div> : null}
    </div>
  );
}

function Badge({ text, tone = "blue" }: { text: string; tone?: "blue" | "red" | "green" | "orange" | "purple" }) {
  const color = {
    blue: "bg-blue-600/90",
    red: "bg-red-700/90",
    green: "bg-emerald-700/90",
    orange: "bg-orange-600/90",
    purple: "bg-purple-700/90",
  }[tone];
  return <span className={`px-3 py-1 rounded-full text-xs font-semibold ${color}`}>{text}</span>;
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="glass rounded-xl p-5">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">{title}</h3>
      </div>
      <div className="mt-4">{children}</div>
    </section>
  );
}

function KeyResults({ data }: { data: OrchestratorResult }) {
  const ds = data?.detection_summary || {};
  const c = ds.classification || {};
  const s = ds.severity || {};
  const ps = data?.planning_summary || {};

  const lines: string[] = [];
  lines.push(`Threat: ${c?.threat_detected ? "YES" : "NO"} | Type: ${c?.disaster_type || "unknown"} | Confidence: ${c?.confidence_score || 0} | Severity: ${c?.severity_level || "low"}`);
  if (Array.isArray(c?.risk_factors) && c.risk_factors.length) {
    lines.push(`Risk Factors: ${c.risk_factors.slice(0, 3).join(", ")}`);
  }
  if (Object.keys(s).length) {
    lines.push(`Severity Score: ${s?.severity_score ?? 0} | Population At Risk: ${s?.population_at_risk ?? 0} | Critical Infra: ${s?.critical_infrastructure_count ?? 0}`);
  }
  if (Object.keys(ps).length) {
    lines.push(`Planning: deployments=${ps?.deployments_created ?? 0}, routes=${ps?.routes ?? 0}`);
  }
  return (
    <ul className="list-disc pl-6 text-zinc-300">
      {lines.map((l, i) => (
        <li key={i}>{l}</li>
      ))}
    </ul>
  );
}

function RoutesAndDeployments({ data }: { data: any }) {
  const deployments = data?.deployments?.deployments || [];
  const routes = data?.evacuation?.routes?.routes || [];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div>
        <div className="text-sm text-zinc-300 mb-2">Deployments ({deployments.length})</div>
        <div className="space-y-2 max-h-[260px] overflow-auto">
          {deployments.slice(0, 25).map((d: any, i: number) => (
            <div key={i} className="rounded border border-white/10 bg-black/20 p-3">
              <div className="text-sm font-semibold">{d?.team_id || d?.team_name || `Team ${i + 1}`}</div>
              <div className="text-xs text-zinc-400">Priority: {d?.priority_level || "n/a"}</div>
              {typeof d?.estimated_arrival_minutes !== "undefined" && <div className="text-xs text-zinc-400">ETA: {d.estimated_arrival_minutes} min</div>}
            </div>
          ))}
          {deployments.length === 0 && <div className="text-sm text-zinc-400">No deployments.</div>}
        </div>
      </div>
      <div>
        <div className="text-sm text-zinc-300 mb-2">Routes ({routes.length})</div>
        <div className="space-y-2 max-h-[260px] overflow-auto">
          {routes.slice(0, 25).map((r: any, i: number) => (
            <div key={i} className="rounded border border-white/10 bg-black/20 p-3">
              <div className="text-sm font-semibold">{Math.round(r?.distance_km ?? 0)} km</div>
              <div className="text-xs text-zinc-400">Capacity: {r?.capacity_per_hour ?? 0} ppl/hr</div>
            </div>
          ))}
          {routes.length === 0 && <div className="text-sm text-zinc-400">No routes.</div>}
        </div>
      </div>
    </div>
  );
}

function RiskPanel({ severity }: { severity: any }) {
  const impact = severity?.impact_assessment || {};
  const populationAtRisk = severity?.population_at_risk ?? 0;
  const affectedArea = severity?.affected_area_km2 ?? 0;
  const criticalInfra = severity?.critical_infrastructure_count ?? 0;
  const density = affectedArea > 0 ? Math.round(populationAtRisk / affectedArea) : 0;

  return (
    <div className="grid grid-cols-1 gap-4">
      <SeverityGauge score={Number(severity?.severity_score || 0)} />
      <div className="grid grid-cols-3 gap-3">
        <div className="rounded bg-black/20 border border-white/10 p-3">
          <div className="text-xs text-zinc-400">Population at Risk</div>
          <div className="text-xl font-semibold">{populationAtRisk.toLocaleString()}</div>
        </div>
        <div className="rounded bg-black/20 border border-white/10 p-3">
          <div className="text-xs text-zinc-400">Affected Area</div>
          <div className="text-xl font-semibold">{affectedArea.toLocaleString()} km²</div>
        </div>
        <div className="rounded bg-black/20 border border-white/10 p-3">
          <div className="text-xs text-zinc-400">Critical Infrastructure</div>
          <div className="text-xl font-semibold">{criticalInfra}</div>
        </div>
      </div>
      <div className="rounded bg-black/20 border border-white/10 p-3">
        <div className="text-xs text-zinc-400">Population Density</div>
        <div className="text-xl font-semibold">{density.toLocaleString()} ppl/km²</div>
      </div>
      <div className="flex flex-wrap gap-2">
        {Object.entries(impact).map(([k, v]) => (
          <span key={k} className={`px-3 py-1 rounded-full text-xs font-semibold ${v ? "bg-red-700/90" : "bg-zinc-600/60"}`}>
            {k.replace(/_/g, " ")}: {v ? "Yes" : "No"}
          </span>
        ))}
        {Object.keys(impact).length === 0 && <div className="text-sm text-zinc-400">No impact markers.</div>}
      </div>
    </div>
  );
}

function CapacityVsDistance({ routes }: { routes: any[] }) {
  const data = routes.map((r: any) => ({
    distance_km: Number(r?.distance_km || 0),
    capacity_per_hour: Number(r?.capacity_per_hour || 0),
  }));
  if (!data.length) return <div className="text-sm text-zinc-400">No route data.</div>;
  return (
    <div className="rounded border border-white/10 bg-black/20 p-3">
      <div className="text-sm text-zinc-300 mb-2">Evacuation Route Capacity vs Distance</div>
      <div className="h-[220px]">
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart>
            <CartesianGrid strokeDasharray="3 3" stroke="#2b3445" />
            <XAxis dataKey="distance_km" name="Distance (km)" tick={{ fill: "#9aa4b2" }} stroke="#596375" />
            <YAxis dataKey="capacity_per_hour" name="Capacity/hr" tick={{ fill: "#9aa4b2" }} stroke="#596375" />
            <ZAxis range={[60, 200]} />
            <Tooltip cursor={{ strokeDasharray: "3 3" }} />
            <Scatter data={data} fill="#10b981" />
          </ScatterChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function RouteCapacityHistogram({ routes }: { routes: any[] }) {
  const data = routes.map((r: any, i: number) => ({ index: i + 1, capacity_per_hour: Number(r?.capacity_per_hour || 0) }));
  if (!data.length) return <div className="text-sm text-zinc-400">No route data.</div>;
  return (
    <div className="rounded border border-white/10 bg-black/20 p-3">
      <div className="text-sm text-zinc-300 mb-2">Route Capacity Distribution</div>
      <div className="h-[220px]">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#2b3445" />
            <XAxis dataKey="index" tick={{ fill: "#9aa4b2" }} stroke="#596375" />
            <YAxis tick={{ fill: "#9aa4b2" }} stroke="#596375" />
            <Tooltip cursor={{ strokeDasharray: "3 3" }} />
            <Bar dataKey="capacity_per_hour" fill="#60a5fa" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function SeverityGauge({ score }: { score: number }) {
  const value = Math.max(0, Math.min(100, Math.round((score || 0) * 100)));
  const data = [{ name: "score", value }];
  return (
    <div className="rounded border border-white/10 bg-black/20 p-3">
      <div className="text-sm text-zinc-300 mb-2">Severity Gauge</div>
      <div className="h-[160px]">
        <ResponsiveContainer width="100%" height="100%">
          <RadialBarChart innerRadius="60%" outerRadius="100%" data={data} startAngle={180} endAngle={0}>
            <RadialBar background={{ fill: "#1f2937" }} isAnimationActive={false} dataKey="value" fill="#b91c1c" />
          </RadialBarChart>
        </ResponsiveContainer>
      </div>
      <div className="text-center text-xl font-semibold">{value}%</div>
    </div>
  );
}

function DeploymentTimelineScatter({ deployments }: { deployments: any[] }) {
  const data = deployments.map(d => ({ x: Number(d?.estimated_arrival_minutes || 0), y: (d?.priority_level || '').toString() }));
  if (!data.length) return <div className="text-sm text-zinc-400">No deployment data.</div>;
  return (
    <div className="rounded border border-white/10 bg-black/20 p-3">
      <div className="text-sm text-zinc-300 mb-2">Team Deployment Timeline (ETA vs Priority)</div>
      <div className="h-[220px]">
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart>
            <CartesianGrid strokeDasharray="3 3" stroke="#2b3445" />
            <XAxis dataKey="x" name="ETA (min)" tick={{ fill: "#9aa4b2" }} stroke="#596375" />
            <YAxis dataKey="y" name="Priority" tick={{ fill: "#9aa4b2" }} stroke="#596375" />
            <Tooltip cursor={{ strokeDasharray: "3 3" }} />
            <Scatter data={data} fill="#f59e0b" />
          </ScatterChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function ETADistributionHistogram({ deployments }: { deployments: any[] }) {
  const buckets: Record<string, number> = {};
  deployments.forEach(d => {
    const eta = Number(d?.estimated_arrival_minutes || 0);
    const key = `${Math.floor(eta / 10) * 10}-${Math.floor(eta / 10) * 10 + 9}`;
    buckets[key] = (buckets[key] || 0) + 1;
  });
  const data = Object.entries(buckets).map(([range, count]) => ({ range, count }));
  if (!data.length) return <div className="text-sm text-zinc-400">No ETA data.</div>;
  return (
    <div className="rounded border border-white/10 bg-black/20 p-3">
      <div className="text-sm text-zinc-300 mb-2">Deployment ETA Distribution</div>
      <div className="h-[220px]">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#2b3445" />
            <XAxis dataKey="range" tick={{ fill: "#9aa4b2" }} stroke="#596375" />
            <YAxis tick={{ fill: "#9aa4b2" }} stroke="#596375" />
            <Tooltip cursor={{ strokeDasharray: "3 3" }} />
            <Bar dataKey="count" fill="#22c55e" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function SeverityFactorsBar({ severity }: { severity: any }) {
  const factors = severity?.severity_factors || {};
  const regex = /[\d,.]+/;
  const data = Object.entries(factors).map(([k, v]: any) => {
    const m = (String(v).replace(/,/g, '').match(regex) || ["0"])[0];
    return { name: k.replace(/_/g, ' ').toUpperCase(), value: Number(m) };
  });
  if (!data.length) return <div className="text-sm text-zinc-400">No factors available.</div>;
  return (
    <div className="rounded border border-white/10 bg-black/20 p-3">
      <div className="text-sm text-zinc-300 mb-2">Severity Factors</div>
      <div className="h-[220px]">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#2b3445" />
            <XAxis dataKey="name" tick={{ fill: "#9aa4b2" }} stroke="#596375" interval={0} angle={-30} height={60} textAnchor="end" />
            <YAxis tick={{ fill: "#9aa4b2" }} stroke="#596375" />
            <Tooltip cursor={{ strokeDasharray: "3 3" }} />
            <Bar dataKey="value" fill="#3b82f6" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function PopulationImpactPie({ severity }: { severity: any }) {
  const population_at_risk = Number(severity?.population_at_risk || 0);
  const critical_infrastructure = Number(severity?.critical_infrastructure_count || 0);
  const safe_estimate = Math.round(population_at_risk * 0.3);
  const data = [
    { name: 'At Risk', value: population_at_risk },
    { name: 'Safe (Est.)', value: safe_estimate },
    { name: 'Critical Infra (x10k)', value: critical_infrastructure * 10000 },
  ];
  const colors = ['#ef4444', '#10b981', '#6366f1'];
  if (population_at_risk <= 0) return <div className="text-sm text-zinc-400">No population metrics.</div>;
  return (
    <div className="rounded border border-white/10 bg-black/20 p-3">
      <div className="text-sm text-zinc-300 mb-2">Population Impact</div>
      <div className="h-[240px]">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie data={data} dataKey="value" nameKey="name" outerRadius={90} label>
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={colors[index % colors.length]} />
              ))}
            </Pie>
            <Tooltip />
          </PieChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
function GenerateSummary({ latest, onApply, watsonx }: { latest: OrchestratorResult | null; onApply: (txt: string) => void; watsonx: { apiKey: string; url: string; projectId: string; modelId: string } }) {
  const [busy, setBusy] = useState(false);
  async function run() {
    if (!latest) return;
    try {
      setBusy(true);
      const res = await fetch(`${API_BASE}/summary`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ results: latest, model_id: watsonx.modelId, watsonx_config: { api_key: watsonx.apiKey, url: watsonx.url, project_id: watsonx.projectId } }),
      });
      if (res.ok) {
        const data = await res.json();
        onApply(String(data?.summary || ""));
      }
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="flex items-center gap-3">
      <div className="text-zinc-400 text-sm">No model summary. Generate one?</div>
      <button disabled={busy} className="rounded bg-indigo-600 px-3 py-1 text-sm font-semibold" onClick={run}>{busy ? "Generating..." : "Generate"}</button>
    </div>
  );
}

function RunPanel({ onRunComplete }: { onRunComplete: (r: OrchestratorResult) => void }) {
  const [mode, setMode] = useState<"Detection" | "Complete Response">("Complete Response");
  const [region, setRegion] = useState("San Francisco Bay Area");
  const [lat, setLat] = useState(37.7749);
  const [lon, setLon] = useState(-122.4194);
  const [radius, setRadius] = useState(100);
  const [modelId, setModelId] = useState("ibm/granite-3-3-8b-instruct");
  const [apiKey, setApiKey] = useState("");
  const [url, setUrl] = useState("https://us-south.ml.cloud.ibm.com");
  const [projectId, setProjectId] = useState("");
  const [prompt, setPrompt] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit() {
    try {
      setBusy(true);
      const endpoint = mode === "Detection" ? "detect" : "complete_response";
      const res = await fetch(`${API_BASE}/${endpoint}?persist=true`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          lat,
          lon,
          radius_km: radius,
          location_name: region,
          watsonx_config: { api_key: apiKey, url, project_id: projectId, model_id: modelId },
          situation_description: prompt,
        }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = (await res.json()) as OrchestratorResult;
      onRunComplete(data);
    } catch {
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-3 text-sm">
      <div>
        <label className="block text-zinc-300 mb-1">Granite model</label>
        <select value={modelId} onChange={e => setModelId(e.target.value)} className="w-full rounded bg-black/30 border border-white/10 px-2 py-2">
          <option>ibm/granite-3-8b-instruct</option>
          <option>ibm/granite-3-3-8b-instruct</option>
          <option>ibm/granite-13b-instruct-v2</option>
          <option>ibm/granite-13b-chat-v2</option>
          <option>ibm/granite-20b-multilingual</option>
        </select>
      </div>

      <div>
        <label className="block text-zinc-300 mb-1">Situation / Instructions</label>
        <textarea value={prompt} onChange={e => setPrompt(e.target.value)} rows={4} className="w-full rounded bg-black/30 border border-white/10 px-2 py-2" placeholder="Describe the situation or provide instructions for the planning agents..." />
      </div>

      <button disabled={busy} onClick={submit} className="rounded bg-emerald-600 hover:bg-emerald-500 transition px-4 py-2 font-semibold">
        {busy ? "Running..." : "Run"}
      </button>

      <details className="rounded border border-white/10 bg-black/20 p-3">
        <summary className="cursor-pointer text-zinc-300">Advanced options</summary>
        <div className="grid grid-cols-2 gap-3 mt-3">
          <div>
            <label className="block text-zinc-300 mb-1">Workflow</label>
            <select value={mode} onChange={e => setMode(e.target.value as any)} className="w-full rounded bg-black/30 border border-white/10 px-2 py-2">
              <option>Detection</option>
              <option>Complete Response</option>
            </select>
          </div>
          <div>
            <label className="block text-zinc-300 mb-1">Region</label>
            <input value={region} onChange={e => setRegion(e.target.value)} className="w-full rounded bg-black/30 border border-white/10 px-2 py-2" />
          </div>
        </div>
        <div className="grid grid-cols-3 gap-3 mt-3">
          <div>
            <label className="block text-zinc-300 mb-1">Lat</label>
            <input type="number" value={lat} onChange={e => setLat(Number(e.target.value))} className="w-full rounded bg-black/30 border border-white/10 px-2 py-2" />
          </div>
          <div>
            <label className="block text-zinc-300 mb-1">Lon</label>
            <input type="number" value={lon} onChange={e => setLon(Number(e.target.value))} className="w-full rounded bg-black/30 border border-white/10 px-2 py-2" />
          </div>
          <div>
            <label className="block text-zinc-300 mb-1">Radius (km)</label>
            <input type="number" value={radius} onChange={e => setRadius(Number(e.target.value))} className="w-full rounded bg-black/30 border border-white/10 px-2 py-2" />
          </div>
        </div>
        <div className="grid grid-cols-3 gap-3 mt-3">
          <input placeholder="API key" value={apiKey} onChange={e => setApiKey(e.target.value)} className="w-full rounded bg-black/30 border border-white/10 px-2 py-2" />
          <input placeholder="URL" value={url} onChange={e => setUrl(e.target.value)} className="w-full rounded bg-black/30 border border-white/10 px-2 py-2" />
          <input placeholder="Project ID" value={projectId} onChange={e => setProjectId(e.target.value)} className="w-full rounded bg-black/30 border border-white/10 px-2 py-2" />
        </div>
      </details>
    </div>
  );
}

function DashboardTabs({
  latest,
  planning,
  severity,
  autoRefresh,
  intervalSec,
  onAutoRefresh,
  onIntervalSec,
  onRefresh,
  onRunComplete,
  onApplySummary,
  watsonx,
  setWatsonx,
}: {
  latest: OrchestratorResult | null;
  planning: any;
  severity: any;
  autoRefresh: boolean;
  intervalSec: number;
  onAutoRefresh: (b: boolean) => void;
  onIntervalSec: (n: number) => void;
  onRefresh: () => void;
  onRunComplete: (r: OrchestratorResult) => void;
  onApplySummary: (txt: string) => void;
  watsonx: { apiKey: string; url: string; projectId: string; modelId: string };
  setWatsonx: (w: { apiKey: string; url: string; projectId: string; modelId: string }) => void;
}) {
  const [tab, setTab] = useState("Overview");
  return (
    <div className="space-y-4">
      <Tabs tabs={["Overview", "Planning", "Risk", "Raw"]} current={tab} onChange={setTab} />
      {tab === "Overview" && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <Section title="Executive Summary">{latest ? <KeyResults data={latest} /> : <div className="text-zinc-400">No data yet.</div>}</Section>
            <Section title="AI Executive Summary">
              {latest?.watsonx_summary ? (
                <div className="prose prose-invert max-w-none whitespace-pre-wrap">{latest.watsonx_summary}</div>
              ) : (
                <GenerateSummary latest={latest} onApply={onApplySummary} watsonx={watsonx} />
              )}
            </Section>
            <Section title="Run">
              <RunPanel onRunComplete={onRunComplete} />
            </Section>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2">
              <Section title="Twitter Sentiment — San Francisco 2025 Earthquake">
                <TwitterSentimentSimulation />
              </Section>
            </div>
            <div className="lg:col-span-1">
              <Section title="Live News Simulation">
                <NewsSimulationPanel />
              </Section>
            </div>
          </div>
        </div>
      )}
      {tab === "Planning" && (
        <div className="grid grid-cols-1 gap-6">
          <Section title="Map">
            <ZonesMap />
          </Section>
          <Section title="Routes & Deployments">
            <RoutesAndDeployments data={planning} />
            <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-4">
              <CapacityVsDistance routes={planning?.evacuation?.routes?.routes || []} />
              <RouteCapacityHistogram routes={planning?.evacuation?.routes?.routes || []} />
            </div>
            <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-4">
              <DeploymentTimelineScatter deployments={planning?.deployments?.deployments || []} />
              <ETADistributionHistogram deployments={planning?.deployments?.deployments || []} />
            </div>
          </Section>
        </div>
      )}
      {tab === "Risk" && (
        <div className="grid grid-cols-1 gap-6">
          <Section title="Risk & Population Impact">
            <RiskPanel severity={severity} />
          </Section>
          <Section title="Severity Factors">
            <SeverityFactorsBar severity={severity} />
          </Section>
          <Section title="Population Impact">
            <PopulationImpactPie severity={severity} />
          </Section>
        </div>
      )}
      {tab === "Raw" && (
        <Section title="Raw JSON">
          {latest ? (
            <pre className="max-h-[500px] overflow-auto text-xs bg-black/30 p-4 rounded border border-white/10">{JSON.stringify(latest, null, 2)}</pre>
          ) : (
            <div className="text-zinc-400">No data loaded.</div>
          )}
        </Section>
      )}
    </div>
  );
}

