"use client";

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useAuth } from '@/context/AuthContext';
import { apiFetch } from '@/lib/http';
import { toast } from 'sonner';
import {
  AcademicProgram,
  AcademicPeriod,
  GradingScheme,
  StudyPlan,
  PeriodOffering,
} from '@/types/academy';
import WorkspaceToolbar from '@/components/WorkspaceToolbar';
import EmptyState from '@/components/ui/EmptyState';
import { DSSkeleton } from '@/design';
import ProgramDrawer from '@/components/academy/ProgramDrawer';
import GradingSchemeDrawer from '@/components/academy/GradingSchemeDrawer';
import AcademicPeriodDrawer from '@/components/academy/AcademicPeriodDrawer';
import StudyPlanSubjectDrawer from '@/components/academy/StudyPlanSubjectDrawer';
import OfferingGradesDrawer from '@/components/academy/OfferingGradesDrawer';
import StudentEnrollmentDrawer from '@/components/academy/StudentEnrollmentDrawer';
import CloseGradesDrawer from '@/components/academy/CloseGradesDrawer';
import {
  GraduationCap,
  Calendar,
  Award,
  BookOpen,
  Users,
  Plus,
  Sliders,
  Edit2,
  Search,
  UserCheck,
  UserPlus,
  Lock,
} from 'lucide-react';
import clsx from 'clsx';

type AdminTab = 'programs' | 'periods' | 'grading' | 'curriculum' | 'offerings' | 'enrollments';

