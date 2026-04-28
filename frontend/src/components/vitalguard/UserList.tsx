import { ShieldCheck, AlertTriangle, AlertOctagon } from "lucide-react";
import type { User, RiskLevel } from "@/data/mockData";

interface UserListProps {
  users: User[];
  selectedId?: string;
  onSelect: (user: User) => void;
}

const riskOrder: Record<RiskLevel, number> = { CRITICAL: 0, FUTURE_ALERT: 1, NORMAL: 2 };

const riskIcon = {
  NORMAL: { icon: ShieldCheck, classes: "status-normal" },
  FUTURE_ALERT: { icon: AlertTriangle, classes: "status-warning" },
  CRITICAL: { icon: AlertOctagon, classes: "status-critical" },
};

const UserList = ({ users, selectedId, onSelect }: UserListProps) => {
  const sorted = [...users].sort((a, b) => riskOrder[a.risk] - riskOrder[b.risk]);
  return (
    <div>
      <h3 className="font-semibold text-foreground mb-3 text-sm">Patients</h3>
      <div className="space-y-1.5">
        {sorted.map((user) => {
          const cfg = riskIcon[user.risk];
          const Icon = cfg.icon;
          return (
            <button
              key={user.id}
              onClick={() => onSelect(user)}
              className={`w-full flex items-center gap-3 p-3 rounded-lg text-left transition-colors ${
                selectedId === user.id ? "bg-primary/10 border border-primary/20" : "hover:bg-secondary"
              }`}
            >
              <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 ${cfg.classes}`}>
                <Icon className="w-4 h-4" />
              </div>
              <div className="min-w-0">
                <p className="text-sm font-medium text-foreground truncate">{user.name}</p>
                <p className="text-xs text-muted-foreground">{user.id} • {user.risk.replace("_", " ")}</p>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
};

export default UserList;
