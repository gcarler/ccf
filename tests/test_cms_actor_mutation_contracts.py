"""CMS mutation contracts must reject unauthenticated actors before touching data."""

import inspect
import uuid
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from backend.crud.cms import forms, newsletters, popups

MUTATIONS = [
    forms.create_cms_form, forms.update_cms_form, forms.delete_cms_form,
    popups.create_cms_popup, popups.update_cms_popup, popups.delete_cms_popup,
    newsletters.create_cms_newsletter, newsletters.update_cms_newsletter,
    newsletters.delete_cms_newsletter, newsletters.send_cms_newsletter,
    newsletters.create_cms_subscriber, newsletters.import_cms_subscribers,
    newsletters.update_cms_subscriber, newsletters.delete_cms_subscriber,
]


@pytest.mark.parametrize("mutate", MUTATIONS, ids=lambda function: function.__name__)
@pytest.mark.parametrize("actor", [None, "malformed-uuid"])
def test_cms_mutations_require_canonical_actor(mutate, actor):
    db = MagicMock()
    row = MagicMock(site_id=uuid.uuid4())
    values = {"db": db, "site_id": row.site_id, "row": row, "payload": MagicMock()}
    arguments = {
        name: values[name]
        for name in inspect.signature(mutate).parameters
        if name != "actor_user_id"
    }
    with pytest.raises(HTTPException) as caught:
        mutate(**arguments, actor_user_id=actor)
    assert caught.value.status_code == 401
    db.query.assert_not_called()
    db.add.assert_not_called()
    db.commit.assert_not_called()
