# Handoff Report: Milestone 2: AI Copilot for Counseling Explorer

## 1. Observation

### Backend Routing and Scope Checks
- The counseling ticket endpoints are defined in `backend/api/crm/pastoral.py` (specifically lines 924–960 for detailed get route, 1120–1250 for CRUD list, post, and patch).
- Sede/Tenant scope checking is enforced using the helper function `_get_scoped_counseling_ticket(db: Session, user: models.User, ticket_id)` defined in `backend/api/crm/_shared.py` (lines 109–127). This helper handles the mapping from counseling tickets to the associated persona's sede:
  ```python
  user_sede = get_user_sede_id(db, user.id)
  query = db.query(models.CounselingTicket).filter(
      models.CounselingTicket.id == ticket_uuid,
      models.CounselingTicket.deleted_at.is_(None),
  )
  if user_sede:
      query = query.join(
          models.Persona, models.CounselingTicket.persona_id == models.Persona.id
      ).filter(models.Persona.sede_id == user_sede)
  ticket = query.first()
  ```

### Relevant Models & Context Sources
- `CounselingTicket` (defined in `backend/models_crm.py` at line 164) contains columns `id`, `persona_id`, `pastor_id`, `subject`, `notes`, `status`, `priority_level`, `sentiment_score`, `sentiment_label`, `created_at`, `deleted_at`.
- `CommunicationLog` (defined in `backend/models_crm.py` at line 625) stores logs of outgoing/incoming communications. It maps to `Persona` via `persona_id`, containing `channel`, `content`, `outcome`, `created_at`.
- `get_persona_timeline(db: Session, persona_id: str)` is defined in `backend/crud/crm_/timeline.py` (lines 10–93) and aggregates timeline events such as enrollments, ministerial assignments, prior counseling sessions, and communication logs.

### OpenAI Integration
- In `backend/agents/orchestrator.py` (lines 19–23, 44–58), the OpenAI client is dynamically imported and initialized:
  ```python
  try:
      from openai import OpenAI
  except ImportError:
      OpenAI = None
  ...
  key = api_key or os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
  self.client = OpenAI(base_url=base_url, api_key=key)
  ```
- Environment variables are defined in `.env` and handled by the centralized `Settings` class in `backend/core/config.py`, which is loaded using `get_settings()` (though `openai_api_key` is not explicitly declared as a setting attribute and is retrieved directly from environment variables).

### Frontend Routing and Components
- The counseling ticket detail page is located at `frontend/src/app/plataforma/crm/counseling/[id]/page.tsx`.
- Currently, the page displays details of a ticket, loading them from the `/crm/counseling/{id}` backend route.
- The notes are displayed as static text inside a `DSCard` (lines 107–112):
  ```tsx
  <DSCard>
      <h3 className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))] mb-3">Notas confidenciales</h3>
      <p className="text-sm text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] leading-relaxed font-medium">
          {session.confidential_notes || "Sin notas confidenciales registradas."}
      </p>
  </DSCard>
  ```
  There is currently no edit state, text editor, or form input for notes.

---

## 2. Logic Chain

- **Scope Check**: Since `_get_scoped_counseling_ticket` already handles multi-tenant boundary checks (returning 404 for cross-sede access), incorporating it at the beginning of the new AI endpoint prevents unauthorized access to counseling data.
- **Context Generation**: Building the prompt requires drawing on historical information. Combining the current ticket subject/notes with `models.CommunicationLog` (full content) and `get_persona_timeline` (history) provides a rich context that allows the LLM to draft a helpful, coherent, and contextualized progress summary.
- **Error Handling / Fallback**: Network failures or missing API keys shouldn't crash the server. If `OPENAI_API_KEY` is not present, or if any OpenAI API call fails, the endpoint should return a pre-formatted placeholder/default draft text that the user can still use and edit.
- **Notes Editor**: Since the detail page currently lacks editing features, we need to introduce a toggled editing state. When active, it replaces the read-only view with a `<textarea>` control and provides a toolbar containing an "AI Copilot" button, a "Guardar" (Save) button, and a "Cancelar" (Cancel) button.

---

## 3. Caveats

- **API Key Preference**: The system uses `OPENAI_API_KEY` (or `OPENROUTER_API_KEY`). We assume standard environment configuration. If OpenRouter is chosen, the endpoint can optionally configure a base URL, similar to `AgentOrchestrator`.
- **Notes Fields**: The model contains both `summary` and `notes`. The detail page uses `notes` for rendering. The plan assumes updating the main `notes` column via `PATCH /crm/counseling/{id}` with `{ "notes": ... }`.

---

## 4. Conclusion

We propose the following detailed plan for Milestone 2:

