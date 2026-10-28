"""Conservative query-local scope proofs for explicitly migrated audit domains.

Only WHERE predicates on queried/joined models, verified FK joins and genuine
ID projections carry scope. Unknown ORM methods fail closed. This is a bounded
source audit, not a replacement for behavioral multi-tenant regression tests.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from functools import lru_cache

IDENTITY_COLUMNS = {
    "persona_id",
    "author_persona_id",
    "student_id",
    "docente_persona_id",
    "mentor_persona_id",
    "mentee_persona_id",
}
PARENT_HELPERS = {
    "_get_scoped_academy_offering": "AcademyPeriodOffering",
    "_get_scoped_academy_plan": "AcademyStudyPlan",
    "_get_scoped_academy_subject": "AcademyStudyPlanSubject",
    "_get_scoped_academy_student": "Persona",
}
# These are actual model FK contracts, not endpoint/file exemptions.
FOREIGN_KEYS = {
    ("Certificate", "enrollment_id"): "Enrollment",
    ("AssignmentSubmission", "enrollment_id"): "Enrollment",
    ("AcademyStudentEnrollment", "offering_id"): "AcademyPeriodOffering",
    ("AcademyStudentEnrollment", "persona_id"): "Persona",
    ("AcademyStudyPlanSubject", "study_plan_id"): "AcademyStudyPlan",
    ("AcademyKnowledgeNode", "offering_id"): "AcademyPeriodOffering",
    ("AcademyKnowledgeEdge", "source_node_id"): "AcademyKnowledgeNode",
    ("AcademyKnowledgeEdge", "target_node_id"): "AcademyKnowledgeNode",
    ("AcademyStudentNodeProgress", "node_id"): "AcademyKnowledgeNode",
    ("AcademyStudentPeriodGrade", "offering_id"): "AcademyPeriodOffering",
    ("AcademyWellnessSignal", "offering_id"): "AcademyPeriodOffering",
    ("AcademyStudyGroup", "offering_id"): "AcademyPeriodOffering",
    ("EncuestaRespuestaDetalle", "pregunta_id"): "EncuestaPregunta",
    ("EncuestaRespuestaEnvio", "formulario_id"): "EncuestaFormulario",
}
# In this domain AST is authoritative and MUST run before line-word heuristics.
PROVENANCE_FUNCTIONS = {
    "get_my_recommendations",
    "get_my_mentorship_requests",
    "get_student_knowledge_progress",
    "get_survey_responses_table",
    "get_offering_grades_docente",
    "get_calendar_events",
    "get_offering_wellness_signals",
    "get_student_portfolio",
    "get_my_mentees",
    "export_my_academy_data",
    "add_subject_to_study_plan_admin",
    "get_my_study_groups",
    "get_survey_analytics",
    "update_subject_admin",
    "get_knowledge_graph",
    "get_cohort_health",
    "get_offering_students_admin",
    "delete_subject_admin",
    "get_my_offerings_docente",
    "get_calendar_workload_prediction",
    "get_my_portfolio",
    "get_available_mentors",
    "list_study_groups_by_offering",
}


def text(node: ast.AST) -> str:
    return ast.unparse(node)


def column(node: ast.AST) -> tuple[str, str] | None:
    if isinstance(node, ast.Attribute) and isinstance(node.value, (ast.Name, ast.Attribute)):
        return text(node.value), node.attr
    return None


def model_name(name: str) -> str:
    return name.rsplit(".", 1)[-1]


@dataclass
class Query:
    projected: set[str]
    models: set[str]
    projections: list[ast.AST]
    predicates: list[ast.AST] = field(default_factory=list)
    joins: list[ast.AST] = field(default_factory=list)


@lru_cache(maxsize=8)
def source_context(source: str):
    tree = ast.parse(source)
    parents = {child: node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}
    return tree, parents


class ScopeProof:
    def __init__(self, source: str, line: int):
        self.tree, self.parents = source_context(source)
        self.function = next(
            (
                n
                for n in ast.walk(self.tree)
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.lineno <= line <= n.end_lineno
            ),
            None,
        )
        self.line = line
        self.assignments = (
            []
            if self.function is None
            else [n for n in ast.walk(self.function) if isinstance(n, (ast.Assign, ast.AnnAssign, ast.AugAssign))]
        )
        self.guards: list[tuple[str, str, int, bool]] = []
        if self.function:
            self.collect_guards()

    def modified(self, name: str, after: int, before: int) -> bool:
        for node in self.assignments:
            if not after < node.lineno < before:
                continue
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                while isinstance(target, (ast.Attribute, ast.Subscript)):
                    target = target.value
                if isinstance(target, ast.Name) and target.id == name:
                    return True
        return False

    def collect_guards(self):
        for node in self.function.body:
            value = node.value if isinstance(node, (ast.Expr, ast.Assign, ast.AnnAssign)) else None
            if isinstance(value, ast.Call) and isinstance(value.func, ast.Name) and value.func.id in PARENT_HELPERS:
                if len(value.args) == 3 and text(value.args[1]) == "current_user":
                    parent_type = PARENT_HELPERS[value.func.id]
                    if isinstance(value.args[2], ast.Name):
                        self.guards.append((value.args[2].id, parent_type, node.lineno, False))
                    if isinstance(node, ast.Assign):
                        for target in node.targets:
                            if isinstance(target, ast.Name):
                                self.guards.append((target.id, parent_type, node.lineno, True))
            # Exact inline Survey guard: authenticated actor sede + parent ID +
            # rejecting cross-sede branch. It is not inferred from nearby words.
            if (
                not isinstance(node, ast.If)
                or not isinstance(node.test, ast.BoolOp)
                or not isinstance(node.test.op, ast.And)
            ):
                continue
            if {text(v) for v in node.test.values} != {
                "user_sede_id is not None",
                "survey.sede_id is not None",
                "survey.sede_id != user_sede_id",
            }:
                continue
            if (
                len(node.body) != 1
                or not isinstance(node.body[0], ast.Raise)
                or not isinstance(node.body[0].exc, ast.Call)
            ):
                continue
            call = node.body[0].exc
            if text(call.func) != "HTTPException" or not any(
                k.arg == "status_code" and text(k.value) == "status.HTTP_403_FORBIDDEN" for k in call.keywords
            ):
                continue
            actor = self.binding("user_sede_id", node.lineno)
            parent = self.binding("survey", node.lineno)
            if actor is None or text(actor.value) != "get_user_sede_id(db, current_user.id)" or parent is None:
                continue
            if not any(
                isinstance(p, ast.Compare) and text(p) == "models_surveys.EncuestaFormulario.id == survey_id"
                for p in ast.walk(parent.value)
            ):
                continue
            self.guards.extend(
                [
                    ("survey", "EncuestaFormulario", node.lineno, True),
                    ("survey_id", "EncuestaFormulario", node.lineno, False),
                ]
            )

    def binding(self, name: str, before: int):
        candidates = []
        for node in self.assignments:
            if node.lineno >= before:
                continue
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if any(isinstance(t, ast.Name) and t.id == name for t in targets):
                candidates.append(node)
        return max(candidates, key=lambda n: n.lineno) if candidates else None

    def value_types(self, node: ast.AST, before: int, seen=frozenset()) -> set[str]:
        for name, parent_type, guarded_at, is_object in self.guards:
            if guarded_at < before and not self.modified(name, guarded_at, before):
                if not is_object and isinstance(node, ast.Name) and node.id == name:
                    return {parent_type}
                if is_object and isinstance(node, ast.Attribute) and text(node) == name + ".id":
                    return {parent_type}
        if isinstance(node, ast.Attribute) and node.attr == "id":
            for loop in ast.walk(self.function):
                if (
                    isinstance(loop, ast.For)
                    and loop.lineno <= before <= loop.end_lineno
                    and text(loop.target) == text(node.value)
                    and text(loop.iter) == "survey.preguntas"
                ):
                    if any(g[0] == "survey" and not self.modified("survey", g[2], before) for g in self.guards):
                        return {"EncuestaPregunta"}
        if isinstance(node, ast.Name):
            key = node.id, before
            if key in seen:
                return set()
            bound = self.binding(node.id, before)
            return (
                self.value_types(bound.value, bound.lineno, seen | {key})
                if bound is not None and bound.value is not None
                else set()
            )
        if isinstance(node, ast.ListComp):
            for generator in node.generators:
                query = self.query(generator.iter, before, seen)
                if query is None or not self.scoped(query, before) or len(query.projected) != 1:
                    continue
                root = next(iter(query.projected))
                if isinstance(node.elt, ast.Attribute) and text(node.elt.value) == text(generator.target):
                    if node.elt.attr == "id":
                        return {model_name(root)}
                    parent = FOREIGN_KEYS.get((model_name(root), node.elt.attr))
                    if parent:
                        return {parent}
                if (
                    isinstance(node.elt, ast.Subscript)
                    and text(node.elt.value) == text(generator.target)
                    and text(node.elt.slice) == "0"
                    and query.projections
                ):
                    projected = column(query.projections[0])
                    if projected and projected[1] == "id":
                        return {model_name(projected[0])}
            return set()
        return set()

    def projection_models(self, value: ast.AST) -> set[str]:
        if isinstance(value, ast.Name):
            return {value.id}
        if isinstance(value, ast.Attribute):
            if isinstance(value.value, ast.Name) and value.value.id in {"models", "models_surveys"}:
                return {text(value)}
            col = column(value)
            return {col[0]} if col else set()
        if isinstance(value, ast.Call):
            return set().union(*(self.projection_models(arg) for arg in value.args))
        return set()

    def query(self, node: ast.AST, before: int, seen=frozenset()) -> Query | None:
        if isinstance(node, ast.Name):
            key = node.id, before
            if key in seen:
                return None
            bound = self.binding(node.id, before)
            if bound is None or bound.value is None:
                return None
            if self.parents.get(bound) is not self.function:
                # A conditional narrowing filter cannot widen an already scoped
                # receiver. Any conditional replacement/unknown transform fails.
                value = bound.value
                if (
                    not isinstance(value, ast.Call)
                    or not isinstance(value.func, ast.Attribute)
                    or value.func.attr not in {"filter", "where"}
                    or text(value.func.value) != node.id
                ):
                    return None
                return self.query(value.func.value, bound.lineno, seen | {key})
            return self.query(bound.value, bound.lineno, seen | {key})
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            return None
        method = node.func.attr
        if method == "query" and text(node.func.value) == "db":
            models = set().union(*(self.projection_models(arg) for arg in node.args))
            return Query(set(models), set(models), list(node.args)) if models else None
        receiver = self.query(node.func.value, before, seen)
        if receiver is None:
            return None
        if method in {"all", "order_by", "options", "limit", "offset", "group_by", "distinct"}:
            return receiver
        if method in {"filter", "where"}:
            receiver.predicates.extend(node.args)
            return receiver
        if method == "join" and node.args:
            receiver.models.update(self.projection_models(node.args[0]))
            receiver.joins.extend(node.args[1:])
            return receiver
        # UNION/from_statement/unknown methods may add rows: never inherit proof.
        return None

    def predicate(self, node: ast.AST, query: Query, before: int) -> set[str]:
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id == "or_":
                branches = [self.predicate(arg, query, before) for arg in node.args]
                return set.intersection(*branches) if branches else set()
            if node.func.id == "and_":
                return set().union(*(self.predicate(arg, query, before) for arg in node.args))
            if node.func.id == "_academy_sede_filter" and len(node.args) == 3 and text(node.args[1]) == "current_user":
                col = column(node.args[2])
                return {col[0]} if col and col[1] == "sede_id" and col[0] in query.models else set()
        if isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], ast.Eq):
            pairs = [(node.left, node.comparators[0]), (node.comparators[0], node.left)]
            for lhs, rhs in pairs:
                col = column(lhs)
                if not col or col[0] not in query.models:
                    continue
                if (
                    col[1] in IDENTITY_COLUMNS
                    and text(rhs) == "current_user.id"
                    and not self.modified("current_user", self.function.lineno, before)
                ):
                    return {col[0]}
                expected = model_name(col[0]) if col[1] == "id" else FOREIGN_KEYS.get((model_name(col[0]), col[1]))
                if expected in self.value_types(rhs, before):
                    return {col[0]}
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "in_"
            and len(node.args) == 1
        ):
            col = column(node.func.value)
            if col and col[0] in query.models:
                expected = model_name(col[0]) if col[1] == "id" else FOREIGN_KEYS.get((model_name(col[0]), col[1]))
                if expected in self.value_types(node.args[0], before):
                    return {col[0]}
        return set()

    def scoped(self, query: Query, before: int) -> bool:
        scoped = set().union(*(self.predicate(p, query, before) for p in query.predicates))
        changed = True
        while changed:
            changed = False
            for join in query.joins:
                if not isinstance(join, ast.Compare) or len(join.ops) != 1 or not isinstance(join.ops[0], ast.Eq):
                    continue
                left, right = column(join.left), column(join.comparators[0])
                for child, parent in [(left, right), (right, left)]:
                    if (
                        child
                        and parent
                        and child[0] in query.models
                        and parent[0] in scoped
                        and parent[1] == "id"
                        and FOREIGN_KEYS.get((model_name(child[0]), child[1])) == model_name(parent[0])
                        and child[0] not in scoped
                    ):
                        scoped.add(child[0])
                        changed = True
        return bool(query.projected) and query.projected <= scoped


def query_has_tenant_provenance(source: str, line: int) -> bool:
    proof = ScopeProof(source, line)
    if proof.function is None:
        return False
    terminal = next(
        (
            node
            for node in ast.walk(proof.function)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "all"
            and node.end_lineno == line
        ),
        None,
    )
    if terminal is None:
        return False
    query = proof.query(terminal, terminal.lineno)
    return query is not None and proof.scoped(query, terminal.lineno)


def in_provenance_domain(source: str, line: int) -> bool:
    return any(
        isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
        and n.name in PROVENANCE_FUNCTIONS
        and n.lineno <= line <= n.end_lineno
        for n in ast.walk(source_context(source)[0])
    )
