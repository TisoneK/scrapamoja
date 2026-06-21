import { Routes, Route } from "react-router-dom";
import { Layout } from "./components/Layout";
import { FeatureFlagsPage } from "./pages/FeatureFlagsPage";
import { EscalationPage } from "./pages/EscalationPage";
import { AuditLogPage } from "./pages/AuditLogPage";

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<FeatureFlagsPage />} />
        <Route path="/feature-flags" element={<FeatureFlagsPage />} />
        <Route path="/escalation" element={<EscalationPage />} />
        <Route path="/audit-log" element={<AuditLogPage />} />
      </Routes>
    </Layout>
  );
}

export default App;
