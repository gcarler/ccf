import codecs
import re

with codecs.open("frontend/src/app/crm/scanner/page.tsx", "r", "utf-8") as f:
    c = f.read()

# 1. Update states and imports
import_old = "import { QrCode, ShieldCheck, Zap, RefreshCcw, UserCheck, Link2, Users } from 'lucide-react';"
import_new = "import { QrCode, ShieldCheck, Zap, RefreshCcw, UserCheck, Link2, Users, Calendar } from 'lucide-react';\nimport { useAuth } from '@/context/AuthContext';\nimport { useEffect } from 'react';"
c = c.replace(import_old, import_new)

state_old = """    const [manualToken, setManualToken] = useState('');
    const [loading, setLoading] = useState(false);"""
state_new = """    const [manualToken, setManualToken] = useState('');
    const [loading, setLoading] = useState(false);
    const { token: authToken } = useAuth();
    const [events, setEvents] = useState<any[]>([]);
    const [selectedEventId, setSelectedEventId] = useState<string>('');

    useEffect(() => {
        if (authToken) {
            apiFetch<any[]>('/crm/events/', { token: authToken }).then(data => {
                setEvents(data);
            }).catch(() => {});
        }
    }, [authToken]);"""
c = c.replace(state_old, state_new)

# 2. Update handleScan to use selectedEventId and authToken
func_old = """    const handleScan = async (token: string) => {
        if (!token) return;
        setLoading(true);
        setIsScanning(false);
        try {
            const data = await apiFetch(`/crm/scanner/validate/${token}`, { method: 'POST' });"""

func_new = """    const handleScan = async (tokenStr: string) => {
        if (!tokenStr) return;
        setLoading(true);
        setIsScanning(false);
        try {
            const endpoint = selectedEventId ? `/crm/scanner/validate/${tokenStr}?event_id=${selectedEventId}` : `/crm/scanner/validate/${tokenStr}`;
            const data = await apiFetch(endpoint, { method: 'POST', token: authToken });"""
c = c.replace(func_old, func_new)

# 3. Add Event Selector to the UI
ui_old = """                                    <p className="text-white font-bold text-lg mb-2">Buscando Código...</p>
                                    <p className="text-slate-500 text-xs">Apunta la cámara al código QR del feligrés</p>
                                </div>

                                {/* Manual Input Toggle (Simulation) */}"""
ui_new = """                                    <p className="text-white font-bold text-lg mb-2">Buscando Código...</p>
                                    <p className="text-slate-500 text-xs">Apunta la cámara al código QR del feligrés</p>
                                </div>
                                
                                <div className="w-full relative mt-4">
                                    <select 
                                        value={selectedEventId} 
                                        onChange={e => setSelectedEventId(e.target.value)}
                                        className="w-full bg-white/5 border border-white/10 rounded-2xl px-6 py-3 text-white text-xs font-bold focus:outline-none focus:border-primary transition-all appearance-none text-center"
                                    >
                                        <option value="" className="bg-slate-900">-- Solo Validar (Sin registrar asistencia) --</option>
                                        {events.map(ev => <option key={ev.id} value={ev.id} className="bg-slate-900">{ev.name}</option>)}
                                    </select>
                                    <div className="absolute right-4 top-1/2 -translate-y-1/2 pointer-events-none text-white/50">
                                        <Calendar size={14} />
                                    </div>
                                </div>

                                {/* Manual Input Toggle (Simulation) */}"""
c = c.replace(ui_old, ui_new)

with codecs.open("frontend/src/app/crm/scanner/page.tsx", "w", "utf-8") as f:
    f.write(c)

print("Frontend scanner updated")
