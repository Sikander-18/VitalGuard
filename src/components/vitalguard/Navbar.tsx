import { Activity, Shield, LogOut } from "lucide-react";
import { Link, useLocation } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";

const Navbar = () => {
  const { pathname } = useLocation();
  const { user, signOut, role } = useAuth();
  return (
    <header className="sticky top-0 z-40 bg-card/80 backdrop-blur-lg border-b border-border/50">
      <div className="container flex items-center justify-between h-14">
        <Link to="/" className="flex items-center gap-2">
          <Activity className="w-6 h-6 text-primary" />
          <span className="font-bold text-foreground text-lg">VitalGuard</span>
        </Link>
        {!user ? (
          <nav className="flex gap-1">
            <Link
              to="/user"
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                pathname === "/user" ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:bg-secondary"
              }`}
            >
              Patient
            </Link>
            <Link
              to="/admin"
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-1.5 ${
                pathname === "/admin" ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:bg-secondary"
              }`}
            >
              <Shield className="w-4 h-4" />
              Admin
            </Link>
          </nav>
        ) : (
          <div className="flex items-center gap-4">
            <span className="text-xs font-medium text-muted-foreground bg-secondary px-2.5 py-1 rounded-full capitalize">
              {role} Mode
            </span>
            <button
              onClick={signOut}
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium text-red-500 hover:bg-red-500/10 transition-colors"
            >
              <LogOut className="w-4 h-4" />
              Sign Out
            </button>
          </div>
        )}
      </div>
    </header>
  );
};

export default Navbar;
