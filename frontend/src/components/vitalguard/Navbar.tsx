import { useState } from "react";
import { Activity, Shield, LogOut, Bell } from "lucide-react";
import { Link, useLocation } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { useNotifications } from "@/hooks/useNotifications";

const Navbar = () => {
  const { pathname } = useLocation();
  const { user, signOut, role } = useAuth();
  const { notifications, requestPermission, permission, markAllAsRead, clearAll } = useNotifications(user?.uid);
  const [showNotifications, setShowNotifications] = useState(false);

  const unreadCount = notifications.filter(n => !n.read).length;

  return (
    <header className="sticky top-0 z-40 bg-card/80 backdrop-blur-lg border-b border-border/50">
      <div className="container flex items-center justify-between h-14 px-4">
        <Link to="/" className="flex items-center gap-2">
          <Activity className="w-6 h-6 text-primary" />
          <span className="font-bold text-foreground text-lg">VitalGuard</span>
        </Link>
        {!user ? (
          <nav className="flex gap-1">
            <Link
              to="/user"
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${pathname === "/user" ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:bg-secondary"
                }`}
            >
              Patient
            </Link>
            <Link
              to="/admin"
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-1.5 ${pathname === "/admin" ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:bg-secondary"
                }`}
            >
              <Shield className="w-4 h-4" />
              Admin
            </Link>
          </nav>
        ) : (
          <div className="flex items-center gap-4 relative">
            <span className="text-xs font-medium text-muted-foreground bg-secondary px-2.5 py-1 rounded-full capitalize">
              {role} Mode
            </span>

            {/* Notification Bell Dropdown */}
            <div className="relative">
              <button
                onClick={() => setShowNotifications(!showNotifications)}
                className="relative p-2 rounded-lg text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors"
                aria-label="Toggle notifications"
              >
                <Bell className="w-5 h-5" />
                {unreadCount > 0 && (
                  <span className="absolute top-1 right-1 w-4 h-4 bg-red-500 text-white text-[9px] font-bold rounded-full flex items-center justify-center animate-pulse">
                    {unreadCount}
                  </span>
                )}
              </button>

              {showNotifications && (
                <>
                  {/* Overlay to close notifications when clicking outside */}
                  <div className="fixed inset-0 z-40" onClick={() => setShowNotifications(false)} />
                  
                  <div className="absolute right-0 mt-2 w-80 bg-card border border-border rounded-xl shadow-xl z-50 overflow-hidden animate-in fade-in slide-in-from-top-3 duration-200">
                    {/* Header */}
                    <div className="p-3 border-b border-border flex items-center justify-between bg-secondary/30">
                      <span className="text-xs font-semibold text-foreground flex items-center gap-1.5">
                        <Bell className="w-3.5 h-3.5 text-primary animate-bounce" /> Live Alerts
                      </span>
                      <div className="flex gap-2">
                        {unreadCount > 0 && (
                          <button onClick={markAllAsRead} className="text-[10px] text-primary hover:underline font-medium">
                            Mark read
                          </button>
                        )}
                        {notifications.length > 0 && (
                          <button onClick={clearAll} className="text-[10px] text-red-500 hover:underline font-medium">
                            Clear
                          </button>
                        )}
                      </div>
                    </div>

                    {/* Browser Push Activation Banner */}
                    {permission === "default" && (
                      <button
                        onClick={() => { requestPermission(); setShowNotifications(false); }}
                        className="w-full px-3 py-2 bg-primary/10 border-b border-primary/20 text-[10px] font-semibold text-primary hover:bg-primary/20 transition-colors text-center"
                      >
                        🔔 Enable Desktop System-Level Push Alerts
                      </button>
                    )}

                    {/* Scrollable Alerts List */}
                    <div className="max-h-64 overflow-y-auto divide-y divide-border custom-scrollbar">
                      {notifications.length > 0 ? (
                        notifications.map((n) => (
                          <div
                            key={n.id}
                            className={`p-3 text-left transition-colors hover:bg-secondary/20 ${!n.read ? "bg-primary/5" : ""}`}
                          >
                            <div className="flex justify-between items-start gap-2 mb-1">
                              <span className={`text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full border ${
                                n.severity === "CRITICAL" 
                                  ? "bg-red-500/10 text-red-400 border-red-500/20" 
                                  : n.severity === "FUTURE_ALERT" 
                                  ? "bg-amber-500/10 text-amber-400 border-amber-500/20" 
                                  : "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                              }`}>
                                {n.severity === "CRITICAL" ? "🚨 Critical" : n.severity === "FUTURE_ALERT" ? "⚠️ Warning" : "✅ Normal"}
                              </span>
                              <span className="text-[9px] text-muted-foreground">
                                {new Date(n.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                              </span>
                            </div>
                            <p className="text-xs font-semibold text-foreground mb-0.5">{n.title}</p>
                            <p className="text-[11px] text-muted-foreground leading-relaxed">{n.body}</p>
                          </div>
                        ))
                      ) : (
                        <div className="py-8 text-center text-xs text-muted-foreground italic">
                          No alerts recorded yet
                        </div>
                      )}
                    </div>
                  </div>
                </>
              )}
            </div>

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
