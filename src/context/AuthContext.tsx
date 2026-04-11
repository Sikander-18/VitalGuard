import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { User, onAuthStateChanged, signOut as firebaseSignOut } from "firebase/auth";
import { auth } from "@/config/firebase";

interface AuthContextType {
  user: User | null;
  loading: boolean;
  role: "user" | "admin" | null;
  setRole: (role: "user" | "admin" | null) => void;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  loading: true,
  role: null,
  setRole: () => {},
  signOut: async () => {},
});

export const useAuth = () => useContext(AuthContext);

export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [role, setRoleState] = useState<"user" | "admin" | null>(
    (localStorage.getItem("role") as "user" | "admin" | null) || null
  );

  const setRole = (newRole: "user" | "admin" | null) => {
    if (newRole) {
      localStorage.setItem("role", newRole);
    } else {
      localStorage.removeItem("role");
    }
    setRoleState(newRole);
  };

  const signOut = async () => {
    await firebaseSignOut(auth);
    setRole(null);
    localStorage.removeItem("onboarding_done");
  };

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, (currentUser) => {
      setUser(currentUser);
      setLoading(false);
    });

    return unsubscribe;
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, role, setRole, signOut }}>
      {!loading && children}
    </AuthContext.Provider>
  );
};
