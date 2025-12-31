import { Route, Routes, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import ProtectedRoute from './components/ProtectedRoute'
import { AuthProvider } from './hooks/useAuth'
import LoginPage from './pages/Login'
import DashboardPage from './pages/Dashboard'
import NumbersPage from './pages/Numbers'
import SchedulePage from './pages/Schedule'
import AdminUsersPage from './pages/AdminUsers'
import ProfilePage from './pages/Profile'

const App = () => {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/"
          element={
            <ProtectedRoute allowedRoles={['ADMIN']}>
              <Layout>
                <DashboardPage />
              </Layout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/numbers"
          element={
            <ProtectedRoute>
              <Layout>
                <NumbersPage />
              </Layout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/schedule"
          element={
            <ProtectedRoute allowedRoles={['ADMIN']}>
              <Layout>
                <SchedulePage />
              </Layout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/admins"
          element={
            <ProtectedRoute allowedRoles={['ADMIN']}>
              <Layout>
                <AdminUsersPage />
              </Layout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/profile"
          element={
            <ProtectedRoute>
              <Layout>
                <ProfilePage />
              </Layout>
            </ProtectedRoute>
          }
        />
        <Route path="*" element={<Navigate to="/" />} />
      </Routes>
    </AuthProvider>
  )
}

export default App
