import { Routes, Route } from "react-router-dom";
import { Layout } from "./components/Layout";
import { FeatureFlagsPage } from "./pages/FeatureFlagsPage";
import { EscalationPage } from "./pages/EscalationPage";
import { AuditLogPage } from "./pages/AuditLogPage";
import { StudioPage } from "./pages/StudioPage";
import { RunsPage } from "./pages/RunsPage";
import { ResultsPage } from "./pages/ResultsPage";

function App() {
  return (
    <Layout>
      <Routes>
        {/* ── Existing admin pages ── */}
        <Route path="/"              element={<FeatureFlagsPage />} />
        <Route path="/feature-flags" element={<FeatureFlagsPage />} />
        <Route path="/escalation"    element={<EscalationPage />} />
        <Route path="/audit-log"     element={<AuditLogPage />} />

        {/* ── New workbench planes ── */}
        <Route path="/studio"  element={<StudioPage />} />
        <Route path="/runs"    element={<RunsPage />} />
        <Route path="/results" element={<ResultsPage />} />
      </Routes>
    </Layout>
  );
}

export default App;
