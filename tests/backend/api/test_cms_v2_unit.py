import uuid
from backend.api import cms_v2
from backend import schemas, models

# Minimal dummy DB to satisfy CRUD operations used in tests
class DummyQuery:
    def __init__(self, model=None):
        self.model = model
        self._data = []
        self._filters = []
        self._order = None
        self._skip = 0
        self._limit = None

    def filter(self, *args, **kwargs):
        self._filters.append((args, kwargs))
        return self

    def order_by(self, *args, **kwargs):
        self._order = (args, kwargs)
        return self

    def offset(self, n):
        self._skip = n
        return self

    def limit(self, n):
        self._limit = n
        return self

    def all(self):
        return []

    def first(self):
        return None

    def count(self):
        return 0

    def scalar(self):
        return None

class DummyDB:
    def __init__(self):
        self.added = []
        self.committed = False
        self.refreshed = []

    def query(self, model):
        return DummyQuery(model)

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        self.committed = True

    def refresh(self, obj):
        self.refreshed.append(obj)
        return obj

    def flush(self):
        pass

# Tests for internal helper _slugify
def test_slugify_basic():
    assert cms_v2._slugify('Hello World') == 'hello-world'
    assert cms_v2._slugify('  Foo_Bar  ') == 'foo_bar'
    assert cms_v2._slugify('Café!') == 'caf'

# Test list_sites returns empty list with dummy DB
def test_list_sites_empty():
    db = DummyDB()
    result = cms_v2.list_sites(db=db, only_active=False)
    assert result == []

# Test create_site uses payload correctly and interacts with DB
def test_create_site_interaction():
    db = DummyDB()
    payload = schemas.CmsSiteCreate(site_key='test', name='Test Site', base_path='/test')
    dummy_user = type('U', (), {'id': uuid.uuid4(), 'role': 'admin'})()
    site = cms_v2.create_site(payload, db=db, current_user=dummy_user)
    assert isinstance(site, models.CmsSite)
    assert site.site_key == 'test'
    assert site.name == 'Test Site'
    assert site.base_path == '/test'
    assert db.added[0] is site
    assert db.committed
