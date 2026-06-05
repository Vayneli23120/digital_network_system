import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import MainLayout from '@/app/layout/MainLayout'
import DashboardPage from '@/pages/dashboard/Dashboard'
import AIAnalysisPage from '@/pages/ai/AIAnalysis'
import JobsPage from '@/pages/jobs/Jobs'
import LoginPage from '@/pages/auth/Login'
import { useAuthStore } from '@/app/store/auth'

function App() {
  const { isLoggedIn } = useAuthStore()

  return (
    <BrowserRouter>
      <Routes>
        {/* 公开路由 */}
        <Route path="/login" element={<LoginPage />} />

        {/* 受保护路由 */}
        <Route
          path="/"
          element={
            isLoggedIn ? <MainLayout /> : <Navigate to="/login" replace />
          }
        >
          <Route index element={<DashboardPage />} />
          <Route path="dashboard" element={<DashboardPage />} />
          <Route path="ai-analysis" element={<AIAnalysisPage />} />
          <Route path="jobs" element={<JobsPage />} />
          {/* 更多路由将在后续添加 */}
        </Route>

        {/* 404 */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App