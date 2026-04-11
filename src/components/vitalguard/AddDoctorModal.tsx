import { useState } from "react";
import { X } from "lucide-react";
import type { Doctor } from "@/data/mockData";

interface AddDoctorModalProps {
  open: boolean;
  onClose: () => void;
  onSave: (doctor: Doctor) => void;
}

const AddDoctorModal = ({ open, onClose, onSave }: AddDoctorModalProps) => {
  const [name, setName] = useState("");
  const [specialization, setSpecialization] = useState("");
  const [availability, setAvailability] = useState<"Available" | "Busy">("Available");

  if (!open) return null;

  const handleSave = () => {
    if (!name.trim() || !specialization.trim()) return;
    onSave({
      id: `D${Date.now()}`,
      name: name.trim(),
      specialization: specialization.trim(),
      availability,
      lat: 28.615 + (Math.random() - 0.5) * 0.01,
      lng: 77.21 + (Math.random() - 0.5) * 0.01,
    });
    setName("");
    setSpecialization("");
    setAvailability("Available");
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm" onClick={onClose}>
      <div className="bg-card rounded-xl shadow-xl border border-border/50 w-full max-w-md mx-4 p-6" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-5">
          <h3 className="text-lg font-semibold text-foreground">Add Doctor</h3>
          <button onClick={onClose} className="p-1 rounded-lg hover:bg-secondary transition-colors">
            <X className="w-4 h-4 text-muted-foreground" />
          </button>
        </div>
        <div className="space-y-4">
          <div>
            <label className="text-sm font-medium text-foreground mb-1 block">Doctor Name</label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Dr. Jane Smith"
              className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/30"
            />
          </div>
          <div>
            <label className="text-sm font-medium text-foreground mb-1 block">Specialization</label>
            <input
              value={specialization}
              onChange={(e) => setSpecialization(e.target.value)}
              placeholder="Cardiologist"
              className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary/30"
            />
          </div>
          <div>
            <label className="text-sm font-medium text-foreground mb-1 block">Availability</label>
            <select
              value={availability}
              onChange={(e) => setAvailability(e.target.value as "Available" | "Busy")}
              className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary/30"
            >
              <option value="Available">Available</option>
              <option value="Busy">Busy</option>
            </select>
          </div>
        </div>
        <div className="flex gap-3 mt-6">
          <button onClick={onClose} className="flex-1 px-4 py-2 rounded-lg border border-border text-sm font-medium text-foreground hover:bg-secondary transition-colors">
            Cancel
          </button>
          <button onClick={handleSave} disabled={!name.trim() || !specialization.trim()} className="flex-1 px-4 py-2 rounded-lg bg-primary text-primary-foreground text-sm font-medium hover:opacity-90 transition-opacity disabled:opacity-50">
            Save
          </button>
        </div>
      </div>
    </div>
  );
};

export default AddDoctorModal;
