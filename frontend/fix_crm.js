const fs = require('fs');
let content = fs.readFileSync('src/app/crm/page.tsx', 'utf8');

const replacement1 =     return (
        <div className="p-8 lg:p-12 space-y-10 w-full animate-in fade-in duration-500">
            {/* Native Workspace Header */}
            <header className="flex flex-col md:flex-row md:items-center justify-between gap-6">
                <div>
                    <div className="flex items-center gap-2 mb-2">
                        <span className="text-[10px] font-black uppercase tracking-widest text-[hsl(var(--primary))] px-2.5 py-1 bg-[hsl(var(--primary)/0.1)] rounded-md">CRM Pastoral</span>
                    </div>
                    <h1 className="text-3xl font-black text-[hsl(var(--text-primary))] tracking-tight flex items-center gap-3">
                        Comunidad CCF
                    </h1>
                    <p className="text-[hsl(var(--text-secondary))] font-medium mt-1">Supervisa consolidación, mensajería y seguimiento pastoral en un solo tablero.</p>
                </div>
                <div className="flex flex-wrap items-center gap-3">
                    <button className="flex items-center gap-2 px-6 py-3.5 bg-[hsl(var(--primary))] text-[hsl(var(--bg-primary))] rounded-2xl text-xs font-bold hover:opacity-90 transition-all shadow-[0_4px_20px_theme(colors.blue.500/0.3)] active:scale-95">
                        <Plus size={16} /> Registrar Miembro
                    </button>
                </div>
            </header>

            <div className="space-y-8">;

const replacement2 =             </div>
        </div>
    );;

let lines = content.split('\r\n');
if (lines.length < 2) lines = content.split('\n');

const idx1 = lines.findIndex(l => l.includes('<CrmDetailShell'));
const idx2 = lines.findIndex(l => l.includes('<div className="p-6 space-y-8">'));

if (idx1 !== -1 && idx2 !== -1) {
    lines.splice(idx1 - 1, (idx2 - (idx1 - 1)) + 1, ...replacement1.split('\n'));
}

const idx3 = lines.findIndex(l => l.includes('</CrmDetailShell>'));
if (idx3 !== -1) {
    lines.splice(idx3 - 2, 4, ...replacement2.split('\n'));
}

fs.writeFileSync('src/app/crm/page.tsx', lines.join('\n'));
console.log('Script completed');
