"use client";

import React, { useState, useEffect, useCallback } from 'react';
import { 
    Settings, 
    Shield, 
    Zap, 
    Database, 
    Server, 
    Activity, 
    Cpu, 
    Globe, 
    Lock, 
    Smartphone, 
    Mail, 
    Layers,
    ChevronRight,
    CheckCircle2,
    AlertTriangle,
    RefreshCw,
    ToggleLeft,
    ToggleRight,
    Loader2
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { useToast } from '@/context/ToastContext';
import { apiFetch } from '@/lib/http';
import { apiUrl } from '@/lib/api';
import AdminShell from '@/components/admin/AdminShell';
import AdminHero from '@/components/admin/AdminHero';
import WorkspaceLayout from '@/components/WorkspaceLayout';
import { useRouter } from 'next/navigation';
import clsx from 'clsx';

export default function SystemSettings() {
    const { token, isAuthenticated } = useAuth();
    const router = useRouter();
    const { addToast } = useToast();
    const [config, setConfig] = useState<any>(null);
    const [auditEvents, setAuditEvents] = useState<any[]>([]);
    const [auditSummary, setAuditSummary] = useState<any>(null);
    const [auditAnomalies, setAuditAnomalies] = useState<any>(null);
    const [incidents, setIncidents] = useState<any[]>([]);
    const [incidentsSummary, setIncidentsSummary] = useState<any>(null);
    const [slaTargets, setSlaTargets] = useState<{ mtta: number; mttr: number }>({ mtta: 60, mttr: 240 });
    const [incidentTrends, setIncidentTrends] = useState<any[]>([]);
    const [incidentNotifications, setIncidentNotifications] = useState<any[]>([]);
    const [incidentStatsWindow, setIncidentStatsWindow] = useState<'weekly' | 'monthly'>('weekly');
    const [incidentStats, setIncidentStats] = useState<any>(null);
    const [complianceHistory, setComplianceHistory] = useState<any[]>([]);
    const [compareSnapshotIds, setCompareSnapshotIds] = useState<{ from: string; to: string }>({ from: '', to: '' });
    const [compareResult, setCompareResult] = useState<any>(null);
    const [historyRetentionDays, setHistoryRetentionDays] = useState<number>(90);
    const [complianceWeeklySummary, setComplianceWeeklySummary] = useState<any[]>([]);
    const [compliancePolicy, setCompliancePolicy] = useState<any>(null);
    const [suppressionDraft, setSuppressionDraft] = useState<{ kind: string; value: string; hours: number; note: string }>({
        kind: 'severity',
        value: 'high',
        hours: 24,
        note: '',
    });
    const [loading, setLoading] = useState(true);
    const [actionLoading, setActionLoading] = useState<string | null>(null);
    const [roleScope, setRoleScope] = useState<Record<string, string>>({});
    const [auditFilters, setAuditFilters] = useState<{ action: string; feature: string; actor: string }>({
        action: '',
        feature: '',
        actor: '',
    });

    const fetchConfig = useCallback(async () => {
        if (!token) return;
        setLoading(true);
        try {
            const data = await apiFetch('/workspace/config', { token, cache: 'no-store' });
            setConfig(data || {
                features_enabled: { lms: true, crm: true, ia: true, donations: false },
                feature_rules: {
                    knowledge_graph: { rollout_percent: 100, roles_allow: [] },
                    web_vitals_dashboard: { rollout_percent: 100, roles_allow: ['admin'] },
                },
                health: { status: 'stable', latency: '42ms', uptime: '99.99%', memory: '45%' }
            });
            const audit = await apiFetch<{ events?: any[] }>('/workspace/flags/audit', {
                token,
                query: {
                    limit: 12,
                    action: auditFilters.action || undefined,
                    feature_id: auditFilters.feature || undefined,
                    actor: auditFilters.actor || undefined,
                },
                cache: 'no-store',
            });
            setAuditEvents(Array.isArray(audit?.events) ? audit.events : []);
            const summary = await apiFetch<{ summary?: any }>('/workspace/flags/audit/summary', {
                token,
                query: {
                    limit: 1000,
                    action: auditFilters.action || undefined,
                    feature_id: auditFilters.feature || undefined,
                    actor: auditFilters.actor || undefined,
                },
                cache: 'no-store',
            });
            setAuditSummary(summary?.summary || null);
            const anomalies = await apiFetch<{ anomalies?: any }>('/workspace/flags/audit/anomalies', {
                token,
                query: {
                    lookback_hours: 24,
                    actor_threshold: 10,
                    action_threshold: 20,
                    action: auditFilters.action || undefined,
                    feature_id: auditFilters.feature || undefined,
                    actor: auditFilters.actor || undefined,
                },
                cache: 'no-store',
            });
            setAuditAnomalies(anomalies?.anomalies || null);
            const incidentsResult = await apiFetch<{ incidents?: any[] }>('/workspace/flags/incidents', {
                token,
                query: { limit: 20, mtta_target_minutes: slaTargets.mtta, mttr_target_minutes: slaTargets.mttr },
                cache: 'no-store',
            });
            setIncidents(Array.isArray(incidentsResult?.incidents) ? incidentsResult.incidents : []);
            const incidentsSummaryResult = await apiFetch<{ summary?: any }>('/workspace/flags/incidents/summary', {
                token,
                query: { mtta_target_minutes: slaTargets.mtta, mttr_target_minutes: slaTargets.mttr },
                cache: 'no-store',
            });
            setIncidentsSummary(incidentsSummaryResult?.summary || null);
            const trendsResult = await apiFetch<{ rows?: any[] }>('/workspace/flags/incidents/trends', {
                token,
                query: { days: 14 },
                cache: 'no-store',
            });
            setIncidentTrends(Array.isArray(trendsResult?.rows) ? trendsResult.rows : []);
            const notificationsResult = await apiFetch<{ notifications?: any[] }>('/workspace/flags/incidents/notifications', {
                token,
                query: { limit: 20 },
                cache: 'no-store',
            });
            setIncidentNotifications(Array.isArray(notificationsResult?.notifications) ? notificationsResult.notifications : []);
            const statsResult = await apiFetch<any>('/workspace/flags/incidents/stats', {
                token,
                query: { window: incidentStatsWindow },
                cache: 'no-store',
            });
            setIncidentStats(statsResult || null);
            const historyResult = await apiFetch<{ history?: any[] }>('/workspace/flags/compliance/history', {
                token,
                query: { limit: 12 },
                cache: 'no-store',
            });
            const historyRows = Array.isArray(historyResult?.history) ? historyResult.history : [];
            setComplianceHistory(historyRows);
            if (historyRows.length >= 2) {
                const newest = historyRows[historyRows.length - 1]?.snapshot_id || '';
                const previous = historyRows[historyRows.length - 2]?.snapshot_id || '';
                setCompareSnapshotIds((prev) => ({
                    from: prev.from || String(previous),
                    to: prev.to || String(newest),
                }));
            }
            const weeklySummaryResult = await apiFetch<{ rows?: any[] }>('/workspace/flags/compliance/history/weekly-summary', {
                token,
                query: { weeks: 8 },
                cache: 'no-store',
            });
            setComplianceWeeklySummary(Array.isArray(weeklySummaryResult?.rows) ? weeklySummaryResult.rows : []);
            const compliancePolicyResult = await apiFetch<{ policy?: any; resolved?: any }>('/workspace/flags/compliance/policy', {
                token,
                cache: 'no-store',
            });
            setCompliancePolicy({
                policy: compliancePolicyResult?.policy || null,
                resolved: compliancePolicyResult?.resolved || null,
            });
        } catch (e) {
            console.error("Config fetch failed", e);
        } finally {
            setLoading(false);
        }
    }, [token, auditFilters, slaTargets, incidentStatsWindow]);

    useEffect(() => { if (isAuthenticated) fetchConfig(); }, [isAuthenticated, fetchConfig]);

    const handleCriticalAction = async (action: string, label: string) => {
        if (!confirm(`¿Estás seguro de que deseas ejecutar: ${label}? Esta acción es crítica para el sistema.`)) return;
        
        setActionLoading(action);
        setTimeout(() => {
            addToast(`${label} ejecutado con éxito`, 'success');
            setActionLoading(null);
        }, 2000);
    };

    const toggleFeature = async (key: string) => {
        if (!token || !config?.features_enabled) return;
        const current = !!config.features_enabled[key];
        const nextValue = !current;
        setActionLoading(`flag-${key}`);
        try {
            const result = await apiFetch<{ features_enabled: Record<string, boolean> }>('/workspace/flags', {
                method: 'PUT',
                token,
                body: { [key]: nextValue },
            });
            const merged = result?.features_enabled || { ...config.features_enabled, [key]: nextValue };
            setConfig({ ...config, features_enabled: merged });
            addToast(`Módulo ${key.toUpperCase()} ${nextValue ? 'Activado' : 'Desactivado'}`, 'success');
        } catch (error) {
            console.error(error);
            addToast(`No se pudo cambiar ${key.toUpperCase()}`, 'error');
        } finally {
            setActionLoading(null);
        }
    };

    const updateRule = async (featureId: string, patch: {
        rollout_percent?: number;
        roles_allow?: string[];
        users_allow?: string[];
        users_deny?: string[];
    }) => {
        if (!token) return;
        setActionLoading(`rule-${featureId}`);
        try {
            await apiFetch(`/workspace/flags/rules/${featureId}`, {
                method: 'PUT',
                token,
                body: patch,
            });
            await fetchConfig();
            addToast(`Regla de ${featureId} actualizada`, 'success');
        } catch (error) {
            console.error(error);
            addToast(`No se pudo actualizar regla ${featureId}`, 'error');
        } finally {
            setActionLoading(null);
        }
    };

    const downloadAudit = async (format: 'json' | 'csv') => {
        try {
            const params = new URLSearchParams({ format, limit: '1000' });
            if (auditFilters.action) params.set('action', auditFilters.action);
            if (auditFilters.feature) params.set('feature_id', auditFilters.feature);
            if (auditFilters.actor) params.set('actor', auditFilters.actor);

            const response = await fetch(apiUrl(`/workspace/flags/audit/export?${params.toString()}`), {
                method: 'GET',
                credentials: 'include',
                headers: {
                    Accept: format === 'csv' ? 'text/csv' : 'application/json',
                },
            });
            if (!response.ok) {
                throw new Error(`Audit export failed (${response.status})`);
            }

            const blob = await response.blob();
            const href = URL.createObjectURL(blob);
            const anchor = document.createElement('a');
            anchor.href = href;
            anchor.download = `feature_flags_audit.${format}`;
            document.body.appendChild(anchor);
            anchor.click();
            anchor.remove();
            URL.revokeObjectURL(href);
            addToast(`Auditoría exportada en ${format.toUpperCase()}`, 'success');
        } catch (error) {
            console.error(error);
            addToast('No se pudo exportar la auditoría', 'error');
        }
    };

    const scanIncidents = async () => {
        if (!token) return;
        setActionLoading('scan-incidents');
        try {
            const result = await apiFetch<{ scan?: { created?: number; updated?: number } }>('/workspace/flags/incidents/scan', {
                method: 'POST',
                token,
                query: {
                    lookback_hours: 24,
                    actor_threshold: 10,
                    action_threshold: 20,
                    action: auditFilters.action || undefined,
                    feature_id: auditFilters.feature || undefined,
                    actor: auditFilters.actor || undefined,
                },
            });
            addToast(`Incidentes escaneados (new: ${result?.scan?.created || 0}, updated: ${result?.scan?.updated || 0})`, 'success');
            await fetchConfig();
        } catch (error) {
            console.error(error);
            addToast('No se pudo escanear incidentes', 'error');
        } finally {
            setActionLoading(null);
        }
    };

    const updateIncident = async (incidentId: string, action: 'acknowledge' | 'close' | 'reopen' | 'silence') => {
        if (!token) return;
        setActionLoading(`incident-${incidentId}-${action}`);
        try {
            await apiFetch(`/workspace/flags/incidents/${incidentId}`, {
                method: 'PATCH',
                token,
                body: {
                    action,
                    silence_minutes: 180,
                },
            });
            addToast(`Incidente ${action} ejecutado`, 'success');
            await fetchConfig();
        } catch (error) {
            console.error(error);
            addToast('No se pudo actualizar incidente', 'error');
        } finally {
            setActionLoading(null);
        }
    };

    const addIncidentNote = async (incidentId: string) => {
        const note = window.prompt('Agregar nota del incidente');
        if (!note || !note.trim()) return;
        if (!token) return;
        setActionLoading(`incident-${incidentId}-note`);
        try {
            await apiFetch(`/workspace/flags/incidents/${incidentId}`, {
                method: 'PATCH',
                token,
                body: {
                    action: 'note',
                    note: note.trim(),
                },
            });
            addToast('Nota agregada al incidente', 'success');
            await fetchConfig();
        } catch (error) {
            console.error(error);
            addToast('No se pudo agregar nota', 'error');
        } finally {
            setActionLoading(null);
        }
    };

    const cleanupIncidents = async () => {
        if (!token) return;
        setActionLoading('cleanup-incidents');
        try {
            const result = await apiFetch<{ cleanup?: { removed_closed?: number; removed_resolved?: number; reopened_silenced?: number } }>('/workspace/flags/incidents/cleanup', {
                method: 'POST',
                token,
                query: {
                    retain_closed_days: 30,
                    retain_resolved_days: 14,
                },
            });
            const removed = (result?.cleanup?.removed_closed || 0) + (result?.cleanup?.removed_resolved || 0);
            addToast(`Cleanup completado (removed: ${removed}, reopened: ${result?.cleanup?.reopened_silenced || 0})`, 'success');
            await fetchConfig();
        } catch (error) {
            console.error(error);
            addToast('No se pudo ejecutar cleanup de incidentes', 'error');
        } finally {
            setActionLoading(null);
        }
    };

    const downloadIncidents = async (format: 'json' | 'csv') => {
        try {
            const params = new URLSearchParams({ format, limit: '1000' });
            const response = await fetch(apiUrl(`/workspace/flags/incidents/export?${params.toString()}`), {
                method: 'GET',
                credentials: 'include',
                headers: {
                    Accept: format === 'csv' ? 'text/csv' : 'application/json',
                },
            });
            if (!response.ok) {
                throw new Error(`Incident export failed (${response.status})`);
            }

            const blob = await response.blob();
            const href = URL.createObjectURL(blob);
            const anchor = document.createElement('a');
            anchor.href = href;
            anchor.download = `feature_flags_incidents.${format}`;
            document.body.appendChild(anchor);
            anchor.click();
            anchor.remove();
            URL.revokeObjectURL(href);
            addToast(`Incidentes exportados en ${format.toUpperCase()}`, 'success');
        } catch (error) {
            console.error(error);
            addToast('No se pudo exportar incidentes', 'error');
        }
    };

    const downloadComplianceSnapshot = async () => {
        try {
            const params = new URLSearchParams({
                download: 'true',
                audit_limit: '300',
                incident_limit: '300',
                lookback_hours: '24',
                actor_threshold: '10',
                action_threshold: '20',
            });
            const response = await fetch(apiUrl(`/workspace/flags/compliance/snapshot?${params.toString()}`), {
                method: 'GET',
                credentials: 'include',
                headers: { Accept: 'application/json' },
            });
            if (!response.ok) {
                throw new Error(`Compliance snapshot failed (${response.status})`);
            }

            const blob = await response.blob();
            const href = URL.createObjectURL(blob);
            const anchor = document.createElement('a');
            anchor.href = href;
            anchor.download = `flags_compliance_snapshot_${new Date().toISOString().slice(0, 10)}.json`;
            document.body.appendChild(anchor);
            anchor.click();
            anchor.remove();
            URL.revokeObjectURL(href);
            addToast('Compliance snapshot exportado', 'success');
        } catch (error) {
            console.error(error);
            addToast('No se pudo exportar compliance snapshot', 'error');
        }
    };

    const downloadComplianceHistoryItem = async (snapshotId: string) => {
        try {
            const response = await fetch(apiUrl(`/workspace/flags/compliance/history/${snapshotId}?download=true`), {
                method: 'GET',
                credentials: 'include',
                headers: { Accept: 'application/json' },
            });
            if (!response.ok) {
                throw new Error(`Compliance history item failed (${response.status})`);
            }

            const blob = await response.blob();
            const href = URL.createObjectURL(blob);
            const anchor = document.createElement('a');
            anchor.href = href;
            anchor.download = `flags_compliance_snapshot_${snapshotId}.json`;
            document.body.appendChild(anchor);
            anchor.click();
            anchor.remove();
            URL.revokeObjectURL(href);
            addToast('Snapshot histórico exportado', 'success');
        } catch (error) {
            console.error(error);
            addToast('No se pudo exportar snapshot histórico', 'error');
        }
    };

    const runComplianceCompare = async () => {
        if (!token) return;
        if (!compareSnapshotIds.from || !compareSnapshotIds.to) {
            addToast('Selecciona dos snapshots para comparar', 'error');
            return;
        }

        setActionLoading('compare-compliance');
        try {
            const result = await apiFetch<any>('/workspace/flags/compliance/compare', {
                token,
                query: {
                    from_snapshot_id: compareSnapshotIds.from,
                    to_snapshot_id: compareSnapshotIds.to,
                },
                cache: 'no-store',
            });
            setCompareResult(result || null);
            addToast('Comparación de snapshots generada', 'success');
        } catch (error) {
            console.error(error);
            addToast('No se pudo comparar snapshots', 'error');
        } finally {
            setActionLoading(null);
        }
    };

    const cleanupComplianceHistory = async () => {
        if (!token) return;
        setActionLoading('cleanup-history');
        try {
            const result = await apiFetch<{ cleanup?: { removed?: number } }>('/workspace/flags/compliance/history/cleanup', {
                method: 'POST',
                token,
                query: { retain_days: historyRetentionDays },
            });
            addToast(`Snapshots depurados: ${result?.cleanup?.removed || 0}`, 'success');
            await fetchConfig();
        } catch (error) {
            console.error(error);
            addToast('No se pudo depurar historial de snapshots', 'error');
        } finally {
            setActionLoading(null);
        }
    };

    const updateCompliancePolicy = async (patch: any) => {
        if (!token) return;
        setActionLoading('update-policy');
        try {
            await apiFetch('/workspace/flags/compliance/policy', {
                method: 'PUT',
                token,
                body: patch,
            });
            addToast('Política de compliance actualizada', 'success');
            await fetchConfig();
        } catch (error) {
            console.error(error);
            addToast('No se pudo actualizar política', 'error');
        } finally {
            setActionLoading(null);
        }
    };

    const createSuppression = async () => {
        if (!token) return;
        setActionLoading('create-suppression');
        try {
            await apiFetch('/workspace/flags/compliance/suppressions', {
                method: 'POST',
                token,
                body: {
                    kind: suppressionDraft.kind,
                    value: suppressionDraft.value,
                    expires_in_hours: suppressionDraft.hours,
                    note: suppressionDraft.note,
                },
            });
            addToast('Supresión creada', 'success');
            await fetchConfig();
        } catch (error) {
            console.error(error);
            addToast('No se pudo crear supresión', 'error');
        } finally {
            setActionLoading(null);
        }
    };

    const deleteSuppression = async (suppressionId: string) => {
        if (!token) return;
        setActionLoading(`delete-supp-${suppressionId}`);
        try {
            await apiFetch(`/workspace/flags/compliance/suppressions/${suppressionId}`, {
                method: 'DELETE',
                token,
            });
            addToast('Supresión eliminada', 'success');
            await fetchConfig();
        } catch (error) {
            console.error(error);
            addToast('No se pudo eliminar supresión', 'error');
        } finally {
            setActionLoading(null);
        }
    };

    if (!isAuthenticated) return null;

    const settingsSidebar = (
        <div className="flex flex-col h-full overflow-hidden">
            <div className="p-8 border-b border-slate-100 dark:border-white/5 space-y-4">
                <div className="size-16 rounded-3xl bg-slate-900 dark:bg-white flex items-center justify-center text-white dark:text-slate-900 shadow-xl">
                    <Zap size={32} />
                </div>
                <div>
                    <h3 className="text-xl font-black tracking-tight text-slate-800 dark:text-white">Motor Core</h3>
                    <p className="text-[10px] font-bold text-blue-500 uppercase tracking-[0.2em]">Configuración Global</p>
                </div>
            </div>
            <div className="flex-1 overflow-y-auto p-4 space-y-2">
                <button className="w-full flex items-center justify-between px-4 py-3 bg-white dark:bg-white/5 shadow-md border border-blue-500/20 rounded-2xl text-blue-600 dark:text-blue-400 font-bold text-xs"><div className="flex items-center gap-3"><Settings size={16} /> Sistema Base</div> <ChevronRight size={14} /></button>
                <button className="w-full flex items-center justify-between px-4 py-3 hover:bg-slate-50 dark:hover:bg-white/5 rounded-2xl text-slate-500 font-bold text-xs transition-colors"><div className="flex items-center gap-3"><Shield size={16} /> Permisos y Roles</div></button>
                <button className="w-full flex items-center justify-between px-4 py-3 hover:bg-slate-50 dark:hover:bg-white/5 rounded-2xl text-slate-500 font-bold text-xs transition-colors"><div className="flex items-center gap-3"><Database size={16} /> Respaldos</div></button>
                <button className="w-full flex items-center justify-between px-4 py-3 hover:bg-slate-50 dark:hover:bg-white/5 rounded-2xl text-slate-500 font-bold text-xs transition-colors"><div className="flex items-center gap-3"><Activity size={16} /> Monitor de Salud</div></button>
            </div>
        </div>
    );

    return (
        <WorkspaceLayout 
            sidebarTitle="Ajustes del Sistema"
            parentTitle="Panel de Control"
            depth={2}
            onBack={() => router.push('/admin')}
            customSidebar={settingsSidebar}
        >
            <AdminShell
                breadcrumbs={[
                    { label: 'Infraestructura', icon: Server },
                    { label: 'Configuración Maestra', icon: Shield }
                ]}
            >
            <AdminHero
                eyebrow="System Core"
                title="Consola de Administración Senior"
                description="Control de bajo nivel del ecosistema MESH. Modifica el comportamiento global de la plataforma, gestiona feature flags y monitoriza el rendimiento del núcleo."
                tags={['v2.1.5', 'High Availability', 'MESH Core']}
                watchers={['Tech Lead', 'Root Admin']}
                primaryAction={{ 
                    label: actionLoading === 'worker' ? 'Reiniciando...' : 'Reiniciar Worker', 
                    icon: actionLoading === 'worker' ? Loader2 : RefreshCw, 
                    onClick: () => handleCriticalAction('worker', 'Reinicio de Worker') 
                }}
                secondaryAction={{ 
                    label: 'Respaldar DB', 
                    icon: Database, 
                    onClick: () => handleCriticalAction('backup', 'Backup de Base de Datos') 
                }}
            />

            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 pb-20">
                <div className="lg:col-span-8 space-y-8">
                    {/* Real-time Health Monitor */}
                    <section className="grid grid-cols-1 md:grid-cols-3 gap-6">
                        <HealthCard label="Latencia de Red" value={loading ? '...' : config?.health?.latency} status="optimal" icon={Activity} />
                        <HealthCard label="Uptime de Sistema" value={loading ? '...' : config?.health?.uptime} status="optimal" icon={Server} />
                        <HealthCard label="Consumo de RAM" value={loading ? '...' : config?.health?.memory} status="stable" icon={Cpu} />
                    </section>

                    {/* Feature Flags Grid */}
                    <section className="bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-[3rem] p-10 shadow-xl space-y-10 relative overflow-hidden">
                        <div className="absolute top-0 right-0 -mr-16 -mt-16 size-64 bg-blue-600/5 rounded-full blur-[100px]" />
                        <div className="relative z-10">
                            <div className="flex items-center gap-3 mb-10">
                                <Layers size={20} className="text-blue-600" />
                                <h3 className="text-lg font-black tracking-tight uppercase tracking-widest">Feature Flags & Módulos</h3>
                            </div>

                            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                <FeatureToggle 
                                    label="Academia & LMS" desc="Habilita el reproductor de cursos y certificados." 
                                    active={config?.features_enabled?.lms} onToggle={() => toggleFeature('lms')} 
                                    loading={actionLoading === 'flag-lms'}
                                />
                                <FeatureToggle 
                                    label="CRM Pastoral" desc="Control de miembros, casas y consolidación." 
                                    active={config?.features_enabled?.crm} onToggle={() => toggleFeature('crm')} 
                                    loading={actionLoading === 'flag-crm'}
                                />
                                <FeatureToggle 
                                    label="Optimus Brain AI" desc="Algoritmos de análisis proactivo y sugerencias." 
                                    active={config?.features_enabled?.ia} onToggle={() => toggleFeature('ia')} 
                                    loading={actionLoading === 'flag-ia'}
                                />
                                <FeatureToggle 
                                    label="Treasury & Pagos" desc="Gestión de donaciones y pasarelas bancarias." 
                                    active={config?.features_enabled?.donations} onToggle={() => toggleFeature('donations')} 
                                    loading={actionLoading === 'flag-donations'}
                                />
                                <FeatureToggle
                                    label="Knowledge Graph"
                                    desc="Activa exploración de grafo interactivo en Insights."
                                    active={config?.features_enabled?.knowledge_graph}
                                    onToggle={() => toggleFeature('knowledge_graph')}
                                    loading={actionLoading === 'flag-knowledge_graph'}
                                />
                                <FeatureToggle
                                    label="Web Vitals Dashboard"
                                    desc="Muestra métricas de performance en panel admin."
                                    active={config?.features_enabled?.web_vitals_dashboard}
                                    onToggle={() => toggleFeature('web_vitals_dashboard')}
                                    loading={actionLoading === 'flag-web_vitals_dashboard'}
                                />
                            </div>
                        </div>
                    </section>

                    {/* Integrated Providers */}
                    <section className="bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-[3rem] p-10 shadow-xl space-y-8">
                        <div className="flex items-center gap-3">
                            <Globe size={20} className="text-blue-600" />
                            <h3 className="text-lg font-black tracking-tight uppercase tracking-widest">Pasarelas & Comunicaciones</h3>
                        </div>

                        <div className="space-y-4">
                            <ProviderRow icon={Smartphone} name="Twilio WhatsApp API" status="Connected" color="emerald" detail="SID: AC...45f" />
                            <ProviderRow icon={Mail} name="SendGrid SMTP Core" status="Warning" color="amber" detail="Check API Key" />
                            <ProviderRow icon={Globe} name="Cloudflare WAF" status="Active" color="blue" detail="Pro Plan" />
                        </div>
                    </section>

                    <section className="bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-[3rem] p-10 shadow-xl space-y-6">
                        <div className="flex items-center justify-between gap-3">
                            <h3 className="text-lg font-black tracking-tight uppercase tracking-widest">Rollout Segmentado</h3>
                            <span className="text-[10px] font-black uppercase tracking-widest text-slate-400">Roles y porcentaje</span>
                        </div>
                        <RolloutControl
                            featureId="knowledge_graph"
                            label="Knowledge Graph"
                            rule={config?.feature_rules?.knowledge_graph}
                            selectedRole={roleScope.knowledge_graph || ''}
                            onRoleChange={(value) => setRoleScope((prev) => ({ ...prev, knowledge_graph: value }))}
                            onSave={({ role, percent, usersAllow, usersDeny }) => updateRule('knowledge_graph', {
                                roles_allow: role ? [role] : [],
                                users_allow: usersAllow,
                                users_deny: usersDeny,
                                rollout_percent: percent,
                            })}
                            loading={actionLoading === 'rule-knowledge_graph'}
                        />
                        <RolloutControl
                            featureId="web_vitals_dashboard"
                            label="Web Vitals Dashboard"
                            rule={config?.feature_rules?.web_vitals_dashboard}
                            selectedRole={roleScope.web_vitals_dashboard || ''}
                            onRoleChange={(value) => setRoleScope((prev) => ({ ...prev, web_vitals_dashboard: value }))}
                            onSave={({ role, percent, usersAllow, usersDeny }) => updateRule('web_vitals_dashboard', {
                                roles_allow: role ? [role] : [],
                                users_allow: usersAllow,
                                users_deny: usersDeny,
                                rollout_percent: percent,
                            })}
                            loading={actionLoading === 'rule-web_vitals_dashboard'}
                        />
                    </section>

                    <section className="bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-[3rem] p-10 shadow-xl space-y-5">
                        <div className="flex items-center justify-between gap-3">
                            <div className="flex items-center gap-3">
                                <h3 className="text-lg font-black tracking-tight uppercase tracking-widest">Auditoría de Flags</h3>
                                {auditAnomalies?.has_anomaly ? (
                                    <span className="inline-flex items-center gap-1 rounded-full bg-rose-50 px-2 py-1 text-[10px] font-black uppercase tracking-widest text-rose-600">
                                        <AlertTriangle size={12} /> Anomalía
                                    </span>
                                ) : (
                                    <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2 py-1 text-[10px] font-black uppercase tracking-widest text-emerald-600">
                                        <CheckCircle2 size={12} /> Normal
                                    </span>
                                )}
                            </div>
                            <div className="flex items-center gap-2">
                                <button onClick={scanIncidents} className="h-9 rounded-xl border border-slate-200 dark:border-white/10 px-3 text-[10px] font-black uppercase tracking-widest text-blue-600 hover:bg-blue-50 dark:hover:bg-white/10">
                                    {actionLoading === 'scan-incidents' ? 'Escaneando...' : 'Scan Incidents'}
                                </button>
                                <button onClick={() => downloadAudit('json')} className="h-9 rounded-xl border border-slate-200 dark:border-white/10 px-3 text-[10px] font-black uppercase tracking-widest text-slate-500 hover:bg-slate-100 dark:hover:bg-white/10">Export JSON</button>
                                <button onClick={() => downloadAudit('csv')} className="h-9 rounded-xl border border-slate-200 dark:border-white/10 px-3 text-[10px] font-black uppercase tracking-widest text-slate-500 hover:bg-slate-100 dark:hover:bg-white/10">Export CSV</button>
                            </div>
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                            <select
                                value={auditFilters.action}
                                onChange={(event) => setAuditFilters((prev) => ({ ...prev, action: event.target.value }))}
                                className="h-10 rounded-xl border border-slate-200 dark:border-white/10 bg-white dark:bg-black/20 px-3 text-xs font-black uppercase tracking-widest text-slate-600 dark:text-slate-200"
                            >
                                <option value="">Todas las acciones</option>
                                <option value="update_flags">update_flags</option>
                                <option value="update_rule">update_rule</option>
                            </select>
                            <select
                                value={auditFilters.feature}
                                onChange={(event) => setAuditFilters((prev) => ({ ...prev, feature: event.target.value }))}
                                className="h-10 rounded-xl border border-slate-200 dark:border-white/10 bg-white dark:bg-black/20 px-3 text-xs font-black uppercase tracking-widest text-slate-600 dark:text-slate-200"
                            >
                                <option value="">Todas las features</option>
                                {Object.keys(config?.features_enabled || {}).map((feature) => (
                                    <option key={feature} value={feature}>{feature}</option>
                                ))}
                            </select>
                            <input
                                value={auditFilters.actor}
                                onChange={(event) => setAuditFilters((prev) => ({ ...prev, actor: event.target.value }))}
                                placeholder="Filtrar actor (id usuario)"
                                className="h-10 rounded-xl border border-slate-200 dark:border-white/10 bg-white dark:bg-black/20 px-3 text-xs font-bold text-slate-600 dark:text-slate-200"
                            />
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
                            <AuditMetric label="Eventos" value={String(auditSummary?.total_events ?? 0)} />
                            <AuditMetric label="Cambios de flags" value={String(auditSummary?.by_action?.update_flags ?? 0)} />
                            <AuditMetric label="Cambios de reglas" value={String(auditSummary?.by_action?.update_rule ?? 0)} />
                            <AuditMetric label="Actores únicos" value={String((auditSummary?.top_actors || []).length)} />
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                            <div className="rounded-2xl border border-slate-100 dark:border-white/10 bg-slate-50 dark:bg-black/20 p-4">
                                <p className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-3">Top Actores</p>
                                <div className="space-y-2">
                                    {(auditSummary?.top_actors || []).slice(0, 4).map((item: any) => (
                                        <div key={`${item.actor}-${item.count}`} className="flex items-center justify-between text-xs">
                                            <span className="font-semibold text-slate-600 dark:text-slate-300">{item.actor}</span>
                                            <span className="font-black text-slate-500">{item.count}</span>
                                        </div>
                                    ))}
                                    {(!auditSummary?.top_actors || auditSummary.top_actors.length === 0) ? (
                                        <p className="text-xs font-semibold text-slate-400">Sin actividad todavía.</p>
                                    ) : null}
                                </div>
                            </div>
                            <div className="rounded-2xl border border-slate-100 dark:border-white/10 bg-slate-50 dark:bg-black/20 p-4">
                                <p className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-3">Top Features</p>
                                <div className="space-y-2">
                                    {(auditSummary?.top_features || []).slice(0, 4).map((item: any) => (
                                        <div key={`${item.feature}-${item.count}`} className="flex items-center justify-between text-xs">
                                            <span className="font-semibold text-slate-600 dark:text-slate-300">{item.feature}</span>
                                            <span className="font-black text-slate-500">{item.count}</span>
                                        </div>
                                    ))}
                                    {(!auditSummary?.top_features || auditSummary.top_features.length === 0) ? (
                                        <p className="text-xs font-semibold text-slate-400">Sin actividad todavía.</p>
                                    ) : null}
                                </div>
                            </div>
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                            <div className="rounded-2xl border border-slate-100 dark:border-white/10 bg-slate-50 dark:bg-black/20 p-4">
                                <p className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-3">Picos por Actor (24h)</p>
                                {(auditAnomalies?.actor_spikes || []).length > 0 ? (
                                    <div className="space-y-2">
                                        {auditAnomalies.actor_spikes.map((item: any) => (
                                            <div key={`${item.actor}-${item.count}`} className="flex items-center justify-between text-xs">
                                                <span className="font-semibold text-slate-600 dark:text-slate-300">{item.actor}</span>
                                                <span className="font-black text-rose-600">{item.count}</span>
                                            </div>
                                        ))}
                                    </div>
                                ) : (
                                    <p className="text-xs font-semibold text-slate-400">Sin picos detectados.</p>
                                )}
                            </div>
                            <div className="rounded-2xl border border-slate-100 dark:border-white/10 bg-slate-50 dark:bg-black/20 p-4">
                                <p className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-3">Picos por Acción (24h)</p>
                                {(auditAnomalies?.action_spikes || []).length > 0 ? (
                                    <div className="space-y-2">
                                        {auditAnomalies.action_spikes.map((item: any) => (
                                            <div key={`${item.action}-${item.count}`} className="flex items-center justify-between text-xs">
                                                <span className="font-semibold text-slate-600 dark:text-slate-300">{item.action}</span>
                                                <span className="font-black text-rose-600">{item.count}</span>
                                            </div>
                                        ))}
                                    </div>
                                ) : (
                                    <p className="text-xs font-semibold text-slate-400">Sin picos detectados.</p>
                                )}
                            </div>
                        </div>
                        {auditEvents.length === 0 ? (
                            <p className="text-xs font-bold text-slate-400 uppercase tracking-widest">Sin eventos registrados.</p>
                        ) : (
                            <div className="space-y-3">
                                {auditEvents.slice().reverse().map((event, idx) => (
                                    <div key={`${event.timestamp || idx}-${event.action || 'event'}`} className="rounded-2xl border border-slate-100 dark:border-white/10 bg-slate-50 dark:bg-black/20 p-4">
                                        <div className="flex items-center justify-between gap-3 mb-2">
                                            <p className="text-[10px] font-black uppercase tracking-widest text-slate-500">{event.action || 'update'}</p>
                                            <p className="text-[10px] font-bold uppercase tracking-widest text-slate-400">{event.timestamp ? new Date(event.timestamp).toLocaleString() : 'n/a'}</p>
                                        </div>
                                        <p className="text-xs font-semibold text-slate-600 dark:text-slate-300">actor: {event.updated_by || 'unknown'} {event.feature_id ? `| feature: ${event.feature_id}` : ''}</p>
                                        {event?.diff?.count ? (
                                            <div className="mt-2 space-y-1">
                                                <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">{event.diff.summary}</p>
                                                {event.diff.changes.slice(0, 3).map((change: any) => (
                                                    <p key={`${change.key}-${String(change.before)}-${String(change.after)}`} className="text-xs text-slate-500 dark:text-slate-400">
                                                        {change.key}: {String(change.before)} {'->'} {String(change.after)}
                                                    </p>
                                                ))}
                                            </div>
                                        ) : null}
                                    </div>
                                ))}
                            </div>
                        )}
                    </section>

                    <section className="bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-[3rem] p-10 shadow-xl space-y-5">
                        <div className="flex items-center justify-between gap-3">
                            <h3 className="text-lg font-black tracking-tight uppercase tracking-widest">Incidentes de Flags</h3>
                            <div className="flex items-center gap-2">
                                <select value={incidentStatsWindow} onChange={(event) => setIncidentStatsWindow(event.target.value as 'weekly' | 'monthly')} className="h-9 rounded-xl border border-slate-200 dark:border-white/10 bg-white dark:bg-black/20 px-2 text-[10px] font-black uppercase tracking-widest text-slate-600 dark:text-slate-200">
                                    <option value="weekly">weekly</option>
                                    <option value="monthly">monthly</option>
                                </select>
                                <button onClick={downloadComplianceSnapshot} className="h-9 rounded-xl border border-slate-200 dark:border-white/10 px-3 text-[10px] font-black uppercase tracking-widest text-indigo-600 hover:bg-indigo-50 dark:hover:bg-white/10">Compliance Snapshot</button>
                                <button onClick={() => downloadIncidents('json')} className="h-9 rounded-xl border border-slate-200 dark:border-white/10 px-3 text-[10px] font-black uppercase tracking-widest text-slate-500 hover:bg-slate-100 dark:hover:bg-white/10">Export Incidents JSON</button>
                                <button onClick={() => downloadIncidents('csv')} className="h-9 rounded-xl border border-slate-200 dark:border-white/10 px-3 text-[10px] font-black uppercase tracking-widest text-slate-500 hover:bg-slate-100 dark:hover:bg-white/10">Export Incidents CSV</button>
                                <button onClick={cleanupIncidents} className="h-9 rounded-xl border border-slate-200 dark:border-white/10 px-3 text-[10px] font-black uppercase tracking-widest text-slate-500 hover:bg-slate-100 dark:hover:bg-white/10">
                                    {actionLoading === 'cleanup-incidents' ? 'Cleaning...' : 'Cleanup'}
                                </button>
                                <span className="text-[10px] font-black uppercase tracking-widest text-slate-400">{incidents.length} items</span>
                            </div>
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                            <AuditMetric label="Created" value={String(incidentStats?.current?.created ?? '-')} />
                            <AuditMetric label="Closed" value={String(incidentStats?.current?.closed ?? '-')} />
                            <AuditMetric label="Closure %" value={incidentStats?.current?.closure_rate != null ? `${incidentStats.current.closure_rate}%` : '-'} />
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                            <DeltaMetric label="Created Δ" value={incidentStats?.deltas?.created_pct} inverse={false} />
                            <DeltaMetric label="MTTA Δ" value={incidentStats?.deltas?.mtta_pct} inverse={true} />
                            <DeltaMetric label="MTTR Δ" value={incidentStats?.deltas?.mttr_pct} inverse={true} />
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
                            <AuditMetric label="Open" value={String(incidentsSummary?.counts?.open ?? 0)} />
                            <AuditMetric label="Ack" value={String(incidentsSummary?.counts?.acknowledged ?? 0)} />
                            <AuditMetric label="Silenced" value={String(incidentsSummary?.counts?.silenced ?? 0)} />
                            <AuditMetric label="MTTA (min)" value={String(incidentsSummary?.mtta_minutes ?? '-')} />
                            <AuditMetric label="MTTR (min)" value={String(incidentsSummary?.mttr_minutes ?? '-')} />
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
                            <AuditMetric label="Critical" value={String(incidentsSummary?.severity_counts?.critical ?? 0)} />
                            <AuditMetric label="High" value={String(incidentsSummary?.severity_counts?.high ?? 0)} />
                            <AuditMetric label="Medium" value={String(incidentsSummary?.severity_counts?.medium ?? 0)} />
                            <AuditMetric label="Low" value={String(incidentsSummary?.severity_counts?.low ?? 0)} />
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                            <div className={clsx(
                                'rounded-2xl border p-3 text-xs font-black uppercase tracking-widest',
                                incidentsSummary?.breaches?.mtta ? 'border-rose-200 bg-rose-50 text-rose-700' : 'border-emerald-200 bg-emerald-50 text-emerald-700',
                            )}>
                                MTTA SLA {incidentsSummary?.breaches?.mtta ? 'BREACH' : 'OK'}
                                <span className="ml-2 font-bold">target {incidentsSummary?.targets?.mtta_minutes ?? slaTargets.mtta}m</span>
                            </div>
                            <div className={clsx(
                                'rounded-2xl border p-3 text-xs font-black uppercase tracking-widest',
                                incidentsSummary?.breaches?.mttr ? 'border-rose-200 bg-rose-50 text-rose-700' : 'border-emerald-200 bg-emerald-50 text-emerald-700',
                            )}>
                                MTTR SLA {incidentsSummary?.breaches?.mttr ? 'BREACH' : 'OK'}
                                <span className="ml-2 font-bold">target {incidentsSummary?.targets?.mttr_minutes ?? slaTargets.mttr}m</span>
                            </div>
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                            <div className="rounded-2xl border border-slate-100 dark:border-white/10 bg-slate-50 dark:bg-black/20 p-4 space-y-2">
                                <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">Target MTTA (min)</p>
                                <input type="number" min={1} max={10080} value={slaTargets.mtta} onChange={(event) => setSlaTargets((prev) => ({ ...prev, mtta: Number(event.target.value) || 1 }))} className="h-10 w-full rounded-xl border border-slate-200 dark:border-white/10 bg-white dark:bg-black/30 px-3 text-xs font-bold" />
                            </div>
                            <div className="rounded-2xl border border-slate-100 dark:border-white/10 bg-slate-50 dark:bg-black/20 p-4 space-y-2">
                                <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">Target MTTR (min)</p>
                                <input type="number" min={1} max={10080} value={slaTargets.mttr} onChange={(event) => setSlaTargets((prev) => ({ ...prev, mttr: Number(event.target.value) || 1 }))} className="h-10 w-full rounded-xl border border-slate-200 dark:border-white/10 bg-white dark:bg-black/30 px-3 text-xs font-bold" />
                            </div>
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                            <div className="rounded-2xl border border-slate-100 dark:border-white/10 bg-slate-50 dark:bg-black/20 p-4">
                                <p className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-3">Tendencia (14 dias)</p>
                                {incidentTrends.length === 0 ? (
                                    <p className="text-xs font-semibold text-slate-400">Sin datos de tendencia.</p>
                                ) : (
                                    <div className="max-h-52 overflow-y-auto space-y-2">
                                        {incidentTrends.slice(-7).map((row) => (
                                            <div key={row.date} className="grid grid-cols-4 gap-2 text-[11px]">
                                                <span className="font-black text-slate-500">{row.date}</span>
                                                <span className="text-slate-600">+{row.created}</span>
                                                <span className="text-emerald-600">-{row.closed}</span>
                                                <span className="text-blue-600">ack {row.acknowledged}</span>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                            <div className="rounded-2xl border border-slate-100 dark:border-white/10 bg-slate-50 dark:bg-black/20 p-4">
                                <p className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-3">Notificaciones internas</p>
                                {incidentNotifications.length === 0 ? (
                                    <p className="text-xs font-semibold text-slate-400">Sin notificaciones.</p>
                                ) : (
                                    <div className="max-h-52 overflow-y-auto space-y-2">
                                        {incidentNotifications.slice().reverse().slice(0, 8).map((item, idx) => (
                                            <div key={`${item.timestamp || idx}-${item.type || 'notif'}`} className="rounded-lg border border-slate-200 dark:border-white/10 bg-white/70 dark:bg-black/30 p-2">
                                                <p className="text-[10px] font-black uppercase tracking-widest text-slate-500">{item.type || 'notification'}</p>
                                                <p className="text-xs font-semibold text-slate-600 dark:text-slate-300">
                                                    incident: {item.incident_id || 'n/a'} | sev: {item.severity || 'n/a'}
                                                </p>
                                                {item.risk_score != null ? (
                                                    <p className="text-[10px] text-slate-500 dark:text-slate-400">risk score: {item.risk_score}</p>
                                                ) : null}
                                                {(item.from_snapshot_id || item.to_snapshot_id) ? (
                                                    <p className="text-[10px] text-slate-500 dark:text-slate-400">from: {item.from_snapshot_id || '-'} to: {item.to_snapshot_id || '-'}</p>
                                                ) : null}
                                                <p className="text-[10px] text-slate-400">{item.timestamp ? new Date(item.timestamp).toLocaleString() : 'n/a'}</p>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        </div>
                        <div className="rounded-2xl border border-slate-100 dark:border-white/10 bg-slate-50 dark:bg-black/20 p-4">
                            <p className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-3">Compliance Snapshot History</p>
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-2 mb-3">
                                <select value={compareSnapshotIds.from} onChange={(event) => setCompareSnapshotIds((prev) => ({ ...prev, from: event.target.value }))} className="h-9 rounded-xl border border-slate-200 dark:border-white/10 bg-white dark:bg-black/20 px-2 text-[10px] font-black uppercase tracking-widest text-slate-600 dark:text-slate-200">
                                    <option value="">from snapshot</option>
                                    {complianceHistory.map((item) => (
                                        <option key={`from-${item.snapshot_id}`} value={item.snapshot_id}>{item.snapshot_id}</option>
                                    ))}
                                </select>
                                <select value={compareSnapshotIds.to} onChange={(event) => setCompareSnapshotIds((prev) => ({ ...prev, to: event.target.value }))} className="h-9 rounded-xl border border-slate-200 dark:border-white/10 bg-white dark:bg-black/20 px-2 text-[10px] font-black uppercase tracking-widest text-slate-600 dark:text-slate-200">
                                    <option value="">to snapshot</option>
                                    {complianceHistory.map((item) => (
                                        <option key={`to-${item.snapshot_id}`} value={item.snapshot_id}>{item.snapshot_id}</option>
                                    ))}
                                </select>
                                <button onClick={runComplianceCompare} className="h-9 rounded-xl border border-slate-200 dark:border-white/10 px-3 text-[10px] font-black uppercase tracking-widest text-indigo-600 hover:bg-indigo-50 dark:hover:bg-white/10">
                                    {actionLoading === 'compare-compliance' ? 'Comparando...' : 'Compare'}
                                </button>
                            </div>
                            <div className="grid grid-cols-1 md:grid-cols-[1fr_auto] gap-2 mb-3">
                                <input type="number" min={1} max={3650} value={historyRetentionDays} onChange={(event) => setHistoryRetentionDays(Number(event.target.value) || 90)} className="h-9 rounded-xl border border-slate-200 dark:border-white/10 bg-white dark:bg-black/20 px-2 text-[10px] font-black uppercase tracking-widest text-slate-600 dark:text-slate-200" />
                                <button onClick={cleanupComplianceHistory} className="h-9 rounded-xl border border-slate-200 dark:border-white/10 px-3 text-[10px] font-black uppercase tracking-widest text-slate-600 hover:bg-slate-100 dark:hover:bg-white/10">
                                    {actionLoading === 'cleanup-history' ? 'Cleaning...' : 'Cleanup History'}
                                </button>
                            </div>
                            {compareResult?.diff ? (
                                <div className="rounded-xl border border-slate-200 dark:border-white/10 bg-white/70 dark:bg-black/30 p-3 mb-3 space-y-1">
                                    <p className="text-[10px] font-black uppercase tracking-widest text-slate-500">Comparison Result</p>
                                    <p className="text-xs text-slate-600 dark:text-slate-300">feature changes: {compareResult.diff.feature_changes_count ?? 0}</p>
                                    <p className="text-xs text-slate-600 dark:text-slate-300">drift severity: <span className={clsx(
                                        'font-black uppercase',
                                        compareResult.diff?.drift?.severity === 'critical' && 'text-rose-700',
                                        compareResult.diff?.drift?.severity === 'high' && 'text-orange-700',
                                        compareResult.diff?.drift?.severity === 'medium' && 'text-amber-700',
                                        (!compareResult.diff?.drift?.severity || compareResult.diff?.drift?.severity === 'low') && 'text-emerald-700',
                                    )}>{compareResult.diff?.drift?.severity || 'low'}</span></p>
                                    <p className="text-xs text-slate-600 dark:text-slate-300">risk score: {compareResult.diff?.drift?.risk_score ?? 0}</p>
                                    <p className="text-xs text-slate-600 dark:text-slate-300">critical flags changed: {compareResult.diff?.drift?.critical_feature_changes?.length ?? 0}</p>
                                    <p className="text-xs text-slate-600 dark:text-slate-300">critical flags disabled: {compareResult.diff?.drift?.critical_disabled?.length ?? 0}</p>
                                    <p className="text-xs text-slate-600 dark:text-slate-300">incident count delta: {compareResult.diff.metrics?.incident_count?.delta ?? '-'}</p>
                                    <p className="text-xs text-slate-600 dark:text-slate-300">critical delta: {compareResult.diff.metrics?.critical_incidents?.delta ?? '-'}</p>
                                    <p className="text-xs text-slate-600 dark:text-slate-300">mtta delta: {compareResult.diff.metrics?.mtta_minutes?.delta ?? '-'}</p>
                                    <p className="text-xs text-slate-600 dark:text-slate-300">mttr delta: {compareResult.diff.metrics?.mttr_minutes?.delta ?? '-'}</p>
                                    {Array.isArray(compareResult.diff?.drift?.reasons) && compareResult.diff.drift.reasons.length > 0 ? (
                                        <div className="pt-1 space-y-1">
                                            {compareResult.diff.drift.reasons.slice(0, 3).map((reason: string, idx: number) => (
                                                <p key={`${reason}-${idx}`} className="text-[11px] text-slate-500 dark:text-slate-400">- {reason}</p>
                                            ))}
                                        </div>
                                    ) : null}
                                    {Array.isArray(compareResult.diff?.drift?.mitigations) && compareResult.diff.drift.mitigations.length > 0 ? (
                                        <div className="pt-1 space-y-1">
                                            {compareResult.diff.drift.mitigations.slice(0, 3).map((item: string, idx: number) => (
                                                <p key={`${item}-${idx}`} className="text-[11px] text-indigo-600 dark:text-indigo-300">* {item}</p>
                                            ))}
                                        </div>
                                    ) : null}
                                </div>
                            ) : null}
                            {complianceHistory.length === 0 ? (
                                <p className="text-xs font-semibold text-slate-400">Sin snapshots registrados.</p>
                            ) : (
                                <div className="space-y-2 max-h-56 overflow-y-auto">
                                    {complianceHistory.slice().reverse().map((item) => (
                                        <div key={`${item.snapshot_id}-${item.recorded_at}`} className="rounded-xl border border-slate-200 dark:border-white/10 bg-white/70 dark:bg-black/30 p-3">
                                            <div className="flex flex-wrap items-center justify-between gap-2">
                                                <p className="text-[10px] font-black uppercase tracking-widest text-slate-500">{item.snapshot_id}</p>
                                                <button onClick={() => downloadComplianceHistoryItem(String(item.snapshot_id || ''))} className="h-7 rounded-lg border border-slate-200 dark:border-white/10 px-2 text-[10px] font-black uppercase tracking-widest text-indigo-600">Download</button>
                                            </div>
                                            <p className="text-[11px] text-slate-600 dark:text-slate-300">{item.recorded_at ? new Date(item.recorded_at).toLocaleString() : 'n/a'}</p>
                                            <p className="text-[10px] text-slate-400">events: {item.summary?.audit_events ?? '-'} | incidents: {item.summary?.incidents ?? '-'}</p>
                                            <p className="text-[10px] text-slate-400">critical: {item.summary?.critical_incidents ?? 0} | anomaly: {item.summary?.has_anomaly ? 'yes' : 'no'}</p>
                                            <p className="text-[10px] text-slate-400">drift: {item.drift_from_previous?.severity || 'n/a'} | risk: {item.drift_from_previous?.risk_score ?? 0}</p>
                                            <p className="text-[10px] text-slate-400">reasons: {(item.drift_from_previous?.reasons || []).slice(0, 1).join(', ') || '-'}</p>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                        <div className="rounded-2xl border border-slate-100 dark:border-white/10 bg-slate-50 dark:bg-black/20 p-4">
                            <p className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-3">Weekly Compliance Summary</p>
                            {complianceWeeklySummary.length === 0 ? (
                                <p className="text-xs font-semibold text-slate-400">Sin resumen semanal.</p>
                            ) : (
                                <div className="max-h-48 overflow-y-auto space-y-1">
                                    {complianceWeeklySummary.map((row) => (
                                        <div key={row.week} className="grid grid-cols-5 gap-2 text-[10px]">
                                            <span className="font-black text-slate-500">{row.week}</span>
                                            <span className="text-slate-600">snap {row.snapshots}</span>
                                            <span className="text-amber-600">anom {row.anomaly_snapshots}</span>
                                            <span className="text-rose-600">driftC {row.critical_drift_alerts}</span>
                                            <span className="text-orange-600">risk {row.max_risk_score}</span>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                        <div className="rounded-2xl border border-slate-100 dark:border-white/10 bg-slate-50 dark:bg-black/20 p-4 space-y-3">
                            <div className="flex items-center justify-between gap-2">
                                <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">Drift Policy Engine</p>
                                <span className="text-[10px] font-bold text-slate-500">env: {compliancePolicy?.resolved?.environment || 'production'}</span>
                            </div>
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
                                <select
                                    value={compliancePolicy?.policy?.active_environment || 'production'}
                                    onChange={(event) => updateCompliancePolicy({ active_environment: event.target.value })}
                                    className="h-9 rounded-xl border border-slate-200 dark:border-white/10 bg-white dark:bg-black/20 px-2 text-[10px] font-black uppercase tracking-widest text-slate-600 dark:text-slate-200"
                                >
                                    <option value="development">development</option>
                                    <option value="staging">staging</option>
                                    <option value="production">production</option>
                                </select>
                                <button
                                    onClick={() => updateCompliancePolicy({
                                        environments: {
                                            [compliancePolicy?.policy?.active_environment || 'production']: {
                                                incident_spike_delta: Number(compliancePolicy?.resolved?.incident_spike_delta || 5),
                                                mtta_regression_pct: Number(compliancePolicy?.resolved?.mtta_regression_pct || 0.25),
                                                mttr_regression_pct: Number(compliancePolicy?.resolved?.mttr_regression_pct || 0.25),
                                                critical_feature_change_count_high: Number(compliancePolicy?.resolved?.critical_feature_change_count_high || 2),
                                                critical_feature_disabled_force: Boolean(compliancePolicy?.resolved?.critical_feature_disabled_force ?? true),
                                            },
                                        },
                                    })}
                                    className="h-9 rounded-xl border border-slate-200 dark:border-white/10 px-2 text-[10px] font-black uppercase tracking-widest text-indigo-600"
                                >
                                    {actionLoading === 'update-policy' ? 'Saving...' : 'Save Policy'}
                                </button>
                                <div className="rounded-xl border border-slate-200 dark:border-white/10 bg-white/70 dark:bg-black/30 px-2 py-1 text-[10px] font-bold text-slate-500">
                                    spike {compliancePolicy?.resolved?.incident_spike_delta ?? '-'} | mtta {compliancePolicy?.resolved?.mtta_regression_pct ?? '-'}
                                </div>
                            </div>
                            <div className="rounded-xl border border-slate-200 dark:border-white/10 bg-white/70 dark:bg-black/30 p-3 space-y-2">
                                <p className="text-[10px] font-black uppercase tracking-widest text-slate-500">Suppressions</p>
                                <div className="grid grid-cols-1 md:grid-cols-4 gap-2">
                                    <select value={suppressionDraft.kind} onChange={(event) => setSuppressionDraft((prev) => ({ ...prev, kind: event.target.value }))} className="h-8 rounded-lg border border-slate-200 dark:border-white/10 bg-white dark:bg-black/20 px-2 text-[10px] font-black uppercase tracking-widest text-slate-600 dark:text-slate-200">
                                        <option value="severity">severity</option>
                                        <option value="feature">feature</option>
                                        <option value="metric_alert">metric_alert</option>
                                        <option value="all">all</option>
                                    </select>
                                    <input value={suppressionDraft.value} onChange={(event) => setSuppressionDraft((prev) => ({ ...prev, value: event.target.value }))} placeholder="value" className="h-8 rounded-lg border border-slate-200 dark:border-white/10 bg-white dark:bg-black/20 px-2 text-[10px] font-bold" />
                                    <input type="number" min={1} max={720} value={suppressionDraft.hours} onChange={(event) => setSuppressionDraft((prev) => ({ ...prev, hours: Number(event.target.value) || 24 }))} className="h-8 rounded-lg border border-slate-200 dark:border-white/10 bg-white dark:bg-black/20 px-2 text-[10px] font-bold" />
                                    <button onClick={createSuppression} className="h-8 rounded-lg border border-slate-200 dark:border-white/10 px-2 text-[10px] font-black uppercase tracking-widest text-indigo-600">{actionLoading === 'create-suppression' ? 'Creating...' : 'Add'}</button>
                                </div>
                                {Array.isArray(compliancePolicy?.resolved?.suppressions) && compliancePolicy.resolved.suppressions.length > 0 ? (
                                    <div className="space-y-1 max-h-36 overflow-y-auto">
                                        {compliancePolicy.resolved.suppressions.map((item: any) => (
                                            <div key={item.id} className="flex items-center justify-between gap-2 rounded-lg border border-slate-200 dark:border-white/10 bg-white/70 dark:bg-black/30 px-2 py-1 text-[10px]">
                                                <span className="font-bold text-slate-600 dark:text-slate-300">{item.kind}:{item.value || '*'} (exp {item.expires_at ? new Date(item.expires_at).toLocaleString() : 'n/a'})</span>
                                                <button onClick={() => deleteSuppression(String(item.id || ''))} className="font-black uppercase tracking-widest text-rose-600">del</button>
                                            </div>
                                        ))}
                                    </div>
                                ) : (
                                    <p className="text-[10px] font-semibold text-slate-400">No active suppressions.</p>
                                )}
                            </div>
                        </div>
                        {incidents.length === 0 ? (
                            <p className="text-xs font-semibold text-slate-400">No hay incidentes abiertos o registrados.</p>
                        ) : (
                            <div className="space-y-3">
                                {incidents.slice().reverse().map((incident) => (
                                    <div key={incident.id} className="rounded-2xl border border-slate-100 dark:border-white/10 bg-slate-50 dark:bg-black/20 p-4">
                                        <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
                                            <p className="text-[10px] font-black uppercase tracking-widest text-slate-500">{incident.kind} | {incident.key}</p>
                                            <div className="flex items-center gap-2">
                                                <span className={clsx(
                                                    'rounded-full px-2 py-1 text-[10px] font-black uppercase tracking-widest',
                                                    incident.severity === 'critical' && 'bg-rose-100 text-rose-700',
                                                    incident.severity === 'high' && 'bg-orange-100 text-orange-700',
                                                    incident.severity === 'medium' && 'bg-amber-100 text-amber-700',
                                                    (!incident.severity || incident.severity === 'low') && 'bg-slate-100 text-slate-600',
                                                )}>{incident.severity || 'low'}</span>
                                                <span className={clsx(
                                                    'rounded-full px-2 py-1 text-[10px] font-black uppercase tracking-widest',
                                                    incident.status === 'open' && 'bg-rose-50 text-rose-600',
                                                    incident.status === 'acknowledged' && 'bg-amber-50 text-amber-600',
                                                    incident.status === 'silenced' && 'bg-blue-50 text-blue-600',
                                                    incident.status === 'closed' && 'bg-emerald-50 text-emerald-600',
                                                )}>{incident.status}</span>
                                            </div>
                                        </div>
                                        <p className="text-xs font-semibold text-slate-600 dark:text-slate-300">count: {incident.count} | threshold: {incident.threshold}</p>
                                        <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mt-1">updated: {incident.updated_at ? new Date(incident.updated_at).toLocaleString() : 'n/a'}</p>
                                        <div className="mt-3 flex flex-wrap gap-2">
                                            <button onClick={() => updateIncident(incident.id, 'acknowledge')} className="h-8 rounded-lg border border-slate-200 dark:border-white/10 px-3 text-[10px] font-black uppercase tracking-widest text-slate-600">Acknowledge</button>
                                            <button onClick={() => updateIncident(incident.id, 'silence')} className="h-8 rounded-lg border border-slate-200 dark:border-white/10 px-3 text-[10px] font-black uppercase tracking-widest text-blue-600">Silence 3h</button>
                                            <button onClick={() => updateIncident(incident.id, 'reopen')} className="h-8 rounded-lg border border-slate-200 dark:border-white/10 px-3 text-[10px] font-black uppercase tracking-widest text-amber-600">Reopen</button>
                                            <button onClick={() => updateIncident(incident.id, 'close')} className="h-8 rounded-lg border border-slate-200 dark:border-white/10 px-3 text-[10px] font-black uppercase tracking-widest text-emerald-600">Close</button>
                                            <button onClick={() => addIncidentNote(incident.id)} className="h-8 rounded-lg border border-slate-200 dark:border-white/10 px-3 text-[10px] font-black uppercase tracking-widest text-violet-600">Add note</button>
                                        </div>
                                        {Array.isArray(incident.history) && incident.history.length > 0 ? (
                                            <div className="mt-3 rounded-xl border border-slate-100 dark:border-white/10 bg-white/60 dark:bg-black/30 p-3">
                                                <p className="text-[10px] font-black uppercase tracking-widest text-slate-400 mb-2">Timeline</p>
                                                <div className="space-y-2">
                                                    {incident.history.slice(-4).reverse().map((entry: any, idx: number) => (
                                                        <div key={`${entry.at || idx}-${entry.event || 'event'}`} className="text-xs">
                                                            <p className="font-black text-slate-600 dark:text-slate-300 uppercase tracking-wider">{entry.event} <span className="font-bold text-slate-400">by {entry.by || 'system'}</span></p>
                                                            <p className="text-[11px] text-slate-500 dark:text-slate-400">{entry.at ? new Date(entry.at).toLocaleString() : 'n/a'}</p>
                                                            {entry.note ? <p className="text-[11px] text-slate-600 dark:text-slate-300">{entry.note}</p> : null}
                                                        </div>
                                                    ))}
                                                </div>
                                            </div>
                                        ) : null}
                                    </div>
                                ))}
                            </div>
                        )}
                    </section>
                </div>

                {/* Cyber Security Sidebar */}
                <aside className="lg:col-span-4 space-y-8">
                    <section className="p-8 bg-slate-900 rounded-[3rem] text-white shadow-2xl space-y-10 relative overflow-hidden group">
                        <div className="absolute top-0 right-0 -mr-10 -mt-10 size-40 bg-blue-600/20 rounded-full blur-3xl" />
                        <div className="relative z-10">
                            <div className="flex items-center gap-3 mb-8">
                                <Lock size={20} className="text-blue-400" />
                                <h4 className="text-[11px] font-black uppercase tracking-[0.3em] text-blue-400">Security Hardening</h4>
                            </div>
                            <div className="space-y-5">
                                <SecurityCheck label="HSTS / SSL Enforcement" active />
                                <SecurityCheck label="Rate Limiting (5 req/m)" active />
                                <SecurityCheck label="RBAC Policy v3.0" active />
                                <SecurityCheck label="Data Encryption at Rest" active />
                            </div>
                            <button className="w-full mt-10 py-5 bg-white text-slate-900 rounded-2xl text-[11px] font-black uppercase tracking-[0.2em] shadow-xl hover:bg-slate-100 transition-all active:scale-95">
                                Ver Registro de Amenazas
                            </button>
                        </div>
                    </section>

                    <section className="bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-[3rem] p-10 shadow-xl space-y-8">
                        <div className="flex items-center justify-between">
                            <h4 className="text-[11px] font-black uppercase tracking-widest text-slate-400">Estado del Cluster</h4>
                            <RefreshCw size={18} className="text-slate-300" />
                        </div>
                        <div className="space-y-6">
                            <ClusterNode label="Worker Analysis" status="running" load="12%" />
                            <ClusterNode label="Socket Server" status="running" load="4%" />
                            <ClusterNode label="Media Processor" status="idle" load="0%" />
                        </div>
                    </section>
                </aside>
            </div>
        </AdminShell>
    </WorkspaceLayout>
    );
}

function HealthCard({ label, value, status, icon: Icon }: any) {
    return (
        <div className="p-8 bg-white dark:bg-white/5 border border-slate-200 dark:border-white/10 rounded-[2.5rem] shadow-sm flex flex-col gap-6 group hover:shadow-xl transition-all">
            <div className="flex justify-between items-start">
                <div className="size-12 rounded-2xl bg-blue-50 dark:bg-blue-900/30 text-blue-600 flex items-center justify-center group-hover:scale-110 transition-transform">
                    <Icon size={24} />
                </div>
                <div className="flex items-center gap-1.5 px-2 py-1 bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 rounded-lg">
                    <div className="size-1.5 rounded-full bg-emerald-500 animate-pulse" />
                    <span className="text-[8px] font-black uppercase">{status}</span>
                </div>
            </div>
            <div>
                <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-1">{label}</p>
                <h4 className="text-3xl font-black text-slate-900 dark:text-white tracking-tighter">{value}</h4>
            </div>
        </div>
    );
}

function FeatureToggle({ label, desc, active, onToggle, loading }: any) {
    return (
        <div className="p-6 bg-slate-50 dark:bg-white/5 rounded-3xl border border-slate-100 dark:border-white/5 flex items-center justify-between group hover:border-blue-500/20 transition-all">
            <div className="flex-1 pr-4">
                <h5 className="text-[13px] font-black text-slate-800 dark:text-white uppercase mb-1">{label}</h5>
                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest leading-tight">{desc}</p>
            </div>
            <button onClick={onToggle} disabled={loading} className="transition-all active:scale-90 disabled:opacity-60">
                {loading ? (
                    <Loader2 size={22} className="animate-spin text-blue-500" />
                ) : active ? (
                    <ToggleRight size={32} className="text-blue-600 shadow-[0_0_10px_rgba(37,99,235,0.2)]" />
                ) : (
                    <ToggleLeft size={32} className="text-slate-300" />
                )}
            </button>
        </div>
    );
}

function AuditMetric({ label, value }: { label: string; value: string }) {
    return (
        <div className="rounded-2xl border border-slate-100 dark:border-white/10 bg-slate-50 dark:bg-black/20 p-4">
            <p className="text-[10px] font-black uppercase tracking-widest text-slate-400">{label}</p>
            <p className="text-2xl font-black text-slate-800 dark:text-white mt-1">{value}</p>
        </div>
    );
}

function DeltaMetric({ label, value, inverse }: { label: string; value: number | null | undefined; inverse: boolean }) {
    const numeric = typeof value === 'number' ? value : null;
    const isGood = numeric == null ? null : inverse ? numeric <= 0 : numeric >= 0;
    const tone = isGood == null ? 'text-slate-500 bg-slate-50 border-slate-200' : isGood ? 'text-emerald-700 bg-emerald-50 border-emerald-200' : 'text-rose-700 bg-rose-50 border-rose-200';

    return (
        <div className={clsx('rounded-2xl border p-4', tone)}>
            <p className="text-[10px] font-black uppercase tracking-widest">{label}</p>
            <p className="text-xl font-black mt-1">{numeric == null ? '-' : `${numeric > 0 ? '+' : ''}${numeric}%`}</p>
        </div>
    );
}

function ProviderRow({ icon: Icon, name, status, color, detail }: any) {
    const colors: any = {
        emerald: 'text-emerald-500 bg-emerald-50 dark:bg-emerald-900/20',
        amber: 'text-amber-500 bg-amber-50 dark:bg-amber-900/20',
        blue: 'text-blue-500 bg-blue-50 dark:bg-blue-900/20'
    };
    return (
        <div className="flex items-center justify-between p-6 bg-white dark:bg-white/5 border border-slate-100 dark:border-white/5 rounded-[2rem] group hover:border-blue-500/20 transition-all shadow-sm">
            <div className="flex items-center gap-5">
                <div className={clsx("size-12 rounded-2xl flex items-center justify-center transition-transform group-hover:scale-110", colors[color])}>
                    <Icon size={24} />
                </div>
                <div>
                    <span className="text-[14px] font-black text-slate-800 dark:text-white uppercase leading-none block mb-1">{name}</span>
                    <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">{detail}</span>
                </div>
            </div>
            <div className={clsx("px-4 py-1.5 rounded-full text-[9px] font-black uppercase tracking-widest", colors[color])}>
                {status}
            </div>
        </div>
    );
}

function SecurityCheck({ label }: any) {
    return (
        <div className="flex items-center gap-3">
            <div className="size-2.5 rounded-full bg-emerald-500 shadow-[0_0_10px_#10b981]" />
            <span className="text-[11px] font-black text-blue-100/80 uppercase tracking-[0.1em]">{label}</span>
        </div>
    );
}

function ClusterNode({ label, status, load }: any) {
    return (
        <div className="flex items-center justify-between p-2">
            <div className="flex items-center gap-3">
                <div className={clsx("size-2 rounded-full", status === 'running' ? 'bg-emerald-500' : 'bg-slate-400')} />
                <span className="text-[11px] font-black text-slate-700 dark:text-slate-200 uppercase">{label}</span>
            </div>
            <span className="text-[10px] font-black text-blue-600 uppercase">{load}</span>
        </div>
    );
}

interface RolloutControlProps {
    featureId: string;
    label: string;
    rule?: { roles_allow?: string[]; rollout_percent?: number; users_allow?: string[]; users_deny?: string[] } | null;
    selectedRole: string;
    onRoleChange: (value: string) => void;
    onSave: (opts: { role: string; percent: number; usersAllow: string[]; usersDeny: string[] }) => void;
    loading?: boolean;
}

function RolloutControl({ featureId, label, rule, selectedRole, onRoleChange, onSave, loading }: RolloutControlProps) {
    const [percent, setPercent] = React.useState(rule?.rollout_percent ?? 100);
    return (
        <div className="p-6 bg-slate-50 dark:bg-white/5 rounded-2xl border border-slate-100 dark:border-white/5 space-y-4">
            <div className="flex items-center justify-between">
                <span className="text-[11px] font-black uppercase tracking-widest text-slate-700 dark:text-slate-200">{label}</span>
                <span className="text-[9px] font-black bg-blue-100 dark:bg-blue-900/30 text-blue-600 px-2 py-0.5 rounded-full uppercase">{featureId}</span>
            </div>
            <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                    <label className="text-[9px] uppercase font-black text-slate-400 tracking-widest">Rol</label>
                    <select
                        value={selectedRole}
                        onChange={(e) => onRoleChange(e.target.value)}
                        className="w-full text-[11px] font-bold bg-white dark:bg-black/20 border border-slate-200 dark:border-white/10 rounded-lg px-3 py-2 outline-none"
                    >
                        <option value="">Todos</option>
                        <option value="admin">Admin</option>
                        <option value="pastor">Pastor</option>
                        <option value="staff">Staff</option>
                    </select>
                </div>
                <div className="space-y-1">
                    <label className="text-[9px] uppercase font-black text-slate-400 tracking-widest">Rollout {percent}%</label>
                    <input
                        type="range" min={0} max={100} value={percent}
                        onChange={(e) => setPercent(Number(e.target.value))}
                        className="w-full accent-blue-600"
                    />
                </div>
            </div>
            <button
                onClick={() => onSave({ role: selectedRole, percent, usersAllow: rule?.users_allow || [], usersDeny: rule?.users_deny || [] })}
                disabled={loading}
                className="w-full py-3 bg-blue-600 text-white rounded-xl text-[10px] font-black uppercase tracking-widest hover:bg-blue-700 transition-all disabled:opacity-50"
            >
                {loading ? 'Guardando...' : 'Aplicar Regla'}
            </button>
        </div>
    );
}

