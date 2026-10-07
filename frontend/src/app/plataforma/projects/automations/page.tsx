import Link from "next/link";
import { ArrowRight, Workflow, Layers3 } from "lucide-react";
import ProjectsShell from "@/components/projects/ProjectsShell";

/**
 * Compatibility landing for the former global automation screen.
 * Project rules are managed in their project context so the route cannot
 * accidentally expose or mutate platform-wide automation rules.
 */
export default function ProjectAutomationsPage() {
  return (
    <ProjectsShell
      breadcrumbs={[
        { label: "Proyectos", icon: Layers3 },
        { label: "Automatizaciones", icon: Workflow },
      ]}
    >
      <main className="mx-auto flex min-h-full w-full max-w-4xl items-center px-4 py-10 sm:px-6">
        <section className="w-full rounded-2xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-1))] p-6 shadow-sm sm:p-8">
          <div className="mb-5 flex size-12 items-center justify-center rounded-xl border border-[hsl(var(--primary)/0.2)] bg-[hsl(var(--primary)/0.1)] text-[hsl(var(--primary))]">
            <Workflow aria-hidden="true" size={24} />
          </div>
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-[hsl(var(--muted-foreground))]">
            Automatizaciones de proyectos
          </p>
          <h1 className="mt-2 text-2xl font-semibold tracking-tight text-[hsl(var(--foreground))] sm:text-3xl">
            Administra las reglas desde su proyecto
          </h1>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-[hsl(var(--muted-foreground))]">
            Las reglas de Proyectos tienen alcance y permisos propios. Abre un
            proyecto y selecciona <span className="font-medium text-[hsl(var(--foreground))]">Automatizaciones</span> para
            revisar sus reglas, crear una nueva o previsualizar sus condiciones.
            La ejecución de efectos está reservada a personas con permiso de gestión.
          </p>
          <Link
            href="/plataforma/projects"
            className="mt-6 inline-flex min-h-11 items-center gap-2 rounded-lg bg-[hsl(var(--primary))] px-4 py-2 text-sm font-semibold text-[hsl(var(--primary-foreground))] transition-opacity hover:opacity-90 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[hsl(var(--ring))] focus-visible:ring-offset-2 focus-visible:ring-offset-[hsl(var(--surface-1))]"
          >
            Ir a mis proyectos
            <ArrowRight aria-hidden="true" size={16} />
          </Link>
        </section>
      </main>
    </ProjectsShell>
  );
}
