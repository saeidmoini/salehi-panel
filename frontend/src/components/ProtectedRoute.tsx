import { Navigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'

const ProtectedRoute: React.FC<{ children: JSX.Element }> = ({ children }) => {
  const { token, loading } = useAuth()
  if (loading) return <div className="p-6">در حال بارگذاری...</div>
  if (!token) return <Navigate to="/login" replace />
  return children
}

export default ProtectedRoute
