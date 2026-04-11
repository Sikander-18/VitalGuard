import { Activity } from "lucide-react";
import { Link } from "react-router-dom";
import Navbar from "@/components/vitalguard/Navbar";

const Index = () => (
  <div className="min-h-screen bg-background">
    <Navbar />
    <main className="container flex flex-col items-center justify-center min-h-[calc(100vh-3.5rem)] text-center py-20">
      <div className="w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center mb-6">
        <Activity className="w-8 h-8 text-primary" />
      </div>
      <h1 className="text-4xl font-bold text-foreground mb-3">VitalGuard</h1>
      <p className="text-lg text-muted-foreground mb-8 max-w-md">
        Real-time health monitoring & emergency response platform
      </p>
      <div className="flex gap-3">
        <Link to="/user" className="px-6 py-3 rounded-xl bg-primary text-primary-foreground font-medium hover:opacity-90 transition-opacity">
          Patient Dashboard
        </Link>
        <Link to="/admin" className="px-6 py-3 rounded-xl bg-secondary text-secondary-foreground font-medium hover:bg-accent transition-colors">
          Admin Dashboard
        </Link>
      </div>
    </main>
  </div>
);

export default Index;