export default function AcademyAdminConsole() {
  const { token, isAuthenticated } = useAuth();
  const [activeTab, setActiveTab] = useState<AdminTab>('programs');
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');

  // Domain data
  const [programs, setPrograms] = useState<AcademicProgram[]>([]);
  const [periods, setPeriods] = useState<AcademicPeriod[]>([]);
  const [schemes, setSchemes] = useState<GradingScheme[]>([]);
  const [studyPlans, setStudyPlans] = useState<StudyPlan[]>([]);
  const [offerings, setOfferings] = useState<PeriodOffering[]>([]);

  // Drawer states (100% sliding panels, 0 modals)
  const [selectedProgram, setSelectedProgram] = useState<AcademicProgram | null>(null);
  const [programDrawerOpen, setProgramDrawerOpen] = useState(false);

  const [selectedScheme, setSelectedScheme] = useState<GradingScheme | null>(null);
  const [schemeDrawerOpen, setSchemeDrawerOpen] = useState(false);

  const [selectedPeriod, setSelectedPeriod] = useState<AcademicPeriod | null>(null);
  const [periodDrawerOpen, setPeriodDrawerOpen] = useState(false);

  const [selectedPlanId, setSelectedPlanId] = useState<string>('');
  const [subjectDrawerOpen, setSubjectDrawerOpen] = useState(false);

  const [selectedOfferingId, setSelectedOfferingId] = useState<string>('');
  const [gradesDrawerOpen, setGradesDrawerOpen] = useState(false);

  const [selectedOfferingForAction, setSelectedOfferingForAction] = useState<PeriodOffering | null>(null);
  const [enrollmentDrawerOpen, setEnrollmentDrawerOpen] = useState(false);
  const [closeGradesDrawerOpen, setCloseGradesDrawerOpen] = useState(false);

  const loadAll = useCallback(async () => {
    if (!token) return;
    try {
      setLoading(true);
      const [progsData, persData, schemesData, plansData, offsData] = await Promise.all([
        apiFetch<AcademicProgram[]>('/academy/admin/programs', { token, cache: 'no-store' }),
        apiFetch<AcademicPeriod[]>('/academy/admin/periods', { token, cache: 'no-store' }),
        apiFetch<GradingScheme[]>('/academy/admin/grading-schemes', { token, cache: 'no-store' }),
        apiFetch<StudyPlan[]>('/academy/admin/study-plans', { token, cache: 'no-store' }),
        apiFetch<PeriodOffering[]>('/academy/admin/offerings', { token, cache: 'no-store' }),
      ]);
      setPrograms(Array.isArray(progsData) ? progsData : []);
      setPeriods(Array.isArray(persData) ? persData : []);
      setSchemes(Array.isArray(schemesData) ? schemesData : []);
      setStudyPlans(Array.isArray(plansData) ? plansData : []);
      setOfferings(Array.isArray(offsData) ? offsData : []);

      if (plansData && plansData.length > 0 && !selectedPlanId) {
        setSelectedPlanId(plansData[0].id);
      }
    } catch (err) {
      console.error(err);
      toast.error('Error al sincronizar datos institucionales de la academia');
    } finally {
      setLoading(false);
    }
  }, [token, selectedPlanId]);

  useEffect(() => {
    if (token && isAuthenticated) {
      loadAll();
    }
  }, [token, isAuthenticated, loadAll]);

  const activePlan = useMemo(() => {
    return studyPlans.find((p) => p.id === selectedPlanId) || studyPlans[0] || null;
  }, [studyPlans, selectedPlanId]);

  const filteredPrograms = useMemo(() => {
    return programs.filter((p) => p.name.toLowerCase().includes(search.toLowerCase()) || p.code.toLowerCase().includes(search.toLowerCase()));
  }, [programs, search]);

  const filteredPeriods = useMemo(() => {
    return periods.filter((p) => p.name.toLowerCase().includes(search.toLowerCase()) || p.code.toLowerCase().includes(search.toLowerCase()));
  }, [periods, search]);

  const filteredOfferings = useMemo(() => {
    return offerings.filter((o) => (o.subject_name || '').toLowerCase().includes(search.toLowerCase()) || (o.docente_name || '').toLowerCase().includes(search.toLowerCase()));
  }, [offerings, search]);

  if (loading) {
    return (
      <div className="p-6 space-y-4 bg-[hsl(var(--bg-primary))] min-h-screen">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <DSSkeleton key={i} className="h-28 rounded-lg" />
          ))}
        </div>
        <DSSkeleton className="h-[450px] rounded-lg" />
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-[hsl(var(--bg-primary))] text-[hsl(var(--foreground))]">
      <WorkspaceToolbar
        breadcrumbs={[
          { label: 'Academia', icon: GraduationCap },
          { label: 'Gestión Institucional & ERP Académico', icon: Sliders },
        ]}
      />

      {/* Hero Header */}
      <div className="px-6 py-4 border-b border-[hsl(var(--border))] bg-[hsl(var(--surface-1))]">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-2xs font-bold uppercase tracking-widest px-2 py-0.5 rounded bg-[hsl(var(--primary)/0.1)] text-[hsl(var(--primary))] border border-[hsl(var(--primary)/0.2)]">
                Panel de Administración Institucional
              </span>
              <span className="text-2xs font-semibold text-[hsl(var(--text-secondary))]">
                Super-PRO Academy Core
              </span>
            </div>
            <h1 className="text-2xl font-bold tracking-tight mt-1 text-[hsl(var(--foreground))]">
              Configuración de Procesos Formativos & Malla Curricular
            </h1>
            <p className="text-xs text-[hsl(var(--text-secondary))] mt-0.5">
              Administra programas académicos (Cursos, Diplomados, Carreras, Maestrías), períodos semestrales, esquemas de cortes porcentuales y créditos educativos.
            </p>
          </div>

          <div className="flex items-center gap-2">
            {activeTab === 'programs' && (
              <button
                type="button"
                onClick={() => {
                  setSelectedProgram(null);
                  setProgramDrawerOpen(true);
                }}
                className="px-4 py-2 text-xs font-bold rounded-lg bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] flex items-center gap-1.5 hover:opacity-90 shadow-md transition-all"
              >
                <Plus className="size-4" />
                <span>Nuevo Proceso Formativo</span>
              </button>
            )}
            {activeTab === 'periods' && (
              <button
                type="button"
                onClick={() => {
                  setSelectedPeriod(null);
                  setPeriodDrawerOpen(true);
                }}
                className="px-4 py-2 text-xs font-bold rounded-lg bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] flex items-center gap-1.5 hover:opacity-90 shadow-md transition-all"
              >
                <Plus className="size-4" />
                <span>Aperturar Período</span>
              </button>
            )}
            {activeTab === 'grading' && (
              <button
                type="button"
                onClick={() => {
                  setSelectedScheme(null);
                  setSchemeDrawerOpen(true);
                }}
                className="px-4 py-2 text-xs font-bold rounded-lg bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] flex items-center gap-1.5 hover:opacity-90 shadow-md transition-all"
              >
                <Plus className="size-4" />
                <span>Nuevo Esquema de Cortes</span>
              </button>
            )}
            {activeTab === 'curriculum' && activePlan && (
              <button
                type="button"
                onClick={() => {
                  setSubjectDrawerOpen(true);
                }}
                className="px-4 py-2 text-xs font-bold rounded-lg bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] flex items-center gap-1.5 hover:opacity-90 shadow-md transition-all"
              >
                <Plus className="size-4" />
                <span>Incorporar Materia al Pensum</span>
              </button>
            )}
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="flex items-center gap-2 mt-4 border-b border-[hsl(var(--border))] -mb-4 overflow-x-auto hide-scrollbar">
          {[
            { id: 'programs', label: 'Procesos de Formación', icon: GraduationCap, count: programs.length },
            { id: 'periods', label: 'Períodos & Semestres', icon: Calendar, count: periods.length },
            { id: 'grading', label: 'Esquemas de Cortes (30-30-40)', icon: Award, count: schemes.length },
            { id: 'curriculum', label: 'Malla Curricular & Créditos', icon: BookOpen, count: activePlan?.subjects.length || 0 },
            { id: 'offerings', label: 'Comisiones & Calificaciones', icon: Users, count: offerings.length },
            { id: 'enrollments', label: 'Matrículas de Estudiantes', icon: UserCheck, count: offerings.reduce((acc, o) => acc + (o.enrolled_count || 0), 0) },
          ].map((tab) => {
            const active = activeTab === tab.id;
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                type="button"
                onClick={() => {
                  setActiveTab(tab.id as AdminTab);
                  setSearch('');
                }}
                className={clsx(
                  'px-3.5 py-2.5 text-xs font-bold border-b-2 flex items-center gap-2 transition-all shrink-0',
                  active
                    ? 'border-[hsl(var(--primary))] text-[hsl(var(--primary))] bg-[hsl(var(--primary)/0.05)]'
                    : 'border-transparent text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--foreground))] hover:border-[hsl(var(--border))]'
                )}
              >
                <Icon className="size-4" />
                <span>{tab.label}</span>
                <span className={clsx('px-1.5 py-0.5 rounded-full text-[10px]', active ? 'bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))]' : 'bg-[hsl(var(--surface-2))]')}>
                  {tab.count}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Main Content Area */}
      <div className="p-6 flex-1 overflow-y-auto">
        {/* Search bar for lists */}
        {activeTab !== 'curriculum' && (
          <div className="mb-4 max-w-md relative">
            <Search className="size-4 absolute left-3 top-2.5 text-[hsl(var(--text-secondary))]" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Buscar por código, nombre o docente..."
              className="w-full pl-9 pr-4 py-2 text-xs rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] focus:outline-none focus:ring-1 focus:ring-[hsl(var(--primary))]"
            />
          </div>
        )}

        {/* 1. Tab: Programas Formativos */}
        {activeTab === 'programs' && (
          <div className="space-y-4">
            {filteredPrograms.length === 0 ? (
              <EmptyState
                icon={GraduationCap}
                title="No hay programas registrados"
                description="Crea carreras, diplomados, cursos libres o maestrías para gobernar la oferta educativa."
                actionLabel="Crear Primer Programa"
                onAction={() => {
                  setSelectedProgram(null);
                  setProgramDrawerOpen(true);
                }}
              />
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {filteredPrograms.map((p) => (
                  <div
                    key={p.id}
                    className="p-4 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] hover:border-[hsl(var(--primary)/0.5)] transition-all shadow-sm flex flex-col justify-between"
                  >
                    <div>
                      <div className="flex items-start justify-between gap-2">
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] text-[hsl(var(--primary))]">
                          {p.program_type.replace('_', ' ')}
                        </span>
                        <span className="text-[11px] font-mono text-[hsl(var(--text-secondary))] font-bold">
                          {p.code}
                        </span>
                      </div>
                      <h3 className="text-base font-bold text-[hsl(var(--foreground))] mt-2">{p.name}</h3>
                      {p.level_name && (
                        <p className="text-xs text-[hsl(var(--text-secondary))] mt-0.5">{p.level_name}</p>
                      )}
                      <p className="text-xs text-[hsl(var(--text-secondary))] mt-2 line-clamp-2">
                        {p.description || 'Sin descripción detallada.'}
                      </p>

                      <div className="grid grid-cols-2 gap-2 mt-4 pt-3 border-t border-[hsl(var(--border))] text-xs">
                        <div className="flex flex-col">
                          <span className="text-[10px] uppercase font-bold text-[hsl(var(--text-secondary))]">Duración</span>
                          <span className="font-semibold">
                            {p.total_duration_units} {p.total_duration_type}
                          </span>
                        </div>
                        <div className="flex flex-col">
                          <span className="text-[10px] uppercase font-bold text-[hsl(var(--text-secondary))]">Malla</span>
                          <span className="font-semibold">{p.study_plans_count || 0} pensums</span>
                        </div>
                        <div className="flex flex-col">
                          <span className="text-[10px] uppercase font-bold text-[hsl(var(--text-secondary))]">Docentes</span>
                          <span className="font-semibold">{p.has_teachers ? 'Requeridos' : 'Autodidacta'}</span>
                        </div>
                        <div className="flex flex-col">
                          <span className="text-[10px] uppercase font-bold text-[hsl(var(--text-secondary))]">Calificación</span>
                          <span className="font-semibold">{p.teachers_can_grade ? 'Por Docentes' : 'Automática'}</span>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center justify-end gap-2 mt-4 pt-3 border-t border-[hsl(var(--border))]">
                      <button
                        type="button"
                        onClick={() => {
                          setSelectedProgram(p);
                          setProgramDrawerOpen(true);
                        }}
                        className="px-3 py-1.5 text-xs font-bold rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] hover:bg-[hsl(var(--surface-1))] flex items-center gap-1 transition-colors"
                      >
                        <Edit2 className="size-3.5" />
                        <span>Configurar</span>
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* 2. Tab: Períodos Académicos */}
        {activeTab === 'periods' && (
          <div className="space-y-4">
            {filteredPeriods.length === 0 ? (
              <EmptyState
                icon={Calendar}
                title="No hay períodos académicos"
                description="Apertura el ciclo lectivo semestral o modular para asociar comisiones y fechas de corte."
                actionLabel="Aperturar Período"
                onAction={() => {
                  setSelectedPeriod(null);
                  setPeriodDrawerOpen(true);
                }}
              />
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {filteredPeriods.map((per) => (
                  <div
                    key={per.id}
                    className="p-4 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] shadow-sm flex flex-col justify-between"
                  >
                    <div>
                      <div className="flex items-center justify-between">
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-[hsl(var(--primary)/0.1)] text-[hsl(var(--primary))] border border-[hsl(var(--primary)/0.2)]">
                          {per.period_type}
                        </span>
                        <span
                          className={clsx(
                            'px-2 py-0.5 rounded text-[10px] font-bold uppercase',
                            per.status === 'open'
                              ? 'bg-[hsl(var(--success)/0.15)] text-[hsl(var(--success))]'
                              : per.status === 'grading'
                              ? 'bg-[hsl(var(--warning)/0.15)] text-[hsl(var(--warning))]'
                              : 'bg-[hsl(var(--surface-2))] text-[hsl(var(--text-secondary))]'
                          )}
                        >
                          {per.status}
                        </span>
                      </div>
                      <h3 className="text-base font-bold text-[hsl(var(--foreground))] mt-2">{per.name}</h3>
                      <p className="text-xs font-mono font-bold text-[hsl(var(--text-secondary))] mt-0.5">
                        Código: {per.code}
                      </p>

                      <div className="space-y-1.5 mt-3 pt-3 border-t border-[hsl(var(--border))] text-xs text-[hsl(var(--text-secondary))]">
                        <div className="flex justify-between">
                          <span>Clases:</span>
                          <span className="font-semibold text-[hsl(var(--foreground))]">
                            {per.start_date} al {per.end_date}
                          </span>
                        </div>
                        {per.grading_deadline && (
                          <div className="flex justify-between">
                            <span>Límite Notas:</span>
                            <span className="font-semibold text-[hsl(var(--destructive))]">
                              {per.grading_deadline}
                            </span>
                          </div>
                        )}
                        <div className="flex justify-between">
                          <span>Comisiones Activas:</span>
                          <span className="font-bold text-[hsl(var(--primary))]">
                            {per.offerings_count || 0}
                          </span>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center justify-end gap-2 mt-4 pt-3 border-t border-[hsl(var(--border))]">
                      <button
                        type="button"
                        onClick={() => {
                          setSelectedPeriod(per);
                          setPeriodDrawerOpen(true);
                        }}
                        className="px-3 py-1.5 text-xs font-bold rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] hover:bg-[hsl(var(--surface-1))] flex items-center gap-1 transition-colors"
                      >
                        <Edit2 className="size-3.5" />
                        <span>Editar Fechas</span>
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* 3. Tab: Esquemas de Cortes de Calificación */}
        {activeTab === 'grading' && (
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {schemes.map((s) => (
                <div
                  key={s.id}
                  className="p-4 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] shadow-sm flex flex-col justify-between"
                >
                  <div>
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-mono font-bold text-[hsl(var(--primary))]">
                        Escala 0 - {s.scale_max} (Aprobatoria: {s.passing_grade})
                      </span>
                      {s.is_default && (
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-[hsl(var(--success)/0.15)] text-[hsl(var(--success))]">
                          ★ Por Defecto
                        </span>
                      )}
                    </div>
                    <h3 className="text-base font-bold text-[hsl(var(--foreground))] mt-2">{s.name}</h3>
                    <p className="text-xs text-[hsl(var(--text-secondary))] mt-1 line-clamp-2">
                      {s.description || 'Sin notas descriptivas.'}
                    </p>

                    {/* Desglose de Cortes */}
                    <div className="mt-4 pt-3 border-t border-[hsl(var(--border))] space-y-2">
                      <span className="text-[10px] uppercase font-bold text-[hsl(var(--text-secondary))]">
                        Distribución de Cortes ({s.cuts.length}):
                      </span>
                      <div className="flex flex-col gap-1.5">
                        {s.cuts.map((c) => (
                          <div
                            key={c.id || c.name}
                            className="p-2 rounded bg-[hsl(var(--surface-2))] border border-[hsl(var(--border))] flex items-center justify-between text-xs"
                          >
                            <span className="font-semibold text-[hsl(var(--foreground))]">{c.name}</span>
                            <span className="font-bold text-[hsl(var(--primary))] px-1.5 py-0.5 rounded bg-[hsl(var(--surface-1))]">
                              {c.weight_percent}%
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center justify-end gap-2 mt-4 pt-3 border-t border-[hsl(var(--border))]">
                    <button
                      type="button"
                      onClick={() => {
                        setSelectedScheme(s);
                        setSchemeDrawerOpen(true);
                      }}
                      className="px-3 py-1.5 text-xs font-bold rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] hover:bg-[hsl(var(--surface-1))] flex items-center gap-1 transition-colors"
                    >
                      <Edit2 className="size-3.5" />
                      <span>Modificar Cortes</span>
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 4. Tab: Malla Curricular & Créditos Educativos */}
        {activeTab === 'curriculum' && (
          <div className="space-y-4">
            {studyPlans.length === 0 ? (
              <EmptyState
                icon={BookOpen}
                title="No hay planes de estudio activos"
                description="Crea un programa primero para generar su pensum y organizar asignaturas con créditos educativos."
              />
            ) : (
              <div className="space-y-4">
                {/* Selector de Plan */}
                <div className="p-4 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] flex flex-wrap items-center justify-between gap-4">
                  <div className="flex items-center gap-3">
                    <span className="text-xs font-bold uppercase tracking-wider text-[hsl(var(--text-secondary))]">
                      Plan / Pensum:
                    </span>
                    <select
                      value={selectedPlanId}
                      onChange={(e) => setSelectedPlanId(e.target.value)}
                      className="px-3 py-1.5 text-sm font-bold rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))]"
                    >
                      {studyPlans.map((sp) => (
                        <option key={sp.id} value={sp.id}>
                          {sp.name} — {sp.program_name || 'Programa'} ({sp.total_credits} créditos totales)
                        </option>
                      ))}
                    </select>
                  </div>

                  {activePlan && (
                    <div className="flex items-center gap-3 text-xs">
                      <span className="px-3 py-1 rounded-lg bg-[hsl(var(--primary)/0.1)] text-[hsl(var(--primary))] font-bold">
                        Total Créditos Requeridos: {activePlan.total_credits}
                      </span>
                      <span className="px-3 py-1 rounded-lg bg-[hsl(var(--surface-2))] font-bold text-[hsl(var(--text-secondary))]">
                        {activePlan.subjects.length} Asignaturas
                      </span>
                    </div>
                  )}
                </div>

                {/* Tabla de Materias con Créditos */}
                {activePlan && activePlan.subjects.length > 0 ? (
                  <div className="rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] overflow-hidden shadow-sm">
                    <table className="w-full text-left border-collapse text-xs">
                      <thead>
                        <tr className="border-b border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] text-[hsl(var(--text-secondary))] font-bold uppercase tracking-wider text-[11px]">
                          <th className="p-3">Código</th>
                          <th className="p-3">Asignatura</th>
                          <th className="p-3 text-center">Nivel / Semestre</th>
                          <th className="p-3 text-center">Créditos Educativos</th>
                          <th className="p-3 text-center">Intensidad Horaria</th>
                          <th className="p-3">Prerrequisitos</th>
                          <th className="p-3 text-right">Carácter</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[hsl(var(--border))]">
                        {activePlan.subjects.map((sub) => (
                          <tr key={sub.id} className="hover:bg-[hsl(var(--surface-2)/0.5)] transition-colors">
                            <td className="p-3 font-mono font-bold text-[hsl(var(--primary))]">{sub.code}</td>
                            <td className="p-3 font-bold text-[hsl(var(--foreground))]">{sub.name}</td>
                            <td className="p-3 text-center font-semibold">Semestre {sub.level_number}</td>
                            <td className="p-3 text-center">
                              <span className="px-2.5 py-1 rounded font-bold text-xs bg-[hsl(var(--primary)/0.1)] text-[hsl(var(--primary))] border border-[hsl(var(--primary)/0.2)]">
                                {sub.credits} Créditos
                              </span>
                            </td>
                            <td className="p-3 text-center text-[hsl(var(--text-secondary))]">
                              {sub.weekly_hours_theory}h T / {sub.weekly_hours_practice}h P / {sub.weekly_hours_independent}h I
                            </td>
                            <td className="p-3 text-[hsl(var(--text-secondary))]">
                              {sub.prerequisite_codes && sub.prerequisite_codes.length > 0
                                ? sub.prerequisite_codes.join(', ')
                                : '—'}
                            </td>
                            <td className="p-3 text-right">
                              {sub.is_mandatory ? (
                                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-[hsl(var(--surface-2))] text-[hsl(var(--foreground))]">
                                  Obligatoria
                                </span>
                              ) : (
                                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-[hsl(var(--surface-2))] text-[hsl(var(--text-secondary))]">
                                  Electiva
                                </span>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <EmptyState
                    icon={BookOpen}
                    title="Plan de estudio sin asignaturas"
                    description="Incorpora las materias del primer semestre y asigna sus créditos educativos."
                    actionLabel="Incorporar Primera Materia"
                    onAction={() => setSubjectDrawerOpen(true)}
                  />
                )}
              </div>
            )}
          </div>
        )}

        {/* 5. Tab: Comisiones & Sábana de Calificaciones */}
        {activeTab === 'offerings' && (
          <div className="space-y-4">
            {filteredOfferings.length === 0 ? (
              <EmptyState
                icon={Users}
                title="No hay comisiones aperturadas"
                description="Las comisiones conectan un semestre con una asignatura de la malla, un docente asignado y un esquema de cortes."
              />
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {filteredOfferings.map((off) => (
                  <div
                    key={off.id}
                    className="p-4 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] shadow-sm flex flex-col justify-between"
                  >
                    <div>
                      <div className="flex items-center justify-between">
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-[hsl(var(--surface-2))] text-[hsl(var(--primary))] font-mono">
                          {off.subject_code} • {off.credits} Créditos
                        </span>
                        <span className="text-2xs font-bold text-[hsl(var(--text-secondary))]">
                          {off.period_code}
                        </span>
                      </div>

                      <h3 className="text-base font-bold text-[hsl(var(--foreground))] mt-2">{off.subject_name}</h3>
                      <p className="text-xs text-[hsl(var(--text-secondary))] mt-0.5">
                        Docente: <strong className="text-[hsl(var(--foreground))]">{off.docente_name}</strong>
                      </p>

                      <div className="mt-3 pt-3 border-t border-[hsl(var(--border))] space-y-1 text-xs text-[hsl(var(--text-secondary))]">
                        <div className="flex justify-between">
                          <span>Grupo:</span>
                          <span className="font-semibold text-[hsl(var(--foreground))]">{off.group_name}</span>
                        </div>
                        <div className="flex justify-between">
                          <span>Esquema Evaluativo:</span>
                          <span className="font-semibold text-[hsl(var(--foreground))]">{off.grading_scheme_name}</span>
                        </div>
                        <div className="flex justify-between">
                          <span>Estudiantes con Acta:</span>
                          <span className="font-bold text-[hsl(var(--primary))]">{off.enrolled_count} matriculados</span>
                        </div>
                      </div>
                    </div>

                    <div className="flex flex-col gap-2 mt-4 pt-3 border-t border-[hsl(var(--border))]">
                      <button
                        type="button"
                        onClick={() => {
                          setSelectedOfferingId(off.id);
                          setGradesDrawerOpen(true);
                        }}
                        className="w-full py-2 text-xs font-bold rounded-lg bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] flex items-center justify-center gap-1.5 shadow transition-all hover:opacity-95"
                      >
                        <Award className="size-3.5" />
                        <span>Ver Sábana de Notas & Calificar</span>
                      </button>
                      <div className="flex gap-2">
                        <button
                          type="button"
                          onClick={() => {
                            setSelectedOfferingForAction(off);
                            setEnrollmentDrawerOpen(true);
                          }}
                          className="flex-1 py-1.5 text-xs font-semibold rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] text-[hsl(var(--foreground))] hover:bg-[hsl(var(--surface-1))] flex items-center justify-center gap-1 transition-colors"
                        >
                          <UserPlus className="size-3.5 text-[hsl(var(--primary))]" />
                          <span>Matricular</span>
                        </button>
                        <button
                          type="button"
                          onClick={() => {
                            setSelectedOfferingForAction(off);
                            setCloseGradesDrawerOpen(true);
                          }}
                          className="flex-1 py-1.5 text-xs font-semibold rounded-lg border border-[hsl(var(--border))] bg-[hsl(var(--surface-2))] text-[hsl(var(--foreground))] hover:bg-[hsl(var(--surface-1))] flex items-center justify-center gap-1 transition-colors"
                        >
                          <Lock className="size-3.5 text-[hsl(var(--destructive))]" />
                          <span>Cerrar Acta</span>
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* 6. Tab: Matrícula de Estudiantes */}
        {activeTab === 'enrollments' && (
          <div className="space-y-4">
            {filteredOfferings.length === 0 ? (
              <EmptyState
                icon={UserCheck}
                title="No hay comisiones disponibles para matrícula"
                description="Primero debes aperturar comisiones en el tab anterior para poder registrar y gestionar la matrícula de estudiantes."
              />
            ) : (
              <div className="rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] overflow-hidden shadow-sm">
                <table className="w-full text-xs text-left">
                  <thead className="bg-[hsl(var(--surface-2))] border-b border-[hsl(var(--border))] text-[hsl(var(--text-secondary))] font-bold uppercase tracking-wider">
                    <tr>
                      <th className="p-3">Código</th>
                      <th className="p-3">Asignatura</th>
                      <th className="p-3">Período</th>
                      <th className="p-3">Docente</th>
                      <th className="p-3 text-center">Matriculados</th>
                      <th className="p-3 text-center">Estado</th>
                      <th className="p-3 text-right">Acciones</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[hsl(var(--border))]">
                    {filteredOfferings.map((off) => (
                      <tr key={off.id} className="hover:bg-[hsl(var(--surface-2))] transition-colors">
                        <td className="p-3 font-mono font-bold text-[hsl(var(--primary))]">{off.subject_code}</td>
                        <td className="p-3 font-bold text-[hsl(var(--foreground))]">{off.subject_name} ({off.group_name})</td>
                        <td className="p-3 text-[hsl(var(--text-secondary))]">{off.period_code}</td>
                        <td className="p-3 text-[hsl(var(--foreground))]">{off.docente_name || 'Sin docente'}</td>
                        <td className="p-3 text-center">
                          <span className="font-bold text-[hsl(var(--primary))]">{off.enrolled_count}</span> / {off.quota_max}
                        </td>
                        <td className="p-3 text-center">
                          <span className={clsx(
                            'px-2 py-0.5 rounded-full text-[10px] font-bold uppercase',
                            off.status === 'closed'
                              ? 'bg-[hsl(var(--destructive)/0.1)] text-[hsl(var(--destructive))]'
                              : 'bg-[hsl(var(--primary)/0.1)] text-[hsl(var(--primary))]'
                          )}>
                            {off.status}
                          </span>
                        </td>
                        <td className="p-3 text-right">
                          <button
                            type="button"
                            onClick={() => {
                              setSelectedOfferingForAction(off);
                              setEnrollmentDrawerOpen(true);
                            }}
                            className="px-3 py-1.5 rounded-lg bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))] text-xs font-semibold hover:opacity-90 transition-opacity inline-flex items-center gap-1.5"
                          >
                            <UserPlus className="size-3.5" />
                            <span>Gestionar Matrícula</span>
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </div>

      {/* ── Drawers Laterales Canónicos (0 Modals Centrados) ──────────────── */}
      <ProgramDrawer
        open={programDrawerOpen}
        onClose={() => setProgramDrawerOpen(false)}
        program={selectedProgram}
        token={token}
        onSuccess={() => loadAll()}
      />

      <GradingSchemeDrawer
        open={schemeDrawerOpen}
        onClose={() => setSchemeDrawerOpen(false)}
        scheme={selectedScheme}
        token={token}
        onSuccess={() => loadAll()}
      />

      <AcademicPeriodDrawer
        open={periodDrawerOpen}
        onClose={() => setPeriodDrawerOpen(false)}
        period={selectedPeriod}
        token={token}
        onSuccess={() => loadAll()}
      />

      {activePlan && (
        <StudyPlanSubjectDrawer
          open={subjectDrawerOpen}
          onClose={() => setSubjectDrawerOpen(false)}
          studyPlanId={activePlan.id}
          subject={null}
          schemes={schemes}
          token={token}
          onSuccess={() => loadAll()}
        />
      )}

      <OfferingGradesDrawer
        open={gradesDrawerOpen}
        onClose={() => setGradesDrawerOpen(false)}
        offeringId={selectedOfferingId}
        token={token}
        onSuccess={() => loadAll()}
      />

      <StudentEnrollmentDrawer
        open={enrollmentDrawerOpen}
        onClose={() => setEnrollmentDrawerOpen(false)}
        offering={selectedOfferingForAction}
        token={token}
        onEnrollmentChanged={() => loadAll()}
      />

      <CloseGradesDrawer
        open={closeGradesDrawerOpen}
        onClose={() => setCloseGradesDrawerOpen(false)}
        offering={selectedOfferingForAction}
        token={token}
        onClosedSuccess={() => loadAll()}
      />
    </div>
  );
}
