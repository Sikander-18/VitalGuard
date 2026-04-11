import { UserPlus, Stethoscope } from "lucide-react";
import type { Doctor } from "@/data/mockData";

interface DoctorListProps {
  doctors: Doctor[];
  onAddDoctor?: () => void;
}

const availColor = {
  Available: "status-normal",
  Busy: "status-warning",
  "Off-duty": "text-muted-foreground bg-secondary",
};

const DoctorList = ({ doctors, onAddDoctor }: DoctorListProps) => (
  <div>
    <div className="flex items-center justify-between mb-3">
      <h3 className="font-semibold text-foreground text-sm">Doctors</h3>
      <button
        onClick={onAddDoctor}
        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-primary text-primary-foreground text-xs font-medium hover:opacity-90 transition-opacity"
      >
        <UserPlus className="w-3.5 h-3.5" />
        Add
      </button>
    </div>
    <div className="space-y-1.5">
      {doctors.map((doc) => (
        <div key={doc.id} className="flex items-center gap-3 p-3 rounded-lg bg-secondary/50">
          <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
            <Stethoscope className="w-4 h-4 text-primary" />
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-sm font-medium text-foreground truncate">{doc.name}</p>
            <p className="text-xs text-muted-foreground">{doc.specialization}</p>
          </div>
          <span className={`text-xs px-2 py-1 rounded-md font-medium ${availColor[doc.availability]}`}>
            {doc.availability}
          </span>
        </div>
      ))}
    </div>
  </div>
);

export default DoctorList;
