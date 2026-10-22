# HALLAZGOS REVISIÓN FRONTEND CCF - 21/10/2026
Fecha: 21 de Octubre 2026  
Alcance: Todo el frontend (`/root/ccf/frontend/src`)  
Tipo: Solo documentación (sin correcciones)


## 1. RESUMEN EJECUTIVO
- Archivos TS: ~18,796 (incluyendo node_modules)
- Archivos TSX: 1,039 (fuera de node_modules)
- Hallazgos documentados a continuación

## 2. ALERTDIALOG / MODALES CENTRADOS
---
/root/ccf/frontend/src/components/projects/ProjectAnyDocDrawer.test.tsx:64:    // Regla de Arquitectura: Cero modales centrados o AlertDialog
/root/ccf/frontend/src/components/projects/ProjectLabelsDrawer.test.tsx:168:  it("handles inline delete without any AlertDialog/modals", async () => {
/root/ccf/frontend/src/components/projects/ProjectLabelsDrawer.tsx:627:                    /* Inline Delete Confirmation (NO modals/AlertDialog) */


## 3. USO DE fetch() CRUDO (NO apiFetch)
---
/root/ccf/frontend/src/lib/cms/revalidate.ts:13:    const res = await fetch("/api/cms/revalidate", {
/root/ccf/frontend/src/lib/vitals.ts:15:    fetch(url, {
/root/ccf/frontend/src/lib/serverApi.ts:21:  const response = await fetch(apiUrl(path), {
/root/ccf/frontend/src/lib/whiteboardExport.ts:83:    const response = await fetch(dataUrl);
/root/ccf/frontend/src/components/public/cms/sections/forms-interactive.tsx:41:          const res = await fetch(actionUrl, {
/root/ccf/frontend/src/app/sitemap.xml/route.ts:14:    const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || ""}/api/cms/v2/public/sites/default/pages`, {
/root/ccf/frontend/src/app/api/tasks/route.ts:7:  const response = await fetch(GRAPHQL_ENDPOINT, {
/root/ccf/frontend/src/app/api/crm/resources/automation-edges/_shared.ts:32:  const response = await fetch(buildBackendUrl(path, request), {


## 4. COLORES HARDCODEADOS (Tailwind directos)
---
/root/ccf/frontend/src/design/ACCESSIBILITY.md:154:bg-blue-500    // Prohibido por reglas canónicas CCF


## 5. TEXTO/CLASES CON COLORES HARDCODEADOS
---
/root/ccf/frontend/src/design/ACCESSIBILITY.md:153:text-gray-400  // No cumple 4.5:1 ni sigue el Design System


## 6. USO DE 'any' (TypeScript)
---
/root/ccf/frontend/src/lib/cms/versionDiff.ts:495:      kind: anyChange ? "changed" : "unchanged",
/root/ccf/frontend/src/app/globals.css:441:      overflow-wrap: anywhere;


## 7. console.log / console.error / debug
---
/root/ccf/frontend/src/lib/cms/versionDiff.test.ts:305:    // ``console.warn`` to keep test output clean and assert the
/root/ccf/frontend/src/lib/cms/versionDiff.ts:237:    console.warn(`${orphanCount} section(s) have no section_key/id`);
/root/ccf/frontend/src/lib/__tests__/projects-views-integration.test.tsx:282:    // Silence console.error so vitest output no se llene de logs esperados.
/root/ccf/frontend/src/lib/http.test.ts:226:  it("error de red sin silent → console.error se llama", async () => {
/root/ccf/frontend/src/lib/http.ts:180:      console.error(`[API_NETWORK_ERROR] ${method} ${path}:`, errObj.message);
/root/ccf/frontend/src/lib/http.ts:214:    if (!silent) console.error(`[API_FAILURE] ${response.status} ${method} ${path}:`, parsed);
/root/ccf/frontend/src/components/ModuleErrorBoundary.tsx:29:    console.error(`[${this.props.moduleName}] Error caught:`, error, errorInfo);
/root/ccf/frontend/src/components/ModuleErrorBoundary.tsx:106:        console.error(`[${moduleName}]`, e);
/root/ccf/frontend/src/components/ui/UniversalWikiView.stories.tsx:42:    onSave: (content: string) => console.log('Saved:', content),
/root/ccf/frontend/src/components/ui/inline-editors/inline-editors.stories.tsx:20:  render: () => <InlineTextInput value="Juan Pérez" onChange={(v) => console.log(v)} />,
/root/ccf/frontend/src/components/ui/inline-editors/inline-editors.stories.tsx:25:  render: () => <InlineTextInput value="" placeholder="Haz clic para editar..." onChange={(v) => console.log(v)} />,
/root/ccf/frontend/src/components/ui/inline-editors/inline-editors.stories.tsx:30:  render: () => <InlineTextInput value="Valor bloqueado" disabled onChange={(v) => console.log(v)} />,
/root/ccf/frontend/src/components/ui/inline-editors/inline-editors.stories.tsx:40:      onChange={(v) => console.log(v)}
/root/ccf/frontend/src/components/ui/inline-editors/inline-editors.stories.tsx:48:    <InlineTextArea value="" placeholder="Añade una descripción..." onChange={(v) => console.log(v)} rows={4} />
/root/ccf/frontend/src/components/ui/inline-editors/inline-editors.stories.tsx:55:    <InlineTextArea value="Descripción bloqueada" disabled onChange={(v) => console.log(v)} />
/root/ccf/frontend/src/components/ui/inline-editors/inline-editors.stories.tsx:63:  render: () => <InlineStatusPicker value="in_progress" onChange={(v) => console.log(v)} />,
/root/ccf/frontend/src/components/ui/inline-editors/inline-editors.stories.tsx:68:  render: () => <InlineStatusPicker value="todo" onChange={(v) => console.log(v)} size="sm" />,
/root/ccf/frontend/src/components/ui/inline-editors/inline-editors.stories.tsx:75:      <InlineStatusPicker value="todo" onChange={(v) => console.log(v)} />
/root/ccf/frontend/src/components/ui/inline-editors/inline-editors.stories.tsx:76:      <InlineStatusPicker value="in_progress" onChange={(v) => console.log(v)} />
/root/ccf/frontend/src/components/ui/inline-editors/inline-editors.stories.tsx:77:      <InlineStatusPicker value="review" onChange={(v) => console.log(v)} />
/root/ccf/frontend/src/components/ui/inline-editors/inline-editors.stories.tsx:78:      <InlineStatusPicker value="completed" onChange={(v) => console.log(v)} />
/root/ccf/frontend/src/components/ui/inline-editors/inline-editors.stories.tsx:87:  render: () => <InlinePriorityPicker value="high" onChange={(v) => console.log(v)} />,
/root/ccf/frontend/src/components/ui/inline-editors/inline-editors.stories.tsx:92:  render: () => <InlinePriorityPicker value="medium" onChange={(v) => console.log(v)} size="sm" />,
/root/ccf/frontend/src/components/ui/inline-editors/inline-editors.stories.tsx:99:      <InlinePriorityPicker value="low" onChange={(v) => console.log(v)} />
/root/ccf/frontend/src/components/ui/inline-editors/inline-editors.stories.tsx:100:      <InlinePriorityPicker value="medium" onChange={(v) => console.log(v)} />
/root/ccf/frontend/src/components/ui/inline-editors/inline-editors.stories.tsx:101:      <InlinePriorityPicker value="high" onChange={(v) => console.log(v)} />
/root/ccf/frontend/src/components/ui/inline-editors/inline-editors.stories.tsx:102:      <InlinePriorityPicker value="urgent" onChange={(v) => console.log(v)} />
/root/ccf/frontend/src/components/ui/inline-editors/InlineDatePicker.stories.tsx:19:    onChange: (v) => console.log('Date selected:', v),
/root/ccf/frontend/src/components/ui/inline-editors/InlineDatePicker.stories.tsx:26:    onChange: (v) => console.log('Date selected:', v),
/root/ccf/frontend/src/components/ui/inline-editors/InlineDatePicker.stories.tsx:33:    onChange: (v) => console.log('Date selected:', v),
/root/ccf/frontend/src/components/ui/inline-editors/InlineDatePicker.stories.tsx:40:    onChange: (v) => console.log('Date selected:', v),
/root/ccf/frontend/src/components/ui/inline-editors/InlineDatePicker.stories.tsx:47:    onChange: (v) => console.log('Date selected:', v),
/root/ccf/frontend/src/components/ui/RightPanel.stories.tsx:28:    onClose: () => console.log('Close panel'),
/root/ccf/frontend/src/components/ui/RightPanel.stories.tsx:53:    onClose: () => console.log('Close panel'),
/root/ccf/frontend/src/components/ui/RightPanel.stories.tsx:70:    onClose: () => console.log('Close panel'),
/root/ccf/frontend/src/components/ui/RightPanel.stories.tsx:86:    onClose: () => console.log('Close panel'),
/root/ccf/frontend/src/components/ui/StatusPicker.stories.tsx:53:      console.log('Selected status:', value);
/root/ccf/frontend/src/components/ui/StatusPicker.stories.tsx:84:      console.log('Selected priority:', value);
/root/ccf/frontend/src/components/ui/StatusPicker.stories.tsx:94:      console.log('Selected status:', value);
/root/ccf/frontend/src/components/ui/StatusPicker.stories.tsx:112:      console.log('Selected:', value);


## 8. COMPONENTES CON MODALES/DIÁLOGOS CENTRADOS (Dialog de shadcn)
---


## 9. TODO/FIXME/XXX
---
/root/ccf/frontend/src/components/projects/ProjectIndicatorsDrawer.tsx:1051:          {/* TAB 2: FORMULARIO Y ASISTENTE METODOLÓGICO CREMA */}
/root/ccf/frontend/src/components/projects/utils.ts:18: * - Filtra: requiere que TODOS los tokens de la búsqueda estén presentes en el nombre.
/root/ccf/frontend/src/components/public/cms/CmsFormRenderer.tsx:826:    // Re-valida TODO antes de enviar (incluso pasos ya visitados).
/root/ccf/frontend/src/design/revisionui-proyectos.md:20:| Calidad Backend | 7/10 | ORM puro, validación Pydantic, sin TODOs pendientes |
/root/ccf/frontend/src/design/revisionui-proyectos.md:101:| ✅ Sin TODOs pendientes | Todos los markers `PEND-*` están documentados como cerrados |
/root/ccf/frontend/src/app/plataforma/evangelism/groups/page.tsx:485: {canManageEvangelism && <option value="all" className="font-bold">✨ TODOS LOS GRUPOS ACTIVOS</option>}
/root/ccf/frontend/src/app/plataforma/evangelism/events/panels/EventAttendanceDrawer.tsx:120: placeholder="CCF-PER-ID-XXXXXX"
/root/ccf/frontend/src/app/plataforma/admin/content/courses/new/page.tsx:165:                                <p className="text-2xs font-bold text-[hsl(var(--muted-foreground))] uppercase tracking-wide mt-1">{formData.code || 'ID-XXX'} • {formData.modality}</p>
/root/ccf/frontend/src/app/plataforma/projects/[id]/page.tsx:296: *  6. Delega TODO el render-switching del `viewType` al componente
/root/ccf/frontend/src/app/plataforma/messages/_components/MessageInput.tsx:122:                    // Filtro reutilizable de personas: en menciones TODO es
/root/ccf/frontend/src/app/public/events/[event_id]/register/page.tsx:101:    // Correlativo canónico (#CCF-EVT-XXXX)


## 10. VERIFICACIÓN RUTAS /plataforma
---
Búsqueda de rutas fuera de /plataforma en app router:
/root/ccf/frontend/src/lib/cms/sanitize.test.ts:57:    const out = sanitizeCmsHtml('<a href="javascript:alert(1)">x</a>');
/root/ccf/frontend/src/lib/evangelism-downloads.test.ts:63:  it("llama apiFetchBlob con GET, crea <a> con href=objectURL + download=fallback, click → toast", async () => {
/root/ccf/frontend/src/components/cms/builder/PublicCoursesManager.tsx:306:            href="/cursos"
/root/ccf/frontend/src/components/cms/builder/PublicCoursesManager.tsx:496:                    href={`/cursos/${course.slug || course.id}`}
/root/ccf/frontend/src/components/cms/builder/PublicPastoralManager.tsx:327:              href="/pastores"
/root/ccf/frontend/src/components/cms/builder/PublicPastoralManager.tsx:494:                    href={`/pastores/${p.slug}`}
/root/ccf/frontend/src/components/cms/builder/PublicLocationsManager.tsx:321:            href="/sedes"
/root/ccf/frontend/src/components/cms/builder/PublicLocationsManager.tsx:520:                    href={
/root/ccf/frontend/src/components/cms/CmsModuleNav.tsx:140:                href={tab.href}
/root/ccf/frontend/src/components/WorkspaceLayout.test.tsx:23:        <a href={href} onClick={(event) => { onClick?.(event); event.preventDefault(); }} {...props}>{children}</a>
/root/ccf/frontend/src/components/WorkspaceToolbar.tsx:89:                                {bc.href ? <Link href={bc.href} prefetch={false}>{content}</Link> : content}
/root/ccf/frontend/src/components/ui/TableView.tsx:249:            ? <a href={url} target="_blank" rel="noopener noreferrer" className="text-[hsl(var(--primary))] hover:underline text-xs truncate block" onClick={(e) => e.stopPropagation()}>{url}</a>
/root/ccf/frontend/src/components/ui/SidePanel.tsx:95:                                    href={fullViewHref}
/root/ccf/frontend/src/components/ui/CommandCenter.tsx:55:        { id: "projects", label: "Gestión de Proyectos", icon: Layers, shortcut: "G P", group: "Acceso Rápido", action: () => router.push(PROJECTS_LIST_ROUTE) },
/root/ccf/frontend/src/components/ui/CommandCenter.tsx:175:                                                onSelect={() => runCommand(() => router.push(item.href))}
/root/ccf/frontend/src/components/WorkspaceMainSidebar.test.tsx:10:vi.mock('next/link', () => ({ default: ({ href, children, ...props }: React.AnchorHTMLAttributes<HTMLAnchorElement> & { href: string }) => <a href={href} {...props}>{children}</a> }));
/root/ccf/frontend/src/components/Footer.tsx:90:                                            href={link.href}
/root/ccf/frontend/src/components/Footer.tsx:115:                        <Link href="/" className="hover:text-white transition-colors">Sitio público</Link>
/root/ccf/frontend/src/components/Footer.tsx:116:                        <Link href="/login" className="hover:text-white transition-colors">Acceso interno</Link>
/root/ccf/frontend/src/components/ProtectedRoute.tsx:190:                    href={href}
/root/ccf/frontend/src/components/ProtectedRoute.tsx:308:                router.push('/login');
/root/ccf/frontend/src/components/ProtectedRoute.tsx:331:                href="/login"
/root/ccf/frontend/src/components/surveys/ThankYouScreen.tsx:34:          href={redirectUrl}
/root/ccf/frontend/src/components/surveys/SurveyPublicRenderer.tsx:350:          href="/"
/root/ccf/frontend/src/components/surveys/FormBuilderTab.tsx:221:                        href={`/surveys/${survey.slug || survey.id}`}
/root/ccf/frontend/src/components/Navbar.tsx:66:                    <Link href="/" className="flex items-center gap-2.5 group">
/root/ccf/frontend/src/components/Navbar.tsx:105:                                    href={item.href}
/root/ccf/frontend/src/components/Navbar.tsx:132:                                <Link href="/login" className="px-3 py-1.5 rounded-md text-xs font-semibold text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--text-primary))] dark:hover:text-white transition-colors">
/root/ccf/frontend/src/components/Navbar.tsx:135:                                <Link href="/register" className="px-3 py-1.5 rounded-md bg-[hsl(var(--primary))] text-white text-xs font-semibold shadow-md shadow-[hsl(var(--info)/20%)] hover:bg-[hsl(var(--primary))] active:scale-95 transition-all">
/root/ccf/frontend/src/components/Navbar.tsx:164:                                                href={sub.href}


## 11. HOOKS/FETCH SIN apiFetch
---
/root/ccf/frontend/src/lib/cms/revalidate.ts
/root/ccf/frontend/src/lib/vitals.ts
/root/ccf/frontend/src/lib/serverApi.ts
/root/ccf/frontend/src/lib/whiteboardExport.ts
/root/ccf/frontend/src/app/sitemap.xml/route.ts
/root/ccf/frontend/src/app/api/tasks/route.ts
/root/ccf/frontend/src/app/api/crm/resources/automation-edges/_shared.ts


## 12. PATRONES INSEGUROS / DATETIME
---
173
Usos de new Date() (muestra):
/root/ccf/frontend/src/lib/cms/heroPopup.ts:101:export function shouldRenderCmsPopup(config: Pick<NormalizedPopupProps, "startAt" | "endAt" | "showOnPaths" | "hideOnPaths">, pathname: string, now = new Date()): boolean {
/root/ccf/frontend/src/lib/mocks/projects.ts:36:  const d = new Date();
/root/ccf/frontend/src/lib/mocks/projects.ts:42:  const d = new Date();
/root/ccf/frontend/src/lib/formulaEngine.ts:200:    processed = processed.replace(/TODAY\(\)/g, () => `"${new Date().toISOString().split("T")[0]}"`);
/root/ccf/frontend/src/lib/formulaEngine.ts:201:    processed = processed.replace(/NOW\(\)/g, () => `"${new Date().toISOString()}"`);
/root/ccf/frontend/src/lib/formulaEngine.test.ts:84:    expect(out).toBe(new Date().toISOString().split("T")[0]);
/root/ccf/frontend/src/lib/notifications.test.ts:149:    const out = isRecentNotification(new Date().toISOString());
/root/ccf/frontend/src/components/ui/inline-editors/InlineDatePicker.tsx:55:  const today = new Date();
/root/ccf/frontend/src/components/ui/inline-editors/InlineDatePicker.tsx:81:  const today = new Date();
/root/ccf/frontend/src/components/ui/UniversalGanttView.test.tsx:7:const today = new Date();
/root/ccf/frontend/src/components/ui/UniversalGanttView.tsx:171:    const today = new Date();
/root/ccf/frontend/src/components/ui/UniversalCalendarView.tsx:49:    const [currentDate, setCurrentDate] = useState(new Date());
/root/ccf/frontend/src/components/ui/UniversalCalendarView.tsx:99:                        <button onClick={() => setCurrentDate(new Date())} className={clsx("px-3 text-2xs font-semibold uppercase tracking-wide transition-colors", todayButtonClassName ?? "text-[hsl(var(--text-secondary))] hover:text-[hsl(var(--primary))]")}>Hoy</button>
/root/ccf/frontend/src/components/ui/UniversalCalendarView.tsx:129:                        const isToday = day.toDateString() === new Date().toDateString();
/root/ccf/frontend/src/components/ui/UniversalCreationDrawer.tsx:89:    const [eventDate, setEventDate] = useState(() => initialData?.initialDate || new Date().toISOString().split('T')[0]);


---
FIN DEL DOCUMENTO