### Step 1: Define Backend API Endpoint
Create a new route in `/root/ccf/backend/api/crm/pastoral.py` under the path `/counseling/{ticket_id}/copilot-draft`:
```python
@router.get("/counseling/{ticket_id}/copilot-draft", response_model=dict)
def get_counseling_copilot_draft(
    ticket_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(require_module_access("crm", "read")),
):
    # 1. Tenant/Sede Scope Validation
    ticket = _get_scoped_counseling_ticket(db, current_user, ticket_id)
    persona = ticket.persona
    
    # 2. Extract context data
    persona_name = _persona_full_name(persona) if persona else "Miembro"
    church_role = persona.church_role if persona else "Miembro"
    spiritual_status = persona.spiritual_status if persona else "Nuevo"
    pastoral_notes = persona.pastoral_notes if persona else ""
    
    # Historical counseling tickets (exclude current)
    past_tickets = (
        db.query(models.CounselingTicket)
        .filter(
            models.CounselingTicket.persona_id == ticket.persona_id,
            models.CounselingTicket.id != ticket.id,
            models.CounselingTicket.deleted_at.is_(None)
        )
        .order_by(models.CounselingTicket.created_at.desc())
        .limit(3)
        .all()
    )
    
    # Communication logs
    comm_logs = (
        db.query(models.CommunicationLog)
        .filter(models.CommunicationLog.persona_id == ticket.persona_id)
        .order_by(models.CommunicationLog.created_at.desc())
        .limit(5)
        .all()
    )
    
    # Format context for prompt
    past_tickets_str = "\n".join([
        f"- {t.created_at.strftime('%Y-%m-%d') if t.created_at else 'N/A'}: [Tema: {t.subject}] Notas: {t.notes or 'Sin notas'}"
        for t in past_tickets
    ])
    
    comm_logs_str = "\n".join([
        f"- {c.created_at.strftime('%Y-%m-%d') if c.created_at else 'N/A'} [{c.channel}]: {c.content}"
        for c in comm_logs
    ])
    
    # 3. Default fallback draft template (used if API key is missing or API errors out)
    default_draft = (
        f"Borrador Sugerido para Consejería de {persona_name}:\n\n"
        f"Tema: {ticket.subject}\n"
        f"Notas previas del ticket: {ticket.notes or 'Ninguna'}\n\n"
        f"Puntos clave sugeridos:\n"
        f"- Revisión del estado espiritual actual ({spiritual_status}).\n"
        f"- Seguimiento de la última sesión / comunicaciones.\n"
        f"- Acciones pastorales inmediatas y oración por necesidades específicas.\n\n"
        f"(Nota: OpenAI API Key no está configurada o falló. Este es un borrador estructurado por defecto)."
    )
    
    # 4. Check OpenAI API key
    import os
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return {"draft": default_draft, "suggestion": default_draft}
        
    # 5. Initialize client and make OpenAI API call
    try:
        from openai import OpenAI
    except ImportError:
        logger.error("openai module is not installed")
        return {"draft": default_draft, "suggestion": default_draft}
        
    try:
        client = OpenAI(api_key=api_key)
        
        system_prompt = (
            "Eres un asistente de IA para Consejería Pastoral de la iglesia CCF.\n"
            "Tu tarea es generar un borrador estructurado de notas de consejería para el ticket actual.\n"
            "Usa el contexto provisto (datos de la persona, histórico de consejería y bitácoras de comunicación) "
            "para producir un texto empático, estructurado (en español) y útil para el consejero.\n"
            "El borrador debe incluir:\n"
            "1. Resumen de la situación / situación actual.\n"
            "2. Puntos clave a tratar o tratados.\n"
            "3. Plan de acción / próximos pasos sugeridos."
        )
        
        user_content = (
            f"Información de la Persona:\n"
            f"- Nombre: {persona_name}\n"
            f"- Rol: {church_role}\n"
            f"- Estado Espiritual: {spiritual_status}\n"
            f"- Notas Pastorales Generales: {pastoral_notes}\n\n"
            f"Ticket Actual:\n"
            f"- Asunto: {ticket.subject}\n"
            f"- Notas del Ticket: {ticket.notes or 'Sin notas previas'}\n\n"
            f"Historial de Consejería Reciente:\n{past_tickets_str or 'Sin sesiones previas'}\n\n"
            f"Comunicaciones Recientes:\n{comm_logs_str or 'Sin comunicaciones registradas'}\n"
        )
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            temperature=0.7,
            max_tokens=600,
        )
        
        generated_draft = response.choices[0].message.content
        return {"draft": generated_draft, "suggestion": generated_draft}
        
    except Exception as e:
        logger.error(f"OpenAI completion error: {e}", exc_info=True)
        error_draft = (
            f"{default_draft}\n\n"
            f"[Error de conexión con IA: {str(e)}]"
        )
        return {"draft": error_draft, "suggestion": error_draft}
```

