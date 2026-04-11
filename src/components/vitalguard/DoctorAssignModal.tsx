import { X, Stethoscope, Check } from "lucide-react";
import { useState } from "react";
import type { Doctor, User } from "@/data/mockData";

interface DoctorAssignModalProps {
  open: boolean;
  onClose: () => void;
  doctors: Doctor[];
  user: User | null;
}

const DoctorAssignModal = ({ open, onClose, doctors, user }: DoctorAssignModalProps) => {
  const [selectedDoc, setSelectedDoc] = useState<string | null>(null);
  const [assigned, setAssigned] = useState(false);

  if (!open || !user) return null;

  const handleAssign = () => {
    setAssigned(true);
    setTimeout(() => {
      setAssigned(false);
      setSelectedDoc(null);
      onClose();
    }, 1500);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-foreground/20 backdrop-blur-sm" onClick={onClose}>
      <div className="bg-card rounded-2xl shadow-xl border border-border/50 w-full max-w-md mx-4 p-6" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold text-foreground text-lg">Appoint Doctor</h3>
          <button onClick={onClose} className="w-8 h-8 rounded-lg flex items-center justify-center hover:bg-secondary transition-colors">
            <X className="w-4 h-4 text-muted-foreground" />
          </button>
        </div>
        <p className="text-sm text-muted-foreground mb-4">
          Assign a doctor to <strong>{user.name}</strong> ({user.id})
        </p>

        {assigned ? (
          <div className="flex flex-col items-center py-8 gap-3">
            <div className="w-12 h-12 rounded-full status-normal-solid flex items-center justify-center">
              <Check className="w-6 h-6" />
            </div>
            <p className="text-sm font-medium text-foreground">Doctor assigned successfully!</p>
          </div>
        ) : (
          <>
            <div className="space-y-2 max-h-64 overflow-y-auto mb-4">
              {doctors.map((doc) => (
                <button
                  key={doc.id}
                  onClick={() => setSelectedDoc(doc.id)}
                  className={`w-full flex items-center gap-3 p-3 rounded-lg text-left transition-colors ${
                    selectedDoc === doc.id ? "bg-primary/10 border border-primary/20" : "bg-secondary/50 hover:bg-secondary"
                  }`}
                >
                  <Stethoscope className="w-4 h-4 text-primary shrink-0" />
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-foreground">{doc.name}</p>
                    <p className="text-xs text-muted-foreground">{doc.specialization} • {doc.availability}</p>
                  </div>
                  {selectedDoc === doc.id && <Check className="w-4 h-4 text-primary shrink-0" />}
                </button>
              ))}
            </div>
            <button
              disabled={!selectedDoc}
              onClick={handleAssign}
              className="w-full py-2.5 rounded-lg bg-primary text-primary-foreground font-medium text-sm hover:opacity-90 transition-opacity disabled:opacity-40"
            >
              Assign Doctor
            </button>
          </>
        )}
      </div>
    </div>
  );
};

export default DoctorAssignModal;
