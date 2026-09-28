import { Route, Routes } from 'react-router-dom';

import AppShell from './components/layout/AppShell';
import ProtectedRoute from './components/auth/ProtectedRoute';
import LandingPage from './pages/LandingPage';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import EntitiesPage from './pages/EntitiesPage';
import FindingsPage from './pages/FindingsPage';
import FindingDetailPage from './pages/FindingDetailPage';
import AlertsPage from './pages/AlertsPage';
import CasesPage from './pages/CasesPage';
import InvestigationsPage from './pages/InvestigationsPage';
import AnalyticsPage from './pages/AnalyticsPage';
import PeerComparisonPage from './pages/PeerComparisonPage';
import ReviewQueuePage from './pages/ReviewQueuePage';
import ReportsPage from './pages/ReportsPage';
import AuditLogPage from './pages/AuditLogPage';
import SettingsPage from './pages/SettingsPage';
import IngestionPage from './pages/IngestionPage';
import NotFoundPage from './pages/NotFoundPage';

export default function App() {
  return (
    <Routes>
      {/* Public landing page — first thing a visitor sees */}
      <Route path="/" element={<LandingPage />} />

      {/* Auto-login (no credentials typed; used internally after Enter Platform) */}
      <Route path="/login" element={<LoginPage />} />

      {/* Authenticated workspace */}
      <Route
        element={
          <ProtectedRoute>
            <AppShell />
          </ProtectedRoute>
        }
      >
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/entities" element={<EntitiesPage />} />
        <Route path="/findings" element={<FindingsPage />} />
        <Route path="/findings/:id" element={<FindingDetailPage />} />
        <Route path="/alerts" element={<AlertsPage />} />
        <Route path="/cases" element={<CasesPage />} />
        <Route path="/investigations" element={<InvestigationsPage />} />
        <Route path="/analytics" element={<AnalyticsPage />} />
        <Route path="/ingestion" element={<IngestionPage />} />
        <Route path="/peer" element={<PeerComparisonPage />} />
        <Route path="/review-queue" element={<ReviewQueuePage />} />
        <Route path="/reports" element={<ReportsPage />} />
        <Route path="/audit-log" element={<AuditLogPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Route>

      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}