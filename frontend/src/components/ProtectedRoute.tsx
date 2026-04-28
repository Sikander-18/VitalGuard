import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";

export const ProtectedRoute = () => {
  const { user, loading } = useAuth();
  
  if (loading) return <div className="min-h-screen flex items-center justify-center">Loading...</div>;
  if (!user) return <Navigate to="/auth" replace />;
  
  return <Outlet />;
};

interface RoleRouteProps {
  allowedRole: "user" | "admin";
}

export const RoleRoute = ({ allowedRole }: RoleRouteProps) => {
  const { role, loading } = useAuth();
  
  if (loading) return <div className="min-h-screen flex items-center justify-center">Loading...</div>;
  
  if (role !== allowedRole) {
    // If role doesn't match, redirect them to their native dashboard or auth
    if (role === "admin") return <Navigate to="/admin" replace />;
    if (role === "user") return <Navigate to="/user" replace />;
    return <Navigate to="/auth" replace />;
  }
  
  return <Outlet />;
};
