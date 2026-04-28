import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { createUserWithEmailAndPassword, signInWithEmailAndPassword, GoogleAuthProvider, signInWithPopup } from "firebase/auth";
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
        let localRole = localStorage.getItem("role") as "user" | "admin" | null;
        if (!localRole) {
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

  const handleGoogleAuth = async () => {
    setLoading(true);
    try {
      const provider = new GoogleAuthProvider();
      await signInWithPopup(auth, provider);
      
      let localRole = localStorage.getItem("role") as "user" | "admin" | null;
      if (!localRole) {
        localRole = roleSelection; // Use the selected radio/button if not in localStorage
      }
      setRole(localRole);
      
      toast({ title: `Successfully ${isLogin ? 'logged in' : 'signed up'} with Google` });

      if (localRole === "admin") {
        navigate("/admin");
      } else {
        navigate(isLogin ? "/user" : "/onboarding");
      }
    } catch (error: any) {
      toast({ 
        title: "Google Authentication Failed", 
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

        <div className="relative">
          <div className="absolute inset-0 flex items-center">
            <span className="w-full border-t border-border/50" />
          </div>
          <div className="relative flex justify-center text-xs uppercase">
            <span className="bg-card px-2 text-muted-foreground">Or continue with</span>
          </div>
        </div>

        <button
          type="button"
          onClick={handleGoogleAuth}
          disabled={loading}
          className="w-full flex items-center justify-center space-x-2 py-2.5 bg-secondary/50 border border-border hover:bg-secondary/80 text-foreground rounded-lg text-sm font-medium transition-colors"
        >
          <svg className="w-5 h-5" viewBox="0 0 48 48">
            <path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/>
            <path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/>
            <path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/>
            <path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/>
            <path fill="none" d="M0 0h48v48H0z"/>
          </svg>
          <span>Google</span>
        </button>

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
