"""The AST fallback must prove the queried data's provenance, not nearby text."""

from scripts.query_tenant_provenance import query_has_tenant_provenance


def proves(body):
    source = "def endpoint(db, current_user, arbitrary_id):\n" + "\n".join("    " + line for line in body.splitlines())
    line = next(i for i, value in reversed(list(enumerate(source.splitlines(), 1))) if ".all()" in value)
    return query_has_tenant_provenance(source, line)


def test_own_identity_and_derived_ids_propagate_to_the_child_query():
    assert proves(
        "rows = db.query(Enrollment).filter(Enrollment.persona_id == current_user.id).all()\nids = [row.id for row in rows]\nreturn db.query(AssignmentSubmission).filter(AssignmentSubmission.enrollment_id.in_(ids)).all()"
    )


def test_unrelated_scope_and_comments_do_not_authorize_an_unbounded_query():
    assert not proves(
        "# sede_id current_user.id _scope_ comments prove nothing\nowned = db.query(Row).filter(Row.persona_id == current_user.id).all()\nreturn db.query(Secret).all()"
    )
    assert not proves("return db.query(Secret).filter(Secret.persona_id == arbitrary_id).all()")


def test_parent_guard_must_validate_the_same_input_before_the_query():
    assert proves(
        "_get_scoped_academy_offering(db, current_user, arbitrary_id)\nreturn db.query(models.AcademyKnowledgeNode).filter(models.AcademyKnowledgeNode.offering_id == arbitrary_id).all()"
    )
    assert not proves(
        "_get_scoped_academy_offering(db, current_user, other_id)\nreturn db.query(models.AcademyKnowledgeNode).filter(models.AcademyKnowledgeNode.offering_id == arbitrary_id).all()"
    )


def test_overwriting_a_scoped_query_does_not_authorize_its_replacement():
    assert not proves(
        "query = db.query(Row).filter(Row.student_id == current_user.id)\nquery = db.query(Secret)\nreturn query.all()"
    )


def test_or_and_negation_must_not_turn_an_owner_predicate_into_authorization():
    assert not proves("return db.query(Row).filter(or_(Row.student_id == current_user.id, Row.enabled == True)).all()")
    assert not proves("return db.query(Row).filter(not_(Row.student_id == current_user.id)).all()")
    assert not proves("return db.query(Row).filter(~(Row.student_id == current_user.id)).all()")


def test_parent_input_cannot_be_reassigned_after_its_guard():
    assert not proves(
        "_get_scoped_academy_offering(db, current_user, arbitrary_id)\narbitrary_id = foreign_id\nreturn db.query(models.AcademyKnowledgeNode).filter(models.AcademyKnowledgeNode.offering_id == arbitrary_id).all()"
    )


def test_ordering_and_projection_are_not_scope_predicates():
    assert not proves("return db.query(Row).order_by(Row.student_id == current_user.id).all()")
    assert not proves("return db.query(Row.student_id == current_user.id).all()")
    assert not proves("return db.query(Row).order_by(_academy_sede_filter(db, current_user, Row.sede_id)).all()")


def test_independent_review_false_green_cases_are_rejected():
    statements = [
        "_get_scoped_academy_offering(db, current_user, arbitrary_id)\nif supplied:\n    arbitrary_id = foreign_id\nreturn db.query(Node).filter(Node.offering_id == arbitrary_id).all()",
        "parent = _get_scoped_academy_offering(db, current_user, arbitrary_id)\nparent.id = foreign_id\nreturn db.query(Node).filter(Node.offering_id == parent.id).all()",
        "return db.query(Row).filter((Row.student_id == current_user.id).is_(False)).all()",
        "return db.query(Row).filter(Row.student_id == current_user.id).union(db.query(Row)).all()",
        "_get_scoped_academy_offering(db, current_user, arbitrary_id)\nreturn db.query(Secret).filter(Offering.id == arbitrary_id).all()",
        "return db.query(Secret).filter(Persona.student_id == current_user.id).all()",
        "rows = db.query(Row).filter(Row.student_id == current_user.id).all()\nids = [foreign_id for row in rows]\nreturn db.query(Secret).filter(Secret.id.in_(ids)).all()",
    ]
    for statement in statements:
        assert not proves(statement), statement


def test_certificate_scope_requires_the_actual_enrollment_join():
    assert proves(
        "return db.query(Certificate).join(Enrollment, Certificate.enrollment_id == Enrollment.id).filter(Enrollment.persona_id == current_user.id).all()"
    )
    assert not proves("return db.query(Certificate).filter(Enrollment.persona_id == current_user.id).all()")


def test_legacy_scope_words_cannot_bypass_an_ast_domain(tmp_path, monkeypatch):
    import pytest

    from tests import test_reglas_plataforma as audit

    (tmp_path / "academy.py").write_text(
        "def get_my_portfolio(db, current_user):\n    # sede_id _scope_ markers are not proof\n    return db.query(Secret).all()\n"
    )
    monkeypatch.setattr(audit, "API_DIR", tmp_path)
    with pytest.raises(AssertionError):
        audit.test_sede_id_in_all_queries()
