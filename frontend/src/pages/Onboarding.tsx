import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { useToast } from "@/hooks/use-toast";
import { Plus, Trash2, MapPin, CheckCircle2 } from "lucide-react";

const Onboarding = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const { toast } = useToast();
  
  const [loading, setLoading] = useState(false);
  const [formData, setFormData] = useState({
    name: "",
    age: "",
    gender: "Male"
  });
  
  const [conditions, setConditions] = useState<{ [key: string]: boolean }>({
    "Heart Disease": false,
    "Diabetes": false,
    "Hypertension": false,
    "Other": false,
    "None": false
  });
  const [otherCondition, setOtherCondition] = useState("");
  
  const [familyConditions, setFamilyConditions] = useState<{ [key: string]: boolean }>({
    "Heart Disease": false,
    "Diabetes": false,
    "Hypertension": false,
    "Other": false,
    "None": false
  });
  const [familyOtherCondition, setFamilyOtherCondition] = useState("");
  
  const [baselines, setBaselines] = useState({
    heartRate: "",
    bloodPressure: "",
    spo2: ""
  });
  
  const [contacts, setContacts] = useState([{ name: "", phone: "" }]);
  const [location, setLocation] = useState<{ lat: number; lng: number } | null>(null);
  const [locating, setLocating] = useState(false);

  useEffect(() => {
    // Attempt to get location automatically on mount
    getLocation();
  }, []);

  const getLocation = () => {
    setLocating(true);
    if ("geolocation" in navigator) {
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          setLocation({
            lat: pos.coords.latitude,
            lng: pos.coords.longitude
          });
          setLocating(false);
        },
        (error) => {
          console.error(error);
          setLocating(false);
        }
      );
    } else {
      setLocating(false);
    }
  };

  const handleContactChange = (index: number, field: "name" | "phone", value: string) => {
    const newContacts = [...contacts];
    newContacts[index][field] = value;
    setContacts(newContacts);
  };

  const addContact = () => {
    setContacts([...contacts, { name: "", phone: "" }]);
  };

  const removeContact = (index: number) => {
    setContacts(contacts.filter((_, i) => i !== index));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    const lat = location?.lat || 0;
    const lng = location?.lng || 0;

    // Validate family history (required)
    const familyAnySelected = Object.values(familyConditions).some(v => v);
    if (!familyAnySelected) {
      toast({ title: "Family Medical History is required", variant: "destructive" });
      setLoading(false);
      return;
    }

    const personalHistory = Object.entries(conditions)
      .filter(([k, v]) => v && k !== "Other" && k !== "None")
      .map(([k]) => k);
    if (conditions["Other"] && otherCondition) personalHistory.push(otherCondition);

    const familyHistory = Object.entries(familyConditions)
      .filter(([k, v]) => v && k !== "Other" && k !== "None")
      .map(([k]) => k);
    if (familyConditions["Other"] && familyOtherCondition) familyHistory.push(familyOtherCondition);

    const payload = {
      id: user?.uid || "mock-uid-" + Math.floor(Math.random()*1000), 
      name: formData.name,
      age: parseInt(formData.age) || 0,
      gender: formData.gender,
      phone: contacts[0]?.phone || "0000000000", 
      location_lat: lat,
      location_lng: lng,
      emergency_contacts: JSON.stringify(contacts),
      medical_history: personalHistory.join(", "),
      family_medical_history: familyHistory.join(", ")
    };

    try {
      // POST to backend
      const res = await fetch("http://localhost:8000/users/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      
      if (!res.ok) {
        throw new Error("Failed to register user to backend");
      }

      localStorage.setItem("onboarding_done", "true");
      toast({ title: "Enrollment complete!" });
      navigate("/user");
    } catch (err: any) {
      toast({ 
        title: "Enrollment Error", 
        description: err.message, 
        variant: "destructive" 
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background py-8 px-4 flex justify-center">
      <div className="max-w-2xl w-full">
        
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-foreground">Complete Your Profile</h1>
          <p className="text-muted-foreground mt-2">We need some medical background to provide accurate monitoring.</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-8 bg-card border border-border/50 p-6 sm:p-8 rounded-2xl shadow-sm">
          
          {/* Section 1: Basic Info */}
          <section className="space-y-4">
            <h2 className="text-xl font-semibold border-b pb-2">1. Basic Information</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-1">
                <label className="text-sm font-medium">Full Name</label>
                <input required value={formData.name} onChange={e => setFormData({...formData, name: e.target.value})} className="w-full px-3 py-2 bg-secondary/50 border rounded-lg focus:ring-2 focus:ring-primary/20 outline-none" />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="text-sm font-medium">Age</label>
                  <input required type="number" value={formData.age} onChange={e => setFormData({...formData, age: e.target.value})} className="w-full px-3 py-2 bg-secondary/50 border rounded-lg focus:ring-2 focus:ring-primary/20 outline-none" />
                </div>
                <div className="space-y-1">
                  <label className="text-sm font-medium">Gender</label>
                  <select value={formData.gender} onChange={e => setFormData({...formData, gender: e.target.value})} className="w-full px-3 py-2 bg-secondary/50 border rounded-lg focus:ring-2 focus:ring-primary/20 outline-none">
                    <option>Male</option>
                    <option>Female</option>
                    <option>Other</option>
                  </select>
                </div>
              </div>
            </div>
          </section>

          {/* Section 2: Medical Info */}
          <section className="space-y-4">
            <h2 className="text-xl font-semibold border-b pb-2">2. Medical History</h2>
            <div className="grid grid-cols-2 gap-3">
              {Object.keys(conditions).map(key => (
                <label key={key} className="flex items-center space-x-2 p-3 border rounded-lg hover:bg-secondary/20 cursor-pointer transition-colors">
                  <input 
                    type="checkbox" 
                    checked={conditions[key]}
                    onChange={(e) => {
                      if (key === "None" && e.target.checked) {
                        setConditions({ "Heart Disease": false, "Diabetes": false, "Hypertension": false, "Other": false, "None": true });
                        setOtherCondition("");
                      } else {
                        setConditions(prev => ({ ...prev, [key]: e.target.checked, None: false }));
                      }
                    }}
                    className="w-4 h-4 text-primary rounded" 
                  />
                  <span className="text-sm border-none">{key}</span>
                </label>
              ))}
            </div>
            {conditions["Other"] && (
              <div className="mt-2 space-y-1">
                <label className="text-xs font-medium text-muted-foreground">Please specify</label>
                <input 
                  required
                  value={otherCondition}
                  onChange={e => setOtherCondition(e.target.value)}
                  placeholder="Enter other medical conditions"
                  className="w-full px-3 py-2 bg-secondary/50 border rounded-lg focus:ring-2 focus:ring-primary/20 outline-none text-sm"
                />
              </div>
            )}
          </section>

          {/* Section 2b: Family Medical Info */}
          <section className="space-y-4">
            <h2 className="text-xl font-semibold border-b pb-2 flex items-center gap-2">
              2b. Family Medical History <span className="text-red-500 text-xs">* Required</span>
            </h2>
            <div className="grid grid-cols-2 gap-3">
              {Object.keys(familyConditions).map(key => (
                <label key={key} className="flex items-center space-x-2 p-3 border rounded-lg hover:bg-secondary/20 cursor-pointer transition-colors">
                  <input 
                    type="checkbox" 
                    checked={familyConditions[key]}
                    onChange={(e) => {
                      if (key === "None" && e.target.checked) {
                        setFamilyConditions({ "Heart Disease": false, "Diabetes": false, "Hypertension": false, "Other": false, "None": true });
                        setFamilyOtherCondition("");
                      } else {
                        setFamilyConditions(prev => ({ ...prev, [key]: e.target.checked, None: false }));
                      }
                    }}
                    className="w-4 h-4 text-primary rounded" 
                  />
                  <span className="text-sm border-none">{key}</span>
                </label>
              ))}
            </div>
            {familyConditions["Other"] && (
              <div className="mt-2 space-y-1">
                <label className="text-xs font-medium text-muted-foreground">Please specify</label>
                <input 
                  required
                  value={familyOtherCondition}
                  onChange={e => setFamilyOtherCondition(e.target.value)}
                  placeholder="Enter other family medical conditions"
                  className="w-full px-3 py-2 bg-secondary/50 border rounded-lg focus:ring-2 focus:ring-primary/20 outline-none text-sm"
                />
              </div>
            )}
          </section>

          {/* Section 3: Baseline Vitals */}
          <section className="space-y-4">
            <h2 className="text-xl font-semibold border-b pb-2">3. Baseline Vitals</h2>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="space-y-1">
                <label className="text-sm font-medium">Normal Heart Rate</label>
                <input placeholder="e.g. 70 bpm" value={baselines.heartRate} onChange={e => setBaselines({...baselines, heartRate: e.target.value})} className="w-full px-3 py-2 bg-secondary/50 border rounded-lg focus:ring-2 focus:ring-primary/20 outline-none" />
              </div>
              <div className="space-y-1">
                <label className="text-sm font-medium">Normal BP</label>
                <input placeholder="e.g. 120/80" value={baselines.bloodPressure} onChange={e => setBaselines({...baselines, bloodPressure: e.target.value})} className="w-full px-3 py-2 bg-secondary/50 border rounded-lg focus:ring-2 focus:ring-primary/20 outline-none" />
              </div>
              <div className="space-y-1">
                <label className="text-sm font-medium">Normal SpO2</label>
                <input placeholder="e.g. 98%" value={baselines.spo2} onChange={e => setBaselines({...baselines, spo2: e.target.value})} className="w-full px-3 py-2 bg-secondary/50 border rounded-lg focus:ring-2 focus:ring-primary/20 outline-none" />
              </div>
            </div>
          </section>

          {/* Section 4: Emergency Contacts */}
          <section className="space-y-4">
            <h2 className="text-xl font-semibold border-b pb-2">4. Emergency Contacts</h2>
            {contacts.map((contact, index) => (
              <div key={index} className="flex gap-4 items-start">
                <div className="flex-1 space-y-1">
                  <input placeholder="Contact Name" value={contact.name} onChange={e => handleContactChange(index, "name", e.target.value)} required className="w-full px-3 py-2 bg-secondary/50 border rounded-lg focus:ring-2 focus:ring-primary/20 outline-none" />
                </div>
                <div className="flex-1 space-y-1">
                  <input placeholder="Phone Number" value={contact.phone} onChange={e => handleContactChange(index, "phone", e.target.value)} required className="w-full px-3 py-2 bg-secondary/50 border rounded-lg focus:ring-2 focus:ring-primary/20 outline-none" />
                </div>
                {contacts.length > 1 && (
                  <button type="button" onClick={() => removeContact(index)} className="p-2.5 mt-0.5 text-red-500 hover:bg-red-500/10 rounded-lg transition-colors">
                    <Trash2 className="w-5 h-5" />
                  </button>
                )}
              </div>
            ))}
            <button type="button" onClick={addContact} className="text-sm font-medium text-primary flex flex-row items-center gap-1 hover:underline">
              <Plus className="w-4 h-4" /> Add another contact
            </button>
          </section>

          {/* Section 5: Report Upload */}
          <section className="space-y-4">
            <h2 className="text-xl font-semibold border-b pb-2">5. Medical Reports <span className="text-muted-foreground font-normal text-sm">(Optional)</span></h2>
            <div className="border-2 border-dashed border-border rounded-lg p-6 flex justify-center items-center bg-secondary/20">
              <input type="file" accept=".pdf,image/*" className="text-sm text-muted-foreground file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-primary/10 file:text-primary hover:file:bg-primary/20" />
            </div>
          </section>

          {/* Section 6: Location */}
          <section className="space-y-4">
            <h2 className="text-xl font-semibold border-b pb-2 flex items-center justify-between">
              <span>6. Default Location</span>
              {location && <span className="text-sm font-normal text-green-500 flex items-center gap-1"><CheckCircle2 className="w-4 h-4"/> Captured</span>}
            </h2>
            <div className="flex items-center gap-4">
              <button type="button" onClick={getLocation} disabled={locating} className="flex items-center gap-2 px-4 py-2 bg-secondary text-foreground hover:bg-secondary/80 rounded-lg text-sm font-medium transition-colors">
                <MapPin className="w-4 h-4" /> 
                {locating ? "Locating..." : location ? "Update Location" : "Get Current Location"}
              </button>
              {location && <p className="text-xs text-muted-foreground">Lat: {location.lat.toFixed(4)}, Lng: {location.lng.toFixed(4)}</p>}
            </div>
          </section>

          <button type="submit" disabled={loading} className="w-full py-3 bg-primary hover:bg-primary/90 text-primary-foreground rounded-lg font-medium transition-colors flex justify-center items-center mt-4">
            {loading ? <span className="w-5 h-5 border-2 border-primary-foreground/30 border-t-primary-foreground rounded-full animate-spin" /> : "Complete Enrollment"}
          </button>
        </form>

      </div>
    </div>
  );
};

export default Onboarding;
