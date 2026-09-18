import { Navigate, Route, Routes } from 'react-router-dom';

import Layout from './components/Layout.jsx';
import ComplaintDetailPage from './pages/complaints/ComplaintDetailPage.jsx';
import ComplaintListPage from './pages/complaints/ComplaintListPage.jsx';
import DashboardPage from './pages/dashboard/DashboardPage.jsx';
import InspectionListPage from './pages/inspections/InspectionListPage.jsx';
import IssueDetailPage from './pages/issues/IssueDetailPage.jsx';
import IssueListPage from './pages/issues/IssueListPage.jsx';
import RestroomDetailPage from './pages/restrooms/RestroomDetailPage.jsx';
import RestroomListPage from './pages/restrooms/RestroomListPage.jsx';

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/restrooms" element={<RestroomListPage />} />
        <Route path="/restrooms/:restroomId" element={<RestroomDetailPage />} />
        <Route path="/inspections" element={<InspectionListPage />} />
        <Route path="/issues" element={<IssueListPage />} />
        <Route path="/issues/:issueId" element={<IssueDetailPage />} />
        <Route path="/complaints" element={<ComplaintListPage />} />
        <Route path="/complaints/:complaintId" element={<ComplaintDetailPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
