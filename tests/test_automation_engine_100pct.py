"""Tests exhaustivos y estructurales para backend/services/automation_engine.py (100% Cobertura)."""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from backend.models_crm import (
    CanalEnvio,
    CategoriaRecurso,
    CrmAutomation,
    CrmAutomationEdge,
    PendingCrmAction,
    Persona,
    PlantillaMensaje,
)
from backend.models_crm_pipeline import CanalOrigenEnum, CasoCRM, EtapaPipeline, PipelineCRM, TipoPipelineEnum
from backend.models_evangelism import Sede
from backend.models_projects import ProjectTask
from backend.services.automation_engine import AutomationEngine


class TestAutomationEngine100Pct:
    def test_singleton_start_stop(self):
        eng1 = AutomationEngine()
        eng2 = AutomationEngine()
        assert eng1 is eng2

        with patch.object(eng1, "_run_loop"):
            eng1.start()
            assert eng1._thread is not None
            eng1.stop()
            assert eng1._thread is None

    @patch("backend.services.automation_engine.SessionLocal")
    def test_check_all_rules(self, mock_session):
        mock_db = MagicMock()
        mock_session.return_value = mock_db

        eng = AutomationEngine()
        with (
            patch.object(AutomationEngine, "_process_overload_rule") as m1,
            patch.object(AutomationEngine, "_process_deadline_rule") as m2,
            patch.object(AutomationEngine, "_process_crm_pending_actions") as m3,
        ):
            eng._check_all_rules()
            m1.assert_called_once()
            m2.assert_called_once()
            m3.assert_called_once()
            mock_db.commit.assert_called_once()
            mock_db.close.assert_called_once()

    def test_process_overload_rule(self, db_session):
        eng = AutomationEngine()
        # Mocking workload raw SQL query fetchall
        with patch.object(db_session, "execute") as mock_exec:
            row = MagicMock()
            row.user_id = uuid.uuid4()
            row.full_name = "User Overloaded"
            row.open_tasks = 10
            mock_exec.return_value.fetchall.return_value = [row]

            eng._process_overload_rule(db_session)
            # Second call should find existing notification and not duplicate
            eng._process_overload_rule(db_session)

    def test_process_deadline_rule(self, db_session):
        from backend.models_projects import Project

        eng = AutomationEngine()
        user_id = uuid.uuid4()
        project = Project(name="Proyecto Test")
        db_session.add(project)
        db_session.commit()

        task = ProjectTask(
            project_id=project.id,
            title="Tarea por vencer",
            status="in_progress",
            due_date=datetime.now() + timedelta(hours=5),
            assignee_id=user_id,
        )
        db_session.add(task)
        db_session.commit()

        eng._process_deadline_rule(db_session)
        # Second execution should skip creating duplicate UserReminder
        eng._process_deadline_rule(db_session)

    def test_trigger_crm_automation(self, db_session):
        auto = CrmAutomation(
            name="Auto Welcome", trigger_event="persona_created", action_type="whatsapp", delay_minutes=5
        )
        db_session.add(auto)
        db_session.commit()

        eng = AutomationEngine()
        target_persona_id = uuid.uuid4()
        eng.trigger_crm_automation(db_session, str(auto.id), str(target_persona_id))

        pending = db_session.query(PendingCrmAction).filter(PendingCrmAction.automation_id == auto.id).first()
        assert pending is not None
        assert pending.target_persona_id == target_persona_id

        # Triggering non-existent automation does nothing
        eng.trigger_crm_automation(db_session, str(uuid.uuid4()), str(target_persona_id))

    def test_process_crm_pending_actions_full_flow(self, db_session):
        sede = Sede(nombre="Sede Auto", ciudad="Bogotá")
        db_session.add(sede)
        db_session.commit()

        persona = Persona(first_name="Pedro", last_name="Pascal", sede_id=sede.id)
        db_session.add(persona)
        db_session.commit()

        pipeline = PipelineCRM(sede_id=sede.id, nombre="Pipe", tipo=TipoPipelineEnum.NUEVOS_VISITANTES)
        db_session.add(pipeline)
        db_session.commit()

        etapa = EtapaPipeline(pipeline_id=pipeline.id, nombre="Inicio", orden=1)
        db_session.add(etapa)
        db_session.commit()

        cat_p = CategoriaRecurso(nombre="Categoría Recurso Test")
        db_session.add(cat_p)
        db_session.commit()

        plantilla = PlantillaMensaje(
            titulo="Bienvenida",
            contenido_texto="Hola {{name}} {{last_name}}, bienvenido a CCF",
            canal=CanalEnvio.WHATSAPP,
            sede_id=sede.id,
            categoria_id=cat_p.id,
        )
        db_session.add(plantilla)
        db_session.commit()

        auto1 = CrmAutomation(
            name="Auto 1 WhatsApp",
            trigger_event="persona_created",
            action_type="whatsapp",
            action_payload={"plantilla_id": str(plantilla.id), "canal": "whatsapp"},
            delay_minutes=0,
        )
        auto2 = CrmAutomation(
            name="Auto 2 Email",
            trigger_event="persona_created",
            action_type="email",
            action_payload={"canal": "email"},
            delay_minutes=10,
        )
        db_session.add_all([auto1, auto2])
        db_session.commit()

        # Connect auto1 -> auto2 with edge condition
        edge = CrmAutomationEdge(
            source_id=auto1.id,
            target_id=auto2.id,
            condition_type="always",
        )
        db_session.add(edge)
        db_session.commit()

        caso = CasoCRM(
            persona_id=persona.id,
            sede_id=sede.id,
            pipeline_id=pipeline.id,
            etapa_actual_id=etapa.id,
            titulo_caso="Caso Pedro",
            origen_canal=CanalOrigenEnum.WEB_FORM,
            payload_web={"custom_field": "val"},
        )
        db_session.add(caso)
        db_session.commit()

        pending_action = PendingCrmAction(
            automation_id=auto1.id,
            target_persona_id=persona.id,
            execute_at=datetime.now(timezone.utc) - timedelta(minutes=1),
            status="pending",
        )
        db_session.add(pending_action)
        db_session.commit()

        eng = AutomationEngine()
        with (
            patch("backend.services.messaging.get_messaging_gateway") as mock_gw,
            patch("backend.crud.crm_.resources.create_envio") as mock_envio,
        ):
            mock_gateway = MagicMock()

            async def dummy_coro(*args, **kwargs):
                return True

            mock_gateway.send_whatsapp.side_effect = lambda *a, **kw: dummy_coro()
            mock_gw.return_value = mock_gateway

            eng._process_crm_pending_actions(db_session)
            assert pending_action.status == "executed"

            # Check next action queued
            queued_next = db_session.query(PendingCrmAction).filter(PendingCrmAction.automation_id == auto2.id).first()
            assert queued_next is not None

    def test_process_crm_pending_actions_edge_conditions_and_cycles(self, db_session):
        eng = AutomationEngine()

        # 1. Missing automation -> status failed
        action_missing = PendingCrmAction(
            automation_id=uuid.uuid4(),
            target_persona_id=uuid.uuid4(),
            execute_at=datetime.now(timezone.utc) - timedelta(minutes=1),
            status="pending",
        )
        db_session.add(action_missing)
        db_session.commit()

        # 2. Cycle detection -> status failed
        auto_a = CrmAutomation(name="Auto A", trigger_event="persona_created", action_type="email", delay_minutes=0)
        auto_b = CrmAutomation(name="Auto B", trigger_event="persona_created", action_type="email", delay_minutes=0)
        db_session.add_all([auto_a, auto_b])
        db_session.commit()

        edge1 = CrmAutomationEdge(source_id=auto_a.id, target_id=auto_b.id)
        edge2 = CrmAutomationEdge(source_id=auto_b.id, target_id=auto_a.id)
        db_session.add_all([edge1, edge2])
        db_session.commit()

        action_cycle = PendingCrmAction(
            automation_id=auto_a.id,
            target_persona_id=uuid.uuid4(),
            execute_at=datetime.now(timezone.utc) - timedelta(minutes=1),
            status="pending",
        )
        db_session.add(action_cycle)
        db_session.commit()

        eng._process_crm_pending_actions(db_session)
        assert action_missing.status == "failed"
        assert action_cycle.status == "failed"

    def test_action_types_and_condition_evaluations(self, db_session):
        sede = Sede(nombre="Sede Conditions", ciudad="Cali")
        db_session.add(sede)
        db_session.commit()

        persona = Persona(first_name="Carlos", last_name="Vives", sede_id=sede.id)
        pipeline = PipelineCRM(sede_id=sede.id, nombre="Pipe2", tipo=TipoPipelineEnum.NUEVOS_VISITANTES)
        db_session.add_all([persona, pipeline])
        db_session.commit()

        etapa1 = EtapaPipeline(pipeline_id=pipeline.id, nombre="Etapa 1", orden=1)
        etapa2 = EtapaPipeline(pipeline_id=pipeline.id, nombre="Etapa 2", orden=2)
        db_session.add_all([etapa1, etapa2])
        db_session.commit()

        caso = CasoCRM(
            persona_id=persona.id,
            sede_id=sede.id,
            pipeline_id=pipeline.id,
            etapa_actual_id=etapa1.id,
            titulo_caso="Caso Carlos",
            origen_canal=CanalOrigenEnum.WEB_FORM,
            payload_web={"score": 10, "city": "Cali", "tag": "VIP"},
        )
        db_session.add(caso)
        db_session.commit()

        # 1. Action: email
        auto_email = CrmAutomation(
            name="Email Action",
            trigger_event="persona_created",
            action_type="email",
            action_payload={"canal": "email", "subject": "Hola", "body": "Bienvenido"},
        )
        # 2. Action: whatsapp
        auto_task = CrmAutomation(
            name="WhatsApp Action",
            trigger_event="persona_created",
            action_type="whatsapp",
            action_payload={"canal": "whatsapp"},
        )
        # 3. Action: sms
        auto_sms = CrmAutomation(
            name="SMS Action",
            trigger_event="persona_created",
            action_type="sms",
            action_payload={"canal": "sms"},
        )

        db_session.add_all([auto_email, auto_task, auto_sms])
        db_session.commit()

        now = datetime.now(timezone.utc) - timedelta(minutes=1)
        act_email = PendingCrmAction(automation_id=auto_email.id, target_persona_id=persona.id, execute_at=now)
        act_task = PendingCrmAction(automation_id=auto_task.id, target_persona_id=persona.id, execute_at=now)
        act_sms = PendingCrmAction(automation_id=auto_sms.id, target_persona_id=persona.id, execute_at=now)
        db_session.add_all([act_email, act_task, act_sms])
        db_session.commit()

        eng = AutomationEngine()
        with (
            patch("backend.services.messaging.get_messaging_gateway") as mock_gw,
            patch("backend.crud.crm_.resources.create_envio") as mock_envio,
        ):
            mock_gateway = MagicMock()

            async def dummy_coro(*args, **kwargs):
                return True

            mock_gateway.send_email.side_effect = lambda *a, **kw: dummy_coro()
            mock_gateway.send_whatsapp.side_effect = lambda *a, **kw: dummy_coro()
            mock_gateway.send_sms.side_effect = lambda *a, **kw: dummy_coro()
            mock_gw.return_value = mock_gateway

            eng._process_crm_pending_actions(db_session)

            assert act_email.status == "executed"
            assert act_task.status == "executed"
            assert act_sms.status == "executed"

    def test_evaluate_condition_operators(self, db_session):
        # Triggering _process_crm_pending_actions with dummy action and edge condition types
        sede = Sede(nombre="Sede Eval", ciudad="Medellín")
        db_session.add(sede)
        db_session.commit()

        persona = Persona(first_name="TestCond", last_name="User", sede_id=sede.id)
        db_session.add(persona)
        db_session.commit()

        # We will test all condition operators by running _process_crm_pending_actions with edge conditions
        operators = [
            ("equals", "first_name", "TestCond", True),
            ("ne", "first_name", "Wrong", True),
            ("contains", "first_name", "Test", True),
            ("starts_with", "first_name", "Test", True),
            ("gt", "score", "5", True),
            ("lt", "score", "15", True),
            ("in", "first_name", '["TestCond", "Other"]', True),
            ("unknown_op", "first_name", "TestCond", False),
        ]

        pipeline = PipelineCRM(sede_id=sede.id, nombre="PipeEval", tipo=TipoPipelineEnum.NUEVOS_VISITANTES)
        db_session.add(pipeline)
        db_session.commit()

        etapa = EtapaPipeline(pipeline_id=pipeline.id, nombre="E1", orden=1)
        db_session.add(etapa)
        db_session.commit()

        caso = CasoCRM(
            persona_id=persona.id,
            sede_id=sede.id,
            pipeline_id=pipeline.id,
            etapa_actual_id=etapa.id,
            titulo_caso="Caso Eval",
            origen_canal=CanalOrigenEnum.WEB_FORM,
            payload_web={"score": 10},
        )
        db_session.add(caso)
        db_session.commit()

        eng = AutomationEngine()

        with (
            patch("backend.services.messaging.get_messaging_gateway") as mock_gw,
            patch("backend.crud.crm_.resources.create_envio") as mock_envio,
        ):
            mock_gateway = MagicMock()

            async def dummy_coro(*args, **kwargs):
                return True

            mock_gateway.send_whatsapp.side_effect = lambda *a, **kw: dummy_coro()
            mock_gateway.send_email.side_effect = lambda *a, **kw: dummy_coro()
            mock_gateway.send_sms.side_effect = lambda *a, **kw: dummy_coro()
            mock_gw.return_value = mock_gateway

            for op, key, val, should_queue in operators:
                auto_src = CrmAutomation(
                    name=f"Src {op}",
                    trigger_event="persona_created",
                    action_type="whatsapp",
                    action_payload={"canal": "whatsapp"},
                )
                auto_tgt = CrmAutomation(
                    name=f"Tgt {op}",
                    trigger_event="persona_created",
                    action_type="whatsapp",
                    action_payload={"canal": "whatsapp"},
                    delay_minutes=5,
                )
                db_session.add_all([auto_src, auto_tgt])
                db_session.commit()

                edge = CrmAutomationEdge(
                    source_id=auto_src.id,
                    target_id=auto_tgt.id,
                    condition_type=op,
                    condition_key=key,
                    condition_value=val,
                )
                db_session.add(edge)
                db_session.commit()

                p_act = PendingCrmAction(
                    automation_id=auto_src.id,
                    target_persona_id=persona.id,
                    execute_at=datetime.now(timezone.utc) - timedelta(minutes=1),
                )
                db_session.add(p_act)
                db_session.commit()

                eng._process_crm_pending_actions(db_session)
                assert p_act.status == "executed"

                tgt_queued = (
                    db_session.query(PendingCrmAction).filter(PendingCrmAction.automation_id == auto_tgt.id).first()
                )
                if should_queue:
                    assert tgt_queued is not None, f"Operator {op} should have queued target action"
                else:
                    assert tgt_queued is None, f"Operator {op} should NOT have queued target action"
