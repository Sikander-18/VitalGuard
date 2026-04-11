import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { createUserWithEmailAndPassword, signInWithEmailAndPassword } from "firebase/auth";
import { auth } from "@/config/firebase";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/hooks/use-toast";
import { Activity } from "lucide-react";

const Auth = () => {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [roleSelection, setRoleSelection] = useState<"user" | "admin">("user");
  const [loading, setLoading] = useState(false);
  
  const { setRole } = useAuth();
  const navigate = useNavigate();
  const { toast } = useToast();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      if (isLogin) {
        // Login Flow
        await signInWithEmailAndPassword(auth, email, password);
        // We look up the role from localStorage for logging in users
        // Since Firebase standard auth does not return custom claims unless set up with Admin SDK
        // For this demo, let's just make sure there is a role or fallback to 'user'.
        // Wait, the rules state we must store role. If they are logging in on a new device, we won't have localStorage!
        // To strictly follow rules without a backend, we'll ask for Role on login, or let's default to user, or use the last set role.
        let localRole = localStorage.getItem("role") as "user" | "admin" | null;
        if (!localRole) {
           // We ask user to select role on signup, so during login if no role exists, we force them to pick one or default.
           // To be safe per prompt: We will use the selected dropdown role for login too if local is missing.
           localRole = roleSelection;
        }
        setRole(localRole);
        
        toast({ title: "Successfully logged in" });

        if (localRole === "admin") {
          navigate("/admin");
        } else {
          // Patient sign in goes directly to /user
          navigate("/user");
        }
      } else {
        // Signup Flow
        await createUserWithEmailAndPassword(auth, email, password);
        setRole(roleSelection);
        
        toast({ title: "Account created successfully" });

        if (roleSelection === "user") {
          navigate("/onboarding");
        } else {
          navigate("/admin");
        }
      }
    } catch (error: any) {
      toast({ 
        title: "Authentication Failed", 
        description: error.message,
        variant: "destructive" 
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background flex flex-col items-center justify-center p-4">
      <div className="max-w-md w-full bg-card border border-border/50 rounded-2xl shadow-sm p-8 space-y-6">
        
        <div className="flex flex-col items-center space-y-2 text-center pb-4">
          <div className="w-12 h-12 bg-primary/10 rounded-xl flex items-center justify-center mb-2">
            <Activity className="w-6 h-6 text-primary" />
          </div>
          <h1 className="text-2xl font-bold text-foreground">Welcome to VitalGuard</h1>
          <p className="text-sm text-muted-foreground">
            {isLogin ? "Enter your credentials to monitor patients" : "Create an account to get started"}
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1">
            <label className="text-sm font-medium">Email</label>
            <input 
              type="email" 
              required 
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-3 py-2 bg-secondary/50 border border-border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 transition-all"
              placeholder="name@example.com"
            />
          </div>

          <div className="space-y-1">
            <label className="text-sm font-medium">Password</label>
            <input 
              type="password" 
              required 
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-3 py-2 bg-secondary/50 border border-border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 transition-all"
              placeholder="••••••••"
            />
          </div>

          {/* Show role selection on both for safety when localStorage is clear, per my previous thought */}
          <div className="space-y-1 pb-2">
            <label className="text-sm font-medium">Select Role</label>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => setRoleSelection("user")}
                className={`py-2 px-4 rounded-lg text-sm font-medium transition-colors ${roleSelection === "user" ? "bg-primary text-primary-foreground" : "bg-secondary text-muted-foreground hover:bg-secondary/80"}`}
              >
                Patient
              </button>
              <button
                type="button"
                onClick={() => setRoleSelection("admin")}
                className={`py-2 px-4 rounded-lg text-sm font-medium transition-colors ${roleSelection === "admin" ? "bg-primary text-primary-foreground" : "bg-secondary text-muted-foreground hover:bg-secondary/80"}`}
              >
                Doctor / Admin
              </button>
            </div>
          </div>

          <button 
            type="submit" 
            disabled={loading}
            className="w-full py-2.5 bg-primary hover:bg-primary/90 text-primary-foreground rounded-lg text-sm font-medium transition-colors flex justify-center items-center"
          >
            {loading ? (
              <span className="w-5 h-5 border-2 border-primary-foreground/30 border-t-primary-foreground rounded-full animate-spin" />
            ) : (
              isLogin ? "Sign In" : "Create Account"
            )}
          </button>
        </form>

        <div className="pt-4 text-center">
          <button 
            onClick={() => setIsLogin(!isLogin)}
            className="text-sm text-primary hover:underline"
          >
            {isLogin ? "Don't have an account? Sign up" : "Already have an account? Sign in"}
          </button>
        </div>
      </div>
    </div>
  );
};

export default Auth;
