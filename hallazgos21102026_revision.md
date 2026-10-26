# REVISIÓN POST-CORRECCIÓN FRONTEND CCF - 21/10/2026
Fecha: 21 de Octubre 2026  
Alcance: Todo el frontend (`/root/ccf/frontend/src`)  
Tipo: Solo documentación (comparativa post-corrección)

## 1. COMPARATIVA CON HALLAZGOS PREVIOS
---
### 1.1 AlertDialog
/root/ccf/frontend/src/components/projects/ProjectAnyDocDrawer.test.tsx:64:    // Regla de Arquitectura: Cero modales centrados o AlertDialog
/root/ccf/frontend/src/components/projects/ProjectLabelsDrawer.test.tsx:168:  it("handles inline delete without any AlertDialog/modals", async () => {
/root/ccf/frontend/src/components/projects/ProjectLabelsDrawer.tsx:627:                    /* Inline Delete Confirmation (NO modals/AlertDialog) */

### 1.2 fetch() crudo (sin apiFetch)
/root/ccf/frontend/src/lib/cms/revalidate.ts:13:    const res = await fetch("/api/cms/revalidate", {
/root/ccf/frontend/src/lib/vitals.ts:15:    fetch(url, {
/root/ccf/frontend/src/lib/serverApi.ts:21:  const response = await fetch(apiUrl(path), {
/root/ccf/frontend/src/lib/whiteboardExport.ts:83:    const response = await fetch(dataUrl);
/root/ccf/frontend/src/components/public/cms/sections/forms-interactive.tsx:41:          const res = await fetch(actionUrl, {
/root/ccf/frontend/src/app/sitemap.xml/route.ts:14:    const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || ""}/api/cms/v2/public/sites/default/pages`, {
/root/ccf/frontend/src/app/api/tasks/route.ts:7:  const response = await fetch(GRAPHQL_ENDPOINT, {
/root/ccf/frontend/src/app/api/crm/resources/automation-edges/_shared.ts:32:  const response = await fetch(buildBackendUrl(path, request), {

### 1.3 Colores hardcodeados (bg-*/text-*/border-* con colores)
1

### 1.4 Uso de 'any'
/root/ccf/frontend/src/lib/cms/versionDiff.ts:495:      kind: anyChange ? "changed" : "unchanged",
/root/ccf/frontend/src/app/globals.css:441:      overflow-wrap: anywhere;

### 1.5 console.* (excluyendo tests/stories si se desea)
/root/ccf/frontend/src/lib/cms/versionDiff.ts:237:    console.warn(`${orphanCount} section(s) have no section_key/id`);
/root/ccf/frontend/src/lib/http.ts:180:      console.error(`[API_NETWORK_ERROR] ${method} ${path}:`, errObj.message);
/root/ccf/frontend/src/lib/http.ts:214:    if (!silent) console.error(`[API_FAILURE] ${response.status} ${method} ${path}:`, parsed);
/root/ccf/frontend/src/components/ModuleErrorBoundary.tsx:29:    console.error(`[${this.props.moduleName}] Error caught:`, error, errorInfo);
/root/ccf/frontend/src/components/ModuleErrorBoundary.tsx:106:        console.error(`[${moduleName}]`, e);
/root/ccf/frontend/src/components/ui/PersonaSelect.tsx:165:                console.error("[PersonaSelect] Error cargando personas:", err);
/root/ccf/frontend/src/components/ui/PersonaSelect.tsx:195:                console.error("[PersonaSelect] Error en endpoint alternativo:", err);
/root/ccf/frontend/src/components/ui/PersonaSelect.tsx:273:                console.error("[PersonaSelect] Error al consultar persona por id:", err);
/root/ccf/frontend/src/components/ui/UniversalCreationDrawer.tsx:289:                    .catch((err) => { console.error('[UniversalCreationDrawer] Failed to create document:', err); toast.error('Error al crear documento'); });
/root/ccf/frontend/src/components/ui/UniversalCreationDrawer.tsx:299:                    }).catch((err) => { console.error('[UniversalCreationDrawer] Failed to create whiteboard:', err); toast.error('Error al crear pizarra'); });
/root/ccf/frontend/src/components/ui/UniversalCreationDrawer.tsx:318:            console.error(e);
/root/ccf/frontend/src/components/ui/CommandCenter.tsx:90:                console.error(err);
/root/ccf/frontend/src/components/ProtectedRoute.tsx:307:                console.warn("[AUTH QUALITY] No user and no token found. Redirecting to login.");
/root/ccf/frontend/src/components/ProtectedRoute.tsx:311:                    console.warn('[AUTH QUALITY] Role mismatch for ProtectedRoute. Redirecting.');
/root/ccf/frontend/src/components/ProtectedRoute.tsx:316:                    console.warn(`[AUTH QUALITY] No required permissions ${allowedPermissions}. Redirecting.`);
/root/ccf/frontend/src/components/ErrorBoundary.tsx:30:    console.error(
/root/ccf/frontend/src/components/MyEnrollments.tsx:104:          }).catch((err) => { console.error('[MyEnrollments] Failed to check-in:', err); });
/root/ccf/frontend/src/components/MyEnrollments.tsx:137:      console.error("Error loading enrollments", error);
/root/ccf/frontend/src/components/surveys/FormResponsesTab.tsx:48:            console.error('Error cargando analítica:', err);
/root/ccf/frontend/src/components/surveys/FormResponsesTab.tsx:59:            console.error('Error cargando tabla de respuestas:', err);
/root/ccf/frontend/src/components/whiteboard/WhiteboardEditor.tsx:521:                console.error("Error loading whiteboard:", err);
/root/ccf/frontend/src/components/crm/PipelineLeadSidebar.tsx:73:                console.error("Error fetching audit:", err);
/root/ccf/frontend/src/components/crm/CounselingDetailSidebar.tsx:65:            console.error("Error fetching session details", err);
/root/ccf/frontend/src/components/academy/OfferingGradesDrawer.tsx:48:      console.error(err);
/root/ccf/frontend/src/components/projects/ProjectLabelsDrawer.tsx:180:      console.error("Error fetching project labels:", err);
/root/ccf/frontend/src/components/public/cms/PublicSectionRenderer.tsx:219:    console.warn(`[CMS] Tipo de sección sin renderer público: ${type}`);
/root/ccf/frontend/src/components/public/cms/PublicSearchModal.tsx:123:        console.error("Failed to perform search:", err);
/root/ccf/frontend/src/components/public/cms/PostComments.tsx:36:      console.error("Error fetching comments:", err);
/root/ccf/frontend/src/components/CourseCatalog.tsx:89:                console.error("Error loading courses", error);
/root/ccf/frontend/src/stores/configStore.ts:45:            console.error("Failed to load workspace config", err);
/root/ccf/frontend/src/hooks/useCourseLessons.ts:39:              console.error(`Error fetching lessons for course ${courseId}`, lessonError);
/root/ccf/frontend/src/hooks/useGraphInsights.ts:44:      console.error(err);
/root/ccf/frontend/src/hooks/useNotifications.ts:31:            console.error(err);
/root/ccf/frontend/src/hooks/useNotifications.ts:60:            console.error(err);
/root/ccf/frontend/src/hooks/useNotifications.ts:75:            console.error(err);
/root/ccf/frontend/src/hooks/usePresence.ts:140:            console.error("Failed to parse presence websocket message", err);
/root/ccf/frontend/src/hooks/usePresence.ts:165:        console.error("Failed to initialize presence WebSocket", err);
/root/ccf/frontend/src/hooks/useWikiDocument.ts:76:                    console.error(err);
/root/ccf/frontend/src/hooks/useWikiDocument.ts:156:            console.error(err);
/root/ccf/frontend/src/hooks/useMeshSocket.ts:35:                console.error('Failed to parse Mesh websocket message', error);
/root/ccf/frontend/src/hooks/useStudentEnrollments.ts:50:      console.warn("Enrollments fetch warning:", err instanceof Error ? err.message : err);
/root/ccf/frontend/src/context/ConfigContext.tsx:34:            console.error("Config load failed", err);
/root/ccf/frontend/src/context/AuthContext.tsx:76:        const timer = setTimeout(() => { console.warn('[AUTH] timeout'); setLoading(false); }, 6000);
/root/ccf/frontend/src/app/donate/page.tsx:128:            console.error(error);
/root/ccf/frontend/src/app/api/analytics/web-vitals/route.ts:17:  console.info('[web-vitals]', payload)
/root/ccf/frontend/src/app/reportWebVitals.ts:17:    console.info('[web-vitals]', {
/root/ccf/frontend/src/app/plataforma/cms/announcements/page.tsx:83:            console.error(err);
/root/ccf/frontend/src/app/plataforma/cms/announcements/page.tsx:109:            console.error(err);
/root/ccf/frontend/src/app/plataforma/community/prayer/page.tsx:35:                console.error("Error fetching prayer requests:", error);
/root/ccf/frontend/src/app/plataforma/community/prayer/request/page.tsx:67:            console.error('prayer request error', error);
/root/ccf/frontend/src/app/plataforma/community/give/page.tsx:44:            console.error('donation error', error);
/root/ccf/frontend/src/app/plataforma/community/give/page.tsx:68:            console.error('prayer request error', error);
/root/ccf/frontend/src/app/plataforma/community/discover/page.tsx:32:                console.error(err);
/root/ccf/frontend/src/app/plataforma/community/events/page.tsx:34:                console.error(err);
/root/ccf/frontend/src/app/plataforma/gastos/page.tsx:82:      .catch(e => { if (e.name !== 'AbortError') { console.error(e); toast.error('Error al cargar datos'); } })
/root/ccf/frontend/src/app/plataforma/gastos/page.tsx:101:    } catch (e) { console.error(e); toast.error("Error al crear reporte"); }
/root/ccf/frontend/src/app/plataforma/gastos/page.tsx:110:    } catch (e) { console.error(e); toast.error("Error al realizar acción"); }
/root/ccf/frontend/src/app/plataforma/gastos/page.tsx:119:    } catch (e) { console.error(e); toast.error("Error al cargar datos"); }
/root/ccf/frontend/src/app/plataforma/tasks/page.tsx:95:      console.error("[Tasks] fetch failed", error);
/root/ccf/frontend/src/app/plataforma/tasks/page.tsx:120:      console.error("[Tasks] complete failed", error);
/root/ccf/frontend/src/app/plataforma/finances/page.tsx:100:            if ((e as Error)?.name !== 'AbortError') console.error('Error fetching expense reports', e);
/root/ccf/frontend/src/app/plataforma/finances/page.tsx:125:        }).catch(e => { if (e.name !== 'AbortError') { console.error(e); toast.error('Error al cargar datos'); } })
/root/ccf/frontend/src/app/plataforma/finances/transparency/page.tsx:31:            .catch(e => { if (e.name !== 'AbortError') { console.error(e); toast.error('Error al cargar datos'); } })
/root/ccf/frontend/src/app/plataforma/support/tickets/page.tsx:64:                console.error(err);
/root/ccf/frontend/src/app/plataforma/support/tickets/page.tsx:121:            console.error(err);
/root/ccf/frontend/src/app/plataforma/support/page.tsx:79:                console.error("Error fetching tickets:", err);
/root/ccf/frontend/src/app/plataforma/support/page.tsx:106:            console.error(err);
/root/ccf/frontend/src/app/plataforma/support/contact/page.tsx:52:            console.error(err);
/root/ccf/frontend/src/app/plataforma/support/kb/page.tsx:83:      console.error("Error loading KB:", err);
/root/ccf/frontend/src/app/plataforma/surveys/[id]/page.tsx:50:            console.error('Error cargando encuesta:', err);
/root/ccf/frontend/src/app/plataforma/surveys/page.tsx:58:            console.error('Error cargando encuestas:', err);
/root/ccf/frontend/src/app/plataforma/wiki/page.tsx:47:            console.error("Error fetching docs:", err);
/root/ccf/frontend/src/app/plataforma/wiki/page.tsx:93:            console.error("Error creating doc:", error);
/root/ccf/frontend/src/app/plataforma/wiki/docs/[page_key]/page.tsx:48:            console.error("Error fetching doc:", err);
/root/ccf/frontend/src/app/plataforma/whiteboard/new/page.tsx:47:      console.error("Error loading projects:", err);
/root/ccf/frontend/src/app/plataforma/whiteboard/new/page.tsx:69:      console.error("Error creating whiteboard:", err);
/root/ccf/frontend/src/app/plataforma/whiteboard/page.tsx:49:      console.error("Error loading whiteboards:", err);
/root/ccf/frontend/src/app/plataforma/whiteboard/page.tsx:70:      console.error("Error deleting whiteboard:", err);
/root/ccf/frontend/src/app/plataforma/admin/donations/[id]/page.tsx:43:                console.error("Error loading donation detail", error);
/root/ccf/frontend/src/app/plataforma/admin/donations/config/page.tsx:100:            console.error(err);
/root/ccf/frontend/src/app/plataforma/admin/settings/socials/page.tsx:61:            console.error(err);
/root/ccf/frontend/src/app/plataforma/admin/settings/experience/page.tsx:63:                console.error(err);
/root/ccf/frontend/src/app/plataforma/admin/settings/locations/page.tsx:48:            console.error(err);
/root/ccf/frontend/src/app/plataforma/admin/settings/system/page.tsx:428:            console.error("Config fetch failed", e);
/root/ccf/frontend/src/app/plataforma/admin/settings/system/page.tsx:473:            console.error(error);
/root/ccf/frontend/src/app/plataforma/admin/settings/system/page.tsx:497:            console.error(error);
/root/ccf/frontend/src/app/plataforma/admin/settings/system/page.tsx:526:            console.error(error);
/root/ccf/frontend/src/app/plataforma/admin/settings/system/page.tsx:550:            console.error(error);
/root/ccf/frontend/src/app/plataforma/admin/settings/system/page.tsx:572:            console.error(error);
/root/ccf/frontend/src/app/plataforma/admin/settings/system/page.tsx:601:            console.error(error);
/root/ccf/frontend/src/app/plataforma/admin/settings/system/page.tsx:626:            console.error(error);
/root/ccf/frontend/src/app/plataforma/admin/settings/system/page.tsx:651:            console.error(error);
/root/ccf/frontend/src/app/plataforma/admin/settings/system/page.tsx:681:            console.error(error);
/root/ccf/frontend/src/app/plataforma/admin/settings/system/page.tsx:703:            console.error(error);
/root/ccf/frontend/src/app/plataforma/admin/settings/system/page.tsx:728:            console.error(error);
/root/ccf/frontend/src/app/plataforma/admin/settings/system/page.tsx:747:            console.error(error);
/root/ccf/frontend/src/app/plataforma/admin/settings/system/page.tsx:766:            console.error(error);
/root/ccf/frontend/src/app/plataforma/admin/settings/system/page.tsx:790:            console.error(error);
/root/ccf/frontend/src/app/plataforma/admin/settings/system/page.tsx:808:            console.error(error);
/root/ccf/frontend/src/app/plataforma/admin/dashboard/page.tsx:84:        } catch (e) { console.error(e); }
/root/ccf/frontend/src/app/plataforma/admin/reports/page.tsx:127:                console.error('BI Analytics fetch failed', e);
/root/ccf/frontend/src/app/plataforma/admin/audit/page.tsx:39:            console.error(error);
/root/ccf/frontend/src/app/plataforma/admin/comments/page.tsx:54:            console.error(err);
/root/ccf/frontend/src/app/plataforma/admin/intelligence/page.tsx:105:            console.error(err);
/root/ccf/frontend/src/app/plataforma/admin/intelligence/page.tsx:154:            console.error(err);
/root/ccf/frontend/src/app/plataforma/admin/intelligence/page.tsx:175:            console.error(err);
/root/ccf/frontend/src/app/plataforma/admin/intelligence/page.tsx:201:            console.error(err);
/root/ccf/frontend/src/app/plataforma/admin/finance/page.tsx:74:        } catch (e: unknown) { if (e instanceof DOMException && e.name === 'AbortError') return; console.error(e); addToast('Error al cargar datos financieros', 'error'); }
/root/ccf/frontend/src/app/plataforma/admin/finance/treasury/page.tsx:62:                console.error(err);
/root/ccf/frontend/src/app/plataforma/admin/content/list/page.tsx:69:            console.error(err);
/root/ccf/frontend/src/app/plataforma/admin/actas/page.tsx:59:                console.error(error);
/root/ccf/frontend/src/app/plataforma/admin/access/page.tsx:199:        console.error(err);
/root/ccf/frontend/src/app/plataforma/admin/mission-impact/page.tsx:65:                console.error(err);
/root/ccf/frontend/src/app/plataforma/admin/analytics/candidates/page.tsx:70:            console.error(err);
/root/ccf/frontend/src/app/plataforma/admin/analytics/web-vitals/page.tsx:43:        console.error("web vitals fetch failed", error);
/root/ccf/frontend/src/app/plataforma/admin/spiritual-life/milestones/page.tsx:69:            console.error(err);
/root/ccf/frontend/src/app/plataforma/admin/maintenance/page.tsx:55:            console.error(err);
/root/ccf/frontend/src/app/plataforma/admin/talents/page.tsx:34:                .catch((err) => { if (err?.name !== 'AbortError') console.error(err); })
/root/ccf/frontend/src/app/plataforma/crm/settings/page.tsx:57:            console.error("Error fetching settings", err);
/root/ccf/frontend/src/app/plataforma/crm/settings/page.tsx:71:            console.error('Error fetching consolidation positions', err);
/root/ccf/frontend/src/app/plataforma/crm/settings/templates/page.tsx:45:      console.error(err);
/root/ccf/frontend/src/app/plataforma/crm/settings/templates/page.tsx:90:      console.error(err);
/root/ccf/frontend/src/app/plataforma/crm/my-card/page.tsx:38:            console.error(err);
/root/ccf/frontend/src/app/plataforma/crm/pipeline/page.tsx:130:                console.error(message);
/root/ccf/frontend/src/app/plataforma/crm/resources/builder/EmailBuilderPage.tsx:53:            console.error(parseErr);
/root/ccf/frontend/src/app/plataforma/crm/resources/builder/EmailBuilderPage.tsx:61:        console.error(err);
/root/ccf/frontend/src/app/plataforma/crm/resources/page.tsx:1103:            console.error(extractErrorMessage(err, 'No se pudo cargar el banco de recursos'));
/root/ccf/frontend/src/app/plataforma/academy/analitica/page.tsx:58:          console.error(error);
/root/ccf/frontend/src/app/plataforma/academy/analitica/page.tsx:93:      console.error(error);
/root/ccf/frontend/src/app/plataforma/academy/analitica/page.tsx:112:      console.error(error);
/root/ccf/frontend/src/app/plataforma/academy/admin/page.tsx:99:      console.error(err);
/root/ccf/frontend/src/app/plataforma/academy/profile/page.tsx:56:                console.error(err);
/root/ccf/frontend/src/app/plataforma/academy/course/[id]/page.tsx:89:            console.error(err);
/root/ccf/frontend/src/app/plataforma/academy/course/[id]/page.tsx:109:            console.error(err);
/root/ccf/frontend/src/app/plataforma/academy/course/[id]/page.tsx:129:            console.error(err);
/root/ccf/frontend/src/app/plataforma/projects/projectsData.ts:13:        console.error('[ProjectsPage] Failed to load projects', error);
/root/ccf/frontend/src/app/plataforma/projects/layout.tsx:17:            console.error('[ProjectsLayout] Failed to load projects for sidebar', error);
/root/ccf/frontend/src/app/plataforma/facturacion/page.tsx:91:    }).catch(e => { if (e.name !== 'AbortError') { console.error(e); toast.error('Error al cargar datos'); } })
/root/ccf/frontend/src/app/plataforma/facturacion/page.tsx:116:    } catch (e) { console.error(e); toast.error("Error al crear factura"); }
/root/ccf/frontend/src/app/plataforma/facturacion/page.tsx:129:    } catch (e) { console.error(e); toast.error("Error al registrar pago"); }
/root/ccf/frontend/src/app/plataforma/facturacion/page.tsx:139:      console.error(err);
/root/ccf/frontend/src/app/plataforma/facturacion/page.tsx:157:    } catch (e) { console.error(e); toast.error("Error al cargar datos"); }
/root/ccf/frontend/src/app/plataforma/firma/page.tsx:78:    } catch (e) { console.error(e); }
/root/ccf/frontend/src/app/plataforma/firma/page.tsx:101:    } catch (e) { console.error(e); toast.error("Error al crear solicitud de firma"); }
/root/ccf/frontend/src/app/plataforma/firma/page.tsx:110:    } catch (e) { console.error(e); toast.error("Error al enviar solicitud"); }
/root/ccf/frontend/src/app/plataforma/firma/page.tsx:121:    } catch (e) { console.error(e); toast.error("Error al firmar documento"); }
/root/ccf/frontend/src/app/plataforma/contabilidad/page.tsx:106:    }).catch(console.error).finally(() => setLoading(false));
/root/ccf/frontend/src/app/plataforma/documentos/page.tsx:76:    } catch (e) { console.error(e); }
/root/ccf/frontend/src/app/plataforma/documentos/page.tsx:100:    } catch (e) { console.error(e); toast.error("Error al crear documento"); }
/root/ccf/frontend/src/app/plataforma/documentos/page.tsx:111:    } catch (e) { console.error(e); toast.error("Error al crear etiqueta"); }
/root/ccf/frontend/src/app/plataforma/documentos/page.tsx:120:    } catch (e) { console.error(e); toast.error("Error al eliminar documento"); }
/root/ccf/frontend/src/app/login/page.tsx:88:            console.error('[LOGIN ERROR]', err);
/root/ccf/frontend/src/app/(public)/cursos/page.tsx:483:        console.error("Error fetching courses:", err);
/root/ccf/frontend/src/app/(public)/eventos/page.tsx:68:        console.error("Error fetching public upcoming events:", err);

### 1.6 DialogContent (modales centrados)
