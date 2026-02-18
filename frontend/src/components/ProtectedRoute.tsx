import { Navigate } from 'react-router-dom'
import { useAuth } from '../hooks/useAuth'

interface ProtectedRouteProps {
  children: JSX.Element
  allowedRoles?: Array<'ADMIN' | 'AGENT'>
  requireSuperuser?: boolean
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children, allowedRoles, requireSuperuser }) => {
  const { token, loading, user } = useAuth()
  if (loading) return <div className="p-6">در حال بارگذاری...</div>
  if (!token) return <Navigate to="/login" replace />
  if (allowedRoles && user && !allowedRoles.includes(user.role)) {
    return <Navigate to="/login" replace />
  }
  if (requireSuperuser && !user?.is_superuser) {
    return <Navigate to="/login" replace />
  }
  return children
}

export default ProtectedRoute
