# Inventario OpenAPI — Projects

> Generado desde `backend.app:app.openapi()` por `scripts/audit_projects_api_contracts.py`.
> El guard declarado se extrae de la dependencia `current_user` del router; esto no prueba
> el resultado por rol ni sustituye la matriz RBAC y sus tests.
> los contratos de negocio en `PROJECTS_API_CONTRACTS.md`.

Operaciones únicas actuales: **121** bajo `/api/projects`.

| Método | Ruta | Operation ID | Guard declarado | Entrada | Respuestas OpenAPI |
|---|---|---|---|---|---|
| `GET` | `/api/projects` | `list_projects_api_projects_get` | `projects:read` | — | `200` `Project`<br>`422` — |
| `POST` | `/api/projects` | `create_project_api_projects_post` | `projects:edit` | `ProjectCreate` | `201` `Project`<br>`422` — |
| `GET` | `/api/projects/activities` | `list_activities_api_projects_activities_get` | `projects:read` | — | `200` `ProjectActivityItem`<br>`422` — |
| `GET` | `/api/projects/assignee-candidates` | `list_project_assignee_candidates_api_projects_assignee_candidates_get` | `projects:read` | — | `200` `ProjectAssigneeCandidate`<br>`422` — |
| `GET` | `/api/projects/assignee-candidates/{persona_id}` | `get_project_assignee_candidate_api_projects_assignee_candidates__persona_id__get` | `projects:read` | — | `200` `ProjectAssigneeCandidate`<br>`422` — |
| `GET` | `/api/projects/comments` | `list_all_comments_api_projects_comments_get` | `projects:read` | — | `200` `ProjectCommentItem`<br>`422` — |
| `POST` | `/api/projects/comments` | `create_comment_api_projects_comments_post` | `projects:edit` | `ProjectCommentCreateWithProject` | `200` `ProjectCommentItem`<br>`422` — |
| `DELETE` | `/api/projects/comments/{comment_id}` | `delete_project_comment_api_projects_comments__comment_id__delete` | `projects:edit` | — | `200` —<br>`422` — |
| `PATCH` | `/api/projects/comments/{comment_id}` | `update_project_comment_api_projects_comments__comment_id__patch` | `projects:edit` | `ProjectCommentUpdate` | `200` `ProjectCommentItem`<br>`422` — |
| `POST` | `/api/projects/from-template/{template_id}` | `instantiate_project_from_template_endpoint_api_projects_from_template__template_id__post` | `projects:edit` | `InstantiateProjectFromTemplate` | `201` `Project`<br>`422` — |
| `GET` | `/api/projects/inbox` | `list_inbox_api_projects_inbox_get` | `projects:read` | — | `200` `ProjectInboxItem`<br>`422` — |
| `POST` | `/api/projects/inbox/{item_id}/read` | `mark_inbox_read_api_projects_inbox__item_id__read_post` | `projects:edit` | — | `200` —<br>`422` — |
| `GET` | `/api/projects/page` | `list_projects_page_api_projects_page_get` | `projects:read` | — | `200` `PaginatedResponse_Project_`<br>`422` — |
| `GET` | `/api/projects/summary` | `portfolio_summary_api_projects_summary_get` | `projects:read` | — | `200` `ProjectPortfolioSummaryRow` |
| `GET` | `/api/projects/summary-page` | `list_project_summaries_page_api_projects_summary_page_get` | `projects:read` | — | `200` `PaginatedResponse_ProjectSummary_`<br>`422` — |
| `GET` | `/api/projects/tasks` | `list_all_my_tasks_api_projects_tasks_get` | `projects:read` | — | `200` `ProjectTask` |
| `GET` | `/api/projects/tasks/page` | `list_my_tasks_page_api_projects_tasks_page_get` | `projects:read` | — | `200` `PaginatedResponse_ProjectTaskPageItem_`<br>`422` — |
| `GET` | `/api/projects/tasks/{task_id}` | `get_task_api_projects_tasks__task_id__get` | `project access: read` | — | `200` `ProjectTask`<br>`422` — |
| `PATCH` | `/api/projects/tasks/{task_id}` | `update_task_api_projects_tasks__task_id__patch` | `project access: edit` | `ProjectTaskUpdate` | `200` `ProjectTask`<br>`422` — |
| `GET` | `/api/projects/templates` | `list_project_templates_api_projects_templates_get` | `projects:read` | — | `200` `ProjectTemplate`<br>`422` — |
| `POST` | `/api/projects/templates` | `create_project_template_endpoint_api_projects_templates_post` | `projects:edit` | `ProjectTemplateCreate` | `201` `ProjectTemplate`<br>`422` — |
| `DELETE` | `/api/projects/templates/{template_id}` | `delete_project_template_endpoint_api_projects_templates__template_id__delete` | `projects:edit` | — | `200` —<br>`422` — |
| `GET` | `/api/projects/templates/{template_id}` | `get_project_template_endpoint_api_projects_templates__template_id__get` | `projects:read` | — | `200` `ProjectTemplate`<br>`422` — |
| `PATCH` | `/api/projects/templates/{template_id}` | `update_project_template_endpoint_api_projects_templates__template_id__patch` | `projects:edit` | `ProjectTemplateUpdate` | `200` `ProjectTemplate`<br>`422` — |
| `POST` | `/api/projects/templates/{template_id}/instantiate` | `instantiate_project_from_template_endpoint_api_projects_templates__template_id__instantiate_post` | `projects:edit` | `InstantiateProjectFromTemplate` | `201` `Project`<br>`422` — |
| `GET` | `/api/projects/whiteboards` | `list_whiteboards_api_projects_whiteboards_get` | `projects:read` | — | `200` `ProjectWhiteboard`<br>`422` — |
| `GET` | `/api/projects/workload` | `workload_summary_api_projects_workload_get` | `projects:read` | — | `200` `ProjectWorkloadSummaryRow` |
| `DELETE` | `/api/projects/{project_id}` | `delete_project_api_projects__project_id__delete` | `academy:manage` | — | `200` —<br>`422` — |
| `GET` | `/api/projects/{project_id}` | `get_project_api_projects__project_id__get` | `project access: read` | — | `200` `Project`<br>`422` — |
| `PATCH` | `/api/projects/{project_id}` | `update_project_api_projects__project_id__patch` | `projects:edit` | `ProjectUpdate` | `200` `Project`<br>`422` — |
| `GET` | `/api/projects/{project_id}/advanced-indicators` | `list_project_indicators_endpoint_api_projects__project_id__advanced_indicators_get` | `projects:read` | — | `200` `ProjectIndicator`<br>`422` — |
| `POST` | `/api/projects/{project_id}/advanced-indicators` | `create_project_indicator_endpoint_api_projects__project_id__advanced_indicators_post` | `projects:edit` | `ProjectIndicatorCreate` | `201` `ProjectIndicator`<br>`422` — |
| `DELETE` | `/api/projects/{project_id}/advanced-indicators/{indicator_id}` | `delete_project_indicator_endpoint_api_projects__project_id__advanced_indicators__indicator_id__delete` | `projects:edit` | — | `200` —<br>`422` — |
| `GET` | `/api/projects/{project_id}/advanced-indicators/{indicator_id}` | `get_project_indicator_endpoint_api_projects__project_id__advanced_indicators__indicator_id__get` | `projects:read` | — | `200` `ProjectIndicator`<br>`422` — |
| `PATCH` | `/api/projects/{project_id}/advanced-indicators/{indicator_id}` | `update_project_indicator_endpoint_api_projects__project_id__advanced_indicators__indicator_id__patch` | `projects:edit` | `ProjectIndicatorUpdate` | `200` `ProjectIndicator`<br>`422` — |
| `GET` | `/api/projects/{project_id}/analytics` | `get_project_analytics_api_projects__project_id__analytics_get` | `project access: read` | — | `200` `ProjectAnalytics`<br>`422` — |
| `GET` | `/api/projects/{project_id}/automations` | `list_project_automations_api_projects__project_id__automations_get` | `projects:read` | — | `200` `ProjectAutomationRule`<br>`422` — |
| `POST` | `/api/projects/{project_id}/automations` | `create_project_automation_api_projects__project_id__automations_post` | `projects:edit` | `ProjectAutomationRuleCreate` | `201` `ProjectAutomationRule`<br>`422` — |
| `POST` | `/api/projects/{project_id}/automations/evaluate` | `evaluate_project_automations_endpoint_api_projects__project_id__automations_evaluate_post` | `projects:edit` | `EvaluateAutomationPayload` | `200` `AutomationExecutionResult`<br>`422` — |
| `DELETE` | `/api/projects/{project_id}/automations/{rule_id}` | `delete_project_automation_api_projects__project_id__automations__rule_id__delete` | `projects:edit` | — | `200` —<br>`422` — |
| `GET` | `/api/projects/{project_id}/automations/{rule_id}` | `get_project_automation_api_projects__project_id__automations__rule_id__get` | `projects:read` | — | `200` `ProjectAutomationRule`<br>`422` — |
| `PATCH` | `/api/projects/{project_id}/automations/{rule_id}` | `update_project_automation_api_projects__project_id__automations__rule_id__patch` | `projects:edit` | `ProjectAutomationRuleUpdate` | `200` `ProjectAutomationRule`<br>`422` — |
| `GET` | `/api/projects/{project_id}/baseline` | `get_project_latest_baseline_endpoint_api_projects__project_id__baseline_get` | `projects:read` | — | `200` `ProjectBaseline`<br>`422` — |
| `POST` | `/api/projects/{project_id}/baseline` | `create_project_baseline_endpoint_api_projects__project_id__baseline_post` | `project access: edit` | `ProjectBaselineCreate` | `200` `ProjectBaseline`<br>`422` — |
| `GET` | `/api/projects/{project_id}/baselines` | `list_project_baselines_endpoint_api_projects__project_id__baselines_get` | `projects:read` | — | `200` `ProjectBaseline`<br>`422` — |
| `GET` | `/api/projects/{project_id}/budget-summary` | `get_project_budget_summary_api_projects__project_id__budget_summary_get` | `projects:read` | — | `200` `ProjectBudgetSummary`<br>`422` — |
| `POST` | `/api/projects/{project_id}/comments` | `create_project_comment_api_projects__project_id__comments_post` | `project access: edit` | `ProjectCommentCreate` | `200` `ProjectCommentItem`<br>`422` — |
| `GET` | `/api/projects/{project_id}/critical-path` | `get_project_critical_path_api_projects__project_id__critical_path_get` | `projects:read` | — | `200` `ProjectCriticalPathSummary`<br>`422` — |
| `GET` | `/api/projects/{project_id}/dependencies` | `list_task_dependencies_api_projects__project_id__dependencies_get` | `projects:read` | — | `200` `ProjectTaskDependency`<br>`422` — |
| `POST` | `/api/projects/{project_id}/dependencies` | `create_task_dependency_api_projects__project_id__dependencies_post` | `projects:edit` | `ProjectTaskDependencyCreate` | `201` `ProjectTaskDependency`<br>`422` — |
| `DELETE` | `/api/projects/{project_id}/dependencies/{dependency_id}` | `delete_task_dependency_api_projects__project_id__dependencies__dependency_id__delete` | `projects:edit` | — | `200` —<br>`422` — |
| `GET` | `/api/projects/{project_id}/expenses` | `list_project_expenses_api_projects__project_id__expenses_get` | `projects:read` | — | `200` `ProjectExpense`<br>`422` — |
| `POST` | `/api/projects/{project_id}/expenses` | `create_project_expense_api_projects__project_id__expenses_post` | `projects:edit` | `ProjectExpenseCreate` | `201` `ProjectExpense`<br>`422` — |
| `DELETE` | `/api/projects/{project_id}/expenses/{expense_id}` | `delete_project_expense_api_projects__project_id__expenses__expense_id__delete` | `projects:edit` | — | `200` —<br>`422` — |
| `GET` | `/api/projects/{project_id}/expenses/{expense_id}` | `get_project_expense_api_projects__project_id__expenses__expense_id__get` | `projects:read` | — | `200` `ProjectExpense`<br>`422` — |
| `PATCH` | `/api/projects/{project_id}/expenses/{expense_id}` | `update_project_expense_api_projects__project_id__expenses__expense_id__patch` | `projects:edit` | `ProjectExpenseUpdate` | `200` `ProjectExpense`<br>`422` — |
| `GET` | `/api/projects/{project_id}/export/executive-data` | `get_project_executive_data_endpoint_api_projects__project_id__export_executive_data_get` | `projects:read` | — | `200` `ProjectExecutiveReportData`<br>`422` — |
| `GET` | `/api/projects/{project_id}/export/expenses-csv` | `export_project_expenses_csv_endpoint_api_projects__project_id__export_expenses_csv_get` | `projects:read` | — | `200` —<br>`422` — |
| `GET` | `/api/projects/{project_id}/export/summary-pdf` | `export_project_summary_pdf_endpoint_api_projects__project_id__export_summary_pdf_get` | `projects:read` | — | `200` —<br>`422` — |
| `GET` | `/api/projects/{project_id}/export/tasks-csv` | `export_project_tasks_csv_endpoint_api_projects__project_id__export_tasks_csv_get` | `projects:read` | — | `200` —<br>`422` — |
| `GET` | `/api/projects/{project_id}/favorites` | `get_project_favorites_endpoint_api_projects__project_id__favorites_get` | `projects:read` | — | `200` —<br>`422` — |
| `GET` | `/api/projects/{project_id}/files` | `list_project_files_endpoint_api_projects__project_id__files_get` | `projects:read` | — | `200` `ProjectFile`<br>`422` — |
| `POST` | `/api/projects/{project_id}/files/link-drive` | `link_project_drive_file_endpoint_api_projects__project_id__files_link_drive_post` | `projects:edit` | `ProjectFileLinkDrivePayload` | `200` `ProjectFile`<br>`422` — |
| `GET` | `/api/projects/{project_id}/files/summary` | `get_project_files_summary_endpoint_api_projects__project_id__files_summary_get` | `projects:read` | — | `200` `ProjectFilesSummary`<br>`422` — |
| `POST` | `/api/projects/{project_id}/files/upload` | `upload_project_file_endpoint_api_projects__project_id__files_upload_post` | `projects:edit` | `Body_upload_project_file_endpoint_api_projects__project_id__files_upload_post` | `200` `ProjectFile`<br>`422` — |
| `DELETE` | `/api/projects/{project_id}/files/{file_id}` | `delete_project_file_endpoint_api_projects__project_id__files__file_id__delete` | `projects:edit` | — | `200` —<br>`422` — |
| `POST` | `/api/projects/{project_id}/indicators/validate-crema` | `validate_crema_indicator_endpoint_api_projects__project_id__indicators_validate_crema_post` | `projects:read` | `ValidateCremaPayload` | `200` `CremaValidationResult`<br>`422` — |
| `GET` | `/api/projects/{project_id}/indicators/{indicator_id}/records` | `list_project_indicator_records_endpoint_api_projects__project_id__indicators__indicator_id__records_get` | `projects:read` | — | `200` `ProjectIndicatorRecord`<br>`422` — |
| `POST` | `/api/projects/{project_id}/indicators/{indicator_id}/records` | `create_project_indicator_record_endpoint_api_projects__project_id__indicators__indicator_id__records_post` | `projects:edit` | `ProjectIndicatorRecordCreate` | `201` `ProjectIndicatorRecord`<br>`422` — |
| `GET` | `/api/projects/{project_id}/kpis` | `list_project_kpis_api_projects__project_id__kpis_get` | `projects:read` | — | `200` `ProjectKPI`<br>`422` — |
| `POST` | `/api/projects/{project_id}/kpis` | `create_project_kpi_api_projects__project_id__kpis_post` | `projects:edit` | `ProjectKPICreate` | `201` `ProjectKPI`<br>`422` — |
| `DELETE` | `/api/projects/{project_id}/kpis/{kpi_id}` | `delete_project_kpi_api_projects__project_id__kpis__kpi_id__delete` | `projects:edit` | — | `200` —<br>`422` — |
| `PATCH` | `/api/projects/{project_id}/kpis/{kpi_id}` | `update_project_kpi_api_projects__project_id__kpis__kpi_id__patch` | `projects:edit` | `ProjectKPIUpdate` | `200` `ProjectKPI`<br>`422` — |
| `GET` | `/api/projects/{project_id}/messages` | `list_project_messages_api_projects__project_id__messages_get` | `projects:read` | — | `200` `ProjectMessageItem`<br>`422` — |
| `POST` | `/api/projects/{project_id}/messages` | `send_project_message_api_projects__project_id__messages_post` | `projects:edit` | `ProjectMessageCreate` | `201` `ProjectMessageItem`<br>`422` — |
| `DELETE` | `/api/projects/{project_id}/messages/{message_id}` | `delete_project_message_api_projects__project_id__messages__message_id__delete` | `projects:edit` | — | `200` —<br>`422` — |
| `GET` | `/api/projects/{project_id}/milestones` | `list_project_milestones_api_projects__project_id__milestones_get` | `projects:read` | — | `200` `ProjectMilestone`<br>`422` — |
| `POST` | `/api/projects/{project_id}/milestones` | `create_project_milestone_api_projects__project_id__milestones_post` | `projects:edit` | `ProjectMilestoneBase` | `201` `ProjectMilestone`<br>`422` — |
| `DELETE` | `/api/projects/{project_id}/milestones/{milestone_id}` | `delete_project_milestone_api_projects__project_id__milestones__milestone_id__delete` | `projects:edit` | — | `200` —<br>`422` — |
| `PATCH` | `/api/projects/{project_id}/milestones/{milestone_id}` | `update_project_milestone_api_projects__project_id__milestones__milestone_id__patch` | `projects:edit` | `ProjectMilestoneUpdate` | `200` `ProjectMilestone`<br>`422` — |
| `GET` | `/api/projects/{project_id}/phases` | `list_project_phases_api_projects__project_id__phases_get` | `project access: read` | — | `200` `ProjectPhaseSchema`<br>`422` — |
| `PUT` | `/api/projects/{project_id}/phases` | `set_project_phases_api_projects__project_id__phases_put` | `project access: manage` | `ProjectPhaseInput` | `200` `ProjectPhaseSchema`<br>`422` — |
| `GET` | `/api/projects/{project_id}/risks` | `list_project_risks_api_projects__project_id__risks_get` | `projects:read` | — | `200` `ProjectRisk`<br>`422` — |
| `POST` | `/api/projects/{project_id}/risks` | `create_project_risk_api_projects__project_id__risks_post` | `projects:edit` | `ProjectRiskCreate` | `201` `ProjectRisk`<br>`422` — |
| `GET` | `/api/projects/{project_id}/risks-summary` | `get_project_risks_summary_api_projects__project_id__risks_summary_get` | `projects:read` | — | `200` `ProjectRiskSummary`<br>`422` — |
| `DELETE` | `/api/projects/{project_id}/risks/{risk_id}` | `delete_project_risk_api_projects__project_id__risks__risk_id__delete` | `projects:edit` | — | `200` —<br>`422` — |
| `GET` | `/api/projects/{project_id}/risks/{risk_id}` | `get_project_risk_api_projects__project_id__risks__risk_id__get` | `projects:read` | — | `200` `ProjectRisk`<br>`422` — |
| `PATCH` | `/api/projects/{project_id}/risks/{risk_id}` | `update_project_risk_api_projects__project_id__risks__risk_id__patch` | `projects:edit` | `ProjectRiskUpdate` | `200` `ProjectRisk`<br>`422` — |
| `POST` | `/api/projects/{project_id}/risks/{risk_id}/convert-to-task` | `convert_risk_to_task_api_projects__project_id__risks__risk_id__convert_to_task_post` | `projects:edit` | — | `201` `ProjectTask`<br>`422` — |
| `POST` | `/api/projects/{project_id}/save-as-template` | `save_project_as_template_endpoint_api_projects__project_id__save_as_template_post` | `projects:edit` | `SaveProjectAsTemplate` | `201` `ProjectTemplate`<br>`422` — |
| `GET` | `/api/projects/{project_id}/tasks` | `list_project_tasks_api_projects__project_id__tasks_get` | `projects:read` | — | `200` `ProjectTask`<br>`422` — |
| `POST` | `/api/projects/{project_id}/tasks` | `create_project_task_api_projects__project_id__tasks_post` | `project access: edit` | `ProjectTaskCreate` | `201` `ProjectTask`<br>`422` — |
| `DELETE` | `/api/projects/{project_id}/tasks/{task_id}` | `delete_project_task_api_projects__project_id__tasks__task_id__delete` | `projects:edit` | — | `200` —<br>`422` — |
| `PATCH` | `/api/projects/{project_id}/tasks/{task_id}` | `update_project_task_api_projects__project_id__tasks__task_id__patch` | `project access: edit` | `ProjectTaskUpdate` | `200` `ProjectTask`<br>`422` — |
| `POST` | `/api/projects/{project_id}/tasks/{task_id}/attachments` | `upload_task_attachment_api_projects__project_id__tasks__task_id__attachments_post` | `project access: edit` | `Body_upload_task_attachment_api_projects__project_id__tasks__task_id__attachments_post` | `200` `ProjectTask`<br>`422` — |
| `DELETE` | `/api/projects/{project_id}/tasks/{task_id}/attachments/{attachment_id}` | `delete_task_attachment_api_projects__project_id__tasks__task_id__attachments__attachment_id__delete` | `project access: edit` | — | `200` —<br>`422` — |
| `POST` | `/api/projects/{project_id}/tasks/{task_id}/comments/{comment_id}/pin` | `pin_task_comment_endpoint_api_projects__project_id__tasks__task_id__comments__comment_id__pin_post` | `projects:edit` | `ProjectPinCommentPayload` | `200` `ProjectCommentItem`<br>`422` — |
| `PATCH` | `/api/projects/{project_id}/tasks/{task_id}/reassign` | `reassign_project_task_api_projects__project_id__tasks__task_id__reassign_patch` | `project access: edit` | `TaskReassignPayload` | `200` `ProjectTask`<br>`422` — |
| `POST` | `/api/projects/{project_id}/tasks/{task_id}/subtasks` | `create_subtask_api_projects__project_id__tasks__task_id__subtasks_post` | `project access: edit` | `ProjectTaskCreate` | `201` `ProjectTask`<br>`422` — |
| `DELETE` | `/api/projects/{project_id}/tasks/{task_id}/subtasks/{subtask_id}` | `delete_subtask_api_projects__project_id__tasks__task_id__subtasks__subtask_id__delete` | `project access: edit` | — | `200` —<br>`422` — |
| `PATCH` | `/api/projects/{project_id}/tasks/{task_id}/subtasks/{subtask_id}` | `update_subtask_api_projects__project_id__tasks__task_id__subtasks__subtask_id__patch` | `project access: edit` | `ProjectTaskUpdate` | `200` `ProjectTask`<br>`422` — |
| `GET` | `/api/projects/{project_id}/tasks/{task_id}/supplies` | `list_task_supplies_api_projects__project_id__tasks__task_id__supplies_get` | `project access: read` | — | `200` `TaskSupply`<br>`422` — |
| `POST` | `/api/projects/{project_id}/tasks/{task_id}/supplies` | `create_task_supply_api_projects__project_id__tasks__task_id__supplies_post` | `project access: edit` | `TaskSupplyCreate` | `201` `TaskSupply`<br>`422` — |
| `DELETE` | `/api/projects/{project_id}/tasks/{task_id}/supplies/{supply_id}` | `delete_task_supply_api_projects__project_id__tasks__task_id__supplies__supply_id__delete` | `project access: edit` | — | `200` —<br>`422` — |
| `PATCH` | `/api/projects/{project_id}/tasks/{task_id}/supplies/{supply_id}` | `update_task_supply_api_projects__project_id__tasks__task_id__supplies__supply_id__patch` | `project access: edit` | `TaskSupplyUpdate` | `200` `TaskSupply`<br>`422` — |
| `GET` | `/api/projects/{project_id}/tasks/{task_id}/time-logs` | `list_task_time_logs_api_projects__project_id__tasks__task_id__time_logs_get` | `projects:read` | — | `200` `ProjectTimeLog`<br>`422` — |
| `POST` | `/api/projects/{project_id}/tasks/{task_id}/toggle-favorite` | `toggle_task_favorite_endpoint_api_projects__project_id__tasks__task_id__toggle_favorite_post` | `projects:read` | — | `200` `ProjectUserFavoriteToggleResponse`<br>`422` — |
| `GET` | `/api/projects/{project_id}/team` | `list_project_team_api_projects__project_id__team_get` | `project access: read` | — | `200` `ProjectMember`<br>`422` — |
| `POST` | `/api/projects/{project_id}/team` | `invite_project_member_api_projects__project_id__team_post` | `project access: edit` | `ProjectMemberCreate` | `201` `ProjectMember`<br>`422` — |
| `DELETE` | `/api/projects/{project_id}/team/{persona_id}` | `remove_project_member_api_projects__project_id__team__persona_id__delete` | `project access: edit` | — | `200` —<br>`422` — |
| `GET` | `/api/projects/{project_id}/time-logs` | `list_project_time_logs_api_projects__project_id__time_logs_get` | `projects:read` | — | `200` `ProjectTimeLog`<br>`422` — |
| `POST` | `/api/projects/{project_id}/time-logs` | `create_project_time_log_api_projects__project_id__time_logs_post` | `projects:edit` | `ProjectTimeLogCreate` | `201` `ProjectTimeLog`<br>`422` — |
| `DELETE` | `/api/projects/{project_id}/time-logs/{log_id}` | `delete_project_time_log_api_projects__project_id__time_logs__log_id__delete` | `projects:edit` | — | `200` —<br>`422` — |
| `GET` | `/api/projects/{project_id}/time-tracking-summary` | `get_project_time_tracking_summary_api_projects__project_id__time_tracking_summary_get` | `projects:read` | — | `200` `ProjectTimeTrackingSummary`<br>`422` — |
| `DELETE` | `/api/projects/{project_id}/whiteboard` | `delete_project_whiteboard_api_projects__project_id__whiteboard_delete` | `project access: edit` | — | `204` —<br>`422` — |
| `GET` | `/api/projects/{project_id}/whiteboard` | `get_project_whiteboard_api_projects__project_id__whiteboard_get` | `project access: read` | — | `200` `ProjectWhiteboard`<br>`422` — |
| `POST` | `/api/projects/{project_id}/whiteboard` | `update_project_whiteboard_api_projects__project_id__whiteboard_post` | `project access: edit` | `ProjectWhiteboardUpdate` | `200` `ProjectWhiteboard`<br>`422` — |
| `POST` | `/api/projects/{project_id}/whiteboard/thumbnail` | `upload_project_whiteboard_thumbnail_api_projects__project_id__whiteboard_thumbnail_post` | `project access: edit` | `Body_upload_project_whiteboard_thumbnail_api_projects__project_id__whiteboard_thumbnail_post` | `200` —<br>`422` — |
| `GET` | `/api/projects/{project_id}/wiki` | `get_project_wiki_api_projects__project_id__wiki_get` | `project access: read` | — | `200` `ProjectDocument`<br>`422` — |
| `POST` | `/api/projects/{project_id}/wiki` | `update_project_wiki_api_projects__project_id__wiki_post` | `project access: edit` | `ProjectDocumentUpdate` | `200` `ProjectDocument`<br>`422` — |
| `GET` | `/api/projects/{project_id}/workload` | `get_project_workload_api_projects__project_id__workload_get` | `projects:read` | — | `200` `ProjectWorkloadSummary`<br>`422` — |
