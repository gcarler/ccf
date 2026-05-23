const fs = require('fs');

let c = fs.readFileSync('frontend/src/app/crm/members/page.tsx', 'utf8');

const newRoles = `const ROLES = [
    'Todos', 'Apóstol', 'Profeta', 'Evangelista', 'Pastor', 'Maestro',
    'Ministro de Culto', 'Líder', 'Servidor', 'Miembro Bautizado',
    'Asistente', 'Visitante Servicios', 'Visitante Faro en Casa', 'Visitante Online'
];`;
c = c.replace(/const ROLES = \[[^]*?\];/, newRoles);

const newColors = `const ROLE_COLORS: Record<string, string> = {
    'Apóstol': 'text-purple-600 bg-purple-50 dark:bg-purple-900/20 dark:text-purple-400',
    'Profeta': 'text-indigo-600 bg-indigo-50 dark:bg-indigo-900/20 dark:text-indigo-400',
    'Evangelista': 'text-orange-600 bg-orange-50 dark:bg-orange-900/20 dark:text-orange-400',
    'Pastor': 'text-blue-600 bg-blue-50 dark:bg-blue-900/20 dark:text-blue-400',
    'Maestro': 'text-teal-600 bg-teal-50 dark:bg-teal-900/20 dark:text-teal-400',
    'Ministro de Culto': 'text-rose-600 bg-rose-50 dark:bg-rose-900/20 dark:text-rose-400',
    'Líder': 'text-amber-600 bg-amber-50 dark:bg-amber-900/20 dark:text-amber-400',
    'Servidor': 'text-emerald-600 bg-emerald-50 dark:bg-emerald-900/20 dark:text-emerald-400',
    'Miembro Bautizado': 'text-sky-600 bg-sky-50 dark:bg-sky-900/20 dark:text-sky-400',
    'Asistente': 'text-violet-600 bg-violet-50 dark:bg-violet-900/20 dark:text-violet-400',
    'Visitante Servicios': 'text-slate-600 bg-slate-100 dark:bg-white/10 dark:text-slate-400',
    'Visitante Faro en Casa': 'text-cyan-600 bg-cyan-50 dark:bg-cyan-900/20 dark:text-cyan-400',
    'Visitante Online': 'text-fuchsia-600 bg-fuchsia-50 dark:bg-fuchsia-900/20 dark:text-fuchsia-400',
};`;
c = c.replace(/const ROLE_COLORS: Record<string, string> = \{[^]*?\};/, newColors);

c = c.replace(/Filtrar por Ministerio/g, 'Filtrar por Cargo / Rol');

fs.writeFileSync('frontend/src/app/crm/members/page.tsx', c, 'utf8');

let c2 = fs.readFileSync('frontend/src/app/crm/members/[id]/page.tsx', 'utf8');
c2 = c2.replace(/{ label: 'Ministerio', value: member.church_role, icon: ShieldCheck },/g, "{ label: 'Rol en Ministerio', value: member.church_role, icon: ShieldCheck },");
c2 = c2.replace(/{ label: 'Ministerio', value: member.church_role, icon: Star },/g, "{ label: 'Rol en la Iglesia', value: member.church_role, icon: Star },");
fs.writeFileSync('frontend/src/app/crm/members/[id]/page.tsx', c2, 'utf8');
