# Deploy Rollback Checklist (CCF)

Fecha: 2026-05-05  
Estado: Vigente  
Ambito: incidentes de despliegue para backend/frontend en Kubernetes (`namespace: ccf`).

## 1. Criterios de activacion

Activar rollback si ocurre al menos una condicion:
- error 5xx sostenido despues de deploy
- `rollout` no converge en backend o frontend
- degradacion critica de login, CRM, evangelismo o academy
- incompatibilidad de migracion detectada en runtime

## 2. Preflight rapido (2-3 minutos)

1. Verificar estado actual:
   - `kubectl get pods -n ccf`
   - `kubectl get deploy -n ccf`
2. Verificar revision activa:
   - `kubectl rollout history deployment/ccf-ccf-backend -n ccf`
   - `kubectl rollout history deployment/ccf-ccf-frontend -n ccf`
3. Confirmar impacto:
   - errores en logs de app
   - alertas de disponibilidad o latencia

## 3. Rollback operativo

### Opcion A: rollback por deployment (rapida)

1. Backend:
   - `kubectl rollout undo deployment/ccf-ccf-backend -n ccf`
2. Frontend:
   - `kubectl rollout undo deployment/ccf-ccf-frontend -n ccf`
3. Verificacion:
   - `kubectl rollout status deployment/ccf-ccf-backend -n ccf --timeout=300s`
   - `kubectl rollout status deployment/ccf-ccf-frontend -n ccf --timeout=300s`

### Opcion B: rollback por Helm release (controlado)

1. Ver historial:
   - `helm history ccf -n ccf`
2. Volver a revision estable:
   - `helm rollback ccf <REVISION_ESTABLE> -n ccf --wait --timeout 10m`
3. Verificacion:
   - `kubectl get pods -n ccf`
   - `kubectl rollout status deployment/ccf-ccf-backend -n ccf --timeout=300s`
   - `kubectl rollout status deployment/ccf-ccf-frontend -n ccf --timeout=300s`

## 4. Datos y migraciones

- Si hubo migraciones incompatibles, detener nuevos writes antes de rollback.
- Si el rollback de app depende de esquema previo, evaluar rollback de DB solo con ventana controlada.
- Nunca ejecutar rollback destructivo de DB sin respaldo validado.

## 5. Cierre del incidente

1. Confirmar recuperacion funcional:
   - login
   - dashboard
   - CRM y evangelismo (eventos/asistencia)
2. Confirmar recuperacion tecnica:
   - sin `CrashLoopBackOff`
   - sin errores criticos en logs de arranque
3. Documentar postmortem minimo:
   - SHA desplegado
   - causa raiz
   - accion de rollback aplicada
   - accion preventiva para CI/CD

## 6. Prevencion obligatoria despues de rollback

- bloquear redeploy automatico del mismo SHA
- abrir fix de pipeline o app antes de reintentar despliegue
- validar en entorno previo con `CI` verde y smoke funcional
