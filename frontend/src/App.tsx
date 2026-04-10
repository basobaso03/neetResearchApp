/**
 * Main App Component with React Router
 */

import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Layout } from './components/layout/Layout';
import {
  HomePage,
  NewResearchPage,
  ResearchProgressPage,
  ReportViewPage,
  SessionsPage
} from './pages';

function App() {
  return (
    <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<HomePage />} />
          <Route path="new" element={<NewResearchPage />} />
          <Route path="progress/:sessionId" element={<ResearchProgressPage />} />
          <Route path="report/:sessionId" element={<ReportViewPage />} />
          <Route path="sessions" element={<SessionsPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