### Step 2: Integrate Notes Editor and AI Copilot in Frontend
Edit `frontend/src/app/plataforma/crm/counseling/[id]/page.tsx` to handle note modification and AI suggestions:

1. **State Hooks:**
   ```tsx
   const [isEditing, setIsEditing] = useState(false);
   const [notes, setNotes] = useState("");
   const [isGenerating, setIsGenerating] = useState(false);
   ```
2. **Handlers:**
   ```tsx
   const handleGenerateCopilotDraft = async () => {
       try {
           setIsGenerating(true);
           const data = await apiFetch<{ draft: string }>(`/crm/counseling/${id}/copilot-draft`, { token });
           setNotes((prev) => (prev ? prev + "\n\n" + data.draft : data.draft));
           toast.success("Borrador de copilot IA cargado");
       } catch (err) {
           console.error(err);
           toast.error("Error al generar borrador con copilot IA");
       } finally {
           setIsGenerating(false);
       }
   };

   const handleSaveNotes = async () => {
       try {
           await apiFetch(`/crm/counseling/${id}`, {
               method: "PATCH",
               token,
               body: JSON.stringify({ notes }),
           });
           setSession((prev) => (prev ? { ...prev, notes } : null));
           setIsEditing(false);
           toast.success("Notas guardadas correctamente");
       } catch (err) {
           console.error(err);
           toast.error("Error al guardar las notas");
       }
   };
   ```
3. **Template Update inside `DSCard`:**
   ```tsx
   <DSCard>
       <div className="flex justify-between items-center mb-3">
           <h3 className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--text-secondary))]">Resumen de la Sesion</h3>
           <div className="flex gap-2">
               {!isEditing ? (
                   <button 
                       onClick={() => { setIsEditing(true); setNotes(session.notes || ""); }} 
                       className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--primary))] hover:underline"
                   >
                       Editar
                   </button>
               ) : (
                   <>
                       <button 
                           onClick={handleGenerateCopilotDraft} 
                           disabled={isGenerating}
                           className="text-[10px] font-bold uppercase tracking-wide text-[hsl(var(--secondary))] hover:underline flex items-center gap-1 disabled:opacity-50"
                       >
                           {isGenerating ? "Generando..." : "AI Copilot"}
                       </button>
                       <button 
                           onClick={handleSaveNotes} 
                           className="text-[10px] font-bold uppercase tracking-wide text-emerald-600 hover:underline"
                       >
                           Guardar
                       </button>
                       <button 
                           onClick={() => setIsEditing(false)} 
                           className="text-[10px] font-bold uppercase tracking-wide text-rose-600 hover:underline"
                       >
                           Cancelar
                       </button>
                   </>
               )}
           </div>
       </div>
       
       {!isEditing ? (
           <p className="text-sm text-[hsl(var(--text-secondary))] dark:text-[hsl(var(--text-secondary))] leading-relaxed font-medium">
               {session.notes || "Sin resumen registrado."}
           </p>
       ) : (
           <textarea
               value={notes}
               onChange={(e) => setNotes(e.target.value)}
               className="w-full h-40 p-2 text-sm border rounded-md dark:bg-white/5 border-[hsl(var(--border))] dark:border-white/10 text-[hsl(var(--text-primary))] focus:outline-none focus:ring-1 focus:ring-[hsl(var(--primary))]"
               placeholder="Escriba las notas o use el AI Copilot..."
           />
       )}
   </DSCard>
   ```

---

## 5. Verification Method

### Backend Endpoint Verification
Add a pytest verification test to `tests/test_flow_tests.py`:
```python
def test_counseling_copilot_draft(self, full):
    c, h, personas = full["c"], full["h"], full["personas"]
    resp_create = c.post("/api/crm/counseling", json={
        "persona_id": str(personas[0].id), "subject": "AI Session Test"
    }, headers=h)
    assert resp_create.status_code == 201
    tid = resp_create.json().get("id")
    
    # Test getting AI copilot draft (key might be missing, testing fallback)
    resp_draft = c.get(f"/api/crm/counseling/{tid}/copilot-draft", headers=h)
    assert resp_draft.status_code == 200
    assert "draft" in resp_draft.json()
    assert "suggestion" in resp_draft.json()
```
Run the test command to verify backend:
```bash
pytest tests/test_flow_tests.py -k test_counseling
```

### Frontend Verification
1. Access the piattaforma CRM counseling detail page: `/plataforma/crm/counseling/[id]`.
2. Click the **Editar** button inside the "Resumen de la Sesion" card.
3. Observe that the notes display changes into a textarea.
4. Click the **AI Copilot** button.
5. Verify that the textarea is populated with the suggestion (whether generated by OpenAI or the default fallback template) and that a toast notification is displayed.
6. Edit the text if desired, then click **Guardar**.
7. Confirm that the patch command successfully saves the note and returns the card to a read-only state with the updated notes.
