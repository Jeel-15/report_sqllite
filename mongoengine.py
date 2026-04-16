import datetime
import json
import os
import re
import secrets
import sqlite3
from copy import deepcopy


_MODEL_REGISTRY = {}


class _MongoDict(dict):
    def to_dict(self):
        return dict(self)


class _SQLiteStore:
    def __init__(self):
        self.path = None

    def configure(self, path=None):
        if path and path.startswith("sqlite:///"):
            path = path.replace("sqlite:///", "", 1)
        if not path:
            path = os.getenv("SQLITE_PATH", "app.db")
        self.path = os.path.abspath(path)
        folder = os.path.dirname(self.path)
        if folder:
            os.makedirs(folder, exist_ok=True)
        self._ensure_schema()

    def _conn(self):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_schema(self):
        with self._conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS __documents (
                    collection TEXT NOT NULL,
                    id TEXT NOT NULL,
                    data TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (collection, id)
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_documents_collection ON __documents(collection)"
            )
            conn.commit()

    def fetch_collection(self, collection):
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT id, data FROM __documents WHERE collection = ?", (collection,)
            ).fetchall()
        result = []
        for row in rows:
            payload = json.loads(row["data"]) if row["data"] else {}
            result.append((row["id"], payload))
        return result

    def upsert(self, collection, doc_id, payload):
        now = datetime.datetime.utcnow().isoformat()
        text = json.dumps(payload, ensure_ascii=False)
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO __documents(collection, id, data, updated_at)
                VALUES(?, ?, ?, ?)
                ON CONFLICT(collection, id)
                DO UPDATE SET data=excluded.data, updated_at=excluded.updated_at
                """,
                (collection, str(doc_id), text, now),
            )
            conn.commit()

    def delete_ids(self, collection, doc_ids):
        if not doc_ids:
            return 0
        placeholders = ",".join("?" for _ in doc_ids)
        params = [collection] + [str(i) for i in doc_ids]
        with self._conn() as conn:
            cursor = conn.execute(
                f"DELETE FROM __documents WHERE collection = ? AND id IN ({placeholders})",
                params,
            )
            conn.commit()
        return cursor.rowcount


_store = _SQLiteStore()


def connect(host=None, path=None, **kwargs):
    # Keep mongoengine-style signature compatibility.
    db_path = path or host or os.getenv("SQLITE_PATH", "app.db")
    _store.configure(db_path)
    return db_path


class BaseField:
    def __init__(self, required=False, default=None, unique=False, choices=None, null=False):
        self.required = required
        self.default = default
        self.unique = unique
        self.choices = choices
        self.null = null
        self.name = None

    def __set_name__(self, owner, name):
        self.name = name

    def get_default(self):
        if callable(self.default):
            return self.default()
        if isinstance(self.default, (dict, list)):
            return deepcopy(self.default)
        return self.default

    def to_storage(self, value):
        return value

    def from_storage(self, value):
        return value

    def __get__(self, instance, owner):
        if instance is None:
            return self
        getter = getattr(instance, "_get_field_value", None)
        if getter:
            return getter(self.name)
        return instance._data.get(self.name)

    def __set__(self, instance, value):
        setter = getattr(instance, "_set_field_value", None)
        if setter:
            setter(self.name, value)
            return
        instance._data[self.name] = self.from_storage(self.to_storage(value))


class StringField(BaseField):
    pass


class BooleanField(BaseField):
    pass


class IntField(BaseField):
    pass


class FloatField(BaseField):
    pass


class DictField(BaseField):
    def from_storage(self, value):
        return value if isinstance(value, dict) else {}


class DynamicField(BaseField):
    pass


class DateTimeField(BaseField):
    def to_storage(self, value):
        if isinstance(value, datetime.datetime):
            return value.isoformat()
        return value

    def from_storage(self, value):
        if isinstance(value, datetime.datetime) or value is None:
            return value
        if isinstance(value, str):
            try:
                if value.endswith("Z"):
                    value = value[:-1] + "+00:00"
                return datetime.datetime.fromisoformat(value)
            except ValueError:
                return None
        return None


class ListField(BaseField):
    def __init__(self, field=None, **kwargs):
        super().__init__(**kwargs)
        self.field = field

    def to_storage(self, value):
        items = value if isinstance(value, list) else []
        if self.field:
            return [self.field.to_storage(v) for v in items]
        return items

    def from_storage(self, value):
        items = value if isinstance(value, list) else []
        if self.field:
            return [self.field.from_storage(v) for v in items]
        return items


class ReferenceField(BaseField):
    def __init__(self, document_type, **kwargs):
        super().__init__(**kwargs)
        self.document_type = document_type

    def _target_cls(self):
        if isinstance(self.document_type, str):
            return _MODEL_REGISTRY.get(self.document_type)
        return self.document_type

    def to_storage(self, value):
        if value is None:
            return None
        if hasattr(value, "id"):
            return str(value.id)
        if isinstance(value, dict):
            if value.get("_id") is not None:
                return str(value.get("_id"))
            if value.get("id") is not None:
                return str(value.get("id"))
        return str(value)

    def from_storage(self, value):
        if value is None:
            return None
        return str(value)


class EmbeddedDocumentField(BaseField):
    def __init__(self, document_type, **kwargs):
        super().__init__(**kwargs)
        self.document_type = document_type

    def _build(self, value):
        if value is None:
            return None
        if isinstance(value, self.document_type):
            return value
        if isinstance(value, dict):
            return self.document_type(**value)
        return None

    def to_storage(self, value):
        obj = self._build(value)
        return obj.to_dict() if obj else None

    def from_storage(self, value):
        return self._build(value)


class EmbeddedDocumentListField(ListField):
    def __init__(self, document_type, **kwargs):
        super().__init__(field=None, **kwargs)
        self.document_type = document_type

    def to_storage(self, value):
        items = value if isinstance(value, list) else []
        out = []
        for item in items:
            if isinstance(item, self.document_type):
                out.append(item.to_dict())
            elif isinstance(item, dict):
                out.append(self.document_type(**item).to_dict())
        return out

    def from_storage(self, value):
        items = value if isinstance(value, list) else []
        out = []
        for item in items:
            if isinstance(item, self.document_type):
                out.append(item)
            elif isinstance(item, dict):
                out.append(self.document_type(**item))
        return out


class DocumentMeta(type):
    def __new__(mcls, name, bases, attrs):
        fields = {}
        for base in bases:
            fields.update(getattr(base, "_fields", {}))
        for key, val in list(attrs.items()):
            if isinstance(val, BaseField):
                fields[key] = val
        cls = super().__new__(mcls, name, bases, attrs)
        cls._fields = fields

        meta = getattr(cls, "meta", {}) or {}
        cls._meta = meta
        cls._collection = meta.get("collection") or f"{name.lower()}s"
        if "QuerySetDescriptor" in globals():
            cls.objects = QuerySetDescriptor(cls)

        _MODEL_REGISTRY[name] = cls
        return cls


class EmbeddedDocument(metaclass=DocumentMeta):
    meta = {}

    def __init__(self, **kwargs):
        object.__setattr__(self, "_data", {})
        for name, field in self._fields.items():
            self._data[name] = field.get_default()
        for key, value in kwargs.items():
            setattr(self, key, value)

    def _get_field_value(self, name):
        return self._data.get(name)

    def _set_field_value(self, name, value):
        field = self._fields.get(name)
        if field:
            self._data[name] = field.from_storage(field.to_storage(value))
        else:
            self._data[name] = value

    def __getattr__(self, item):
        if item in self._fields or item in self._data:
            return self._data.get(item)
        raise AttributeError(item)

    def __setattr__(self, key, value):
        if key.startswith("_"):
            object.__setattr__(self, key, value)
            return
        self._set_field_value(key, value)

    def to_dict(self):
        out = {}
        for key, value in self._data.items():
            field = self._fields.get(key)
            if field:
                out[key] = field.to_storage(value)
            else:
                out[key] = _serialize_dynamic(value)
        return out

    def to_mongo(self):
        return _MongoDict(self.to_dict())


class Document(EmbeddedDocument, metaclass=DocumentMeta):
    meta = {}

    def __init__(self, **kwargs):
        object.__setattr__(self, "_ref_cache", {})
        super().__init__(**kwargs)
        if "id" in kwargs and kwargs["id"] is not None:
            object.__setattr__(self, "id", str(kwargs["id"]))
        elif getattr(self, "id", None) is None:
            object.__setattr__(self, "id", _new_id())

    def __getattr__(self, item):
        if item in self._fields:
            field = self._fields[item]
            if isinstance(field, ReferenceField):
                raw = self._data.get(item)
                if raw is None:
                    return None
                if item in self._ref_cache:
                    return self._ref_cache[item]
                target = field._target_cls()
                if not target:
                    return None
                doc = target.objects(id=raw).first()
                self._ref_cache[item] = doc
                return doc
            return self._data.get(item)
        if item in self._data:
            return self._data[item]
        raise AttributeError(item)

    def _get_field_value(self, name):
        field = self._fields.get(name)
        if isinstance(field, ReferenceField):
            raw = self._data.get(name)
            if raw is None:
                return None
            if name in self._ref_cache:
                return self._ref_cache[name]
            target = field._target_cls()
            if not target:
                return None
            doc = target.objects(id=raw).first()
            self._ref_cache[name] = doc
            return doc
        return self._data.get(name)

    def _set_field_value(self, name, value):
        field = self._fields.get(name)
        if field:
            if isinstance(field, ReferenceField):
                self._ref_cache.pop(name, None)
                if value is not None and hasattr(value, "id"):
                    self._ref_cache[name] = value
            self._data[name] = field.from_storage(field.to_storage(value))
        else:
            self._data[name] = value

    def __setattr__(self, key, value):
        if key in ("id",):
            object.__setattr__(self, key, str(value) if value is not None else None)
            return
        if key.startswith("_"):
            object.__setattr__(self, key, value)
            return
        self._set_field_value(key, value)

    @classmethod
    def _from_store(cls, doc_id, payload):
        obj = cls(id=doc_id)
        for name, field in cls._fields.items():
            if name in payload:
                obj._data[name] = field.from_storage(payload.get(name))
            elif name not in obj._data:
                obj._data[name] = field.get_default()
        for key, value in payload.items():
            if key not in cls._fields:
                obj._data[key] = _deserialize_dynamic(value)
        return obj

    def _to_store_payload(self):
        payload = {}
        for key, value in self._data.items():
            field = self._fields.get(key)
            if field:
                payload[key] = field.to_storage(value)
            else:
                payload[key] = _serialize_dynamic(value)
        return payload

    @classmethod
    def _all_docs(cls):
        rows = _store.fetch_collection(cls._collection)
        return [cls._from_store(doc_id, payload) for doc_id, payload in rows]

    def save(self):
        now = datetime.datetime.utcnow()
        if "createdAt" in self._fields and not self._data.get("createdAt"):
            self._data["createdAt"] = now
        if "updatedAt" in self._fields:
            self._data["updatedAt"] = now

        self._validate_uniques()
        _store.upsert(self._collection, self.id, self._to_store_payload())
        return self

    def delete(self):
        return _store.delete_ids(self._collection, [self.id])

    def to_mongo(self):
        payload = self._to_store_payload()
        payload["_id"] = self.id
        return _MongoDict(payload)

    def _validate_uniques(self):
        unique_fields = [name for name, field in self._fields.items() if getattr(field, "unique", False)]
        for field_name in unique_fields:
            value = self._data.get(field_name)
            if value in (None, ""):
                continue
            existing = self.__class__.objects(**{field_name: value}).first()
            if existing and str(existing.id) != str(self.id):
                raise ValueError(f"Duplicate value for unique field: {field_name}")

        for idx in self._meta.get("indexes", []) or []:
            if not idx.get("unique"):
                continue
            keys = idx.get("fields", [])
            if not keys:
                continue
            filters = {}
            for key in keys:
                filters[key] = self._data.get(key)
            existing = self.__class__.objects(**filters).first()
            if existing and str(existing.id) != str(self.id):
                joined = ", ".join(keys)
                raise ValueError(f"Duplicate value for unique index: {joined}")


class QuerySetDescriptor:
    def __init__(self, model_cls):
        self.model_cls = model_cls

    def __get__(self, instance, owner):
        return QuerySet(self.model_cls)


class QuerySet:
    def __init__(self, model_cls, filters=None, order_spec=None):
        self.model_cls = model_cls
        self._filters = filters[:] if filters else []
        self._order_spec = order_spec[:] if order_spec else []

    def __call__(self, **kwargs):
        return self.filter(**kwargs)

    def _clone(self):
        return QuerySet(self.model_cls, self._filters, self._order_spec)

    def filter(self, **kwargs):
        clone = self._clone()
        clone._filters.append(kwargs)
        return clone

    def order_by(self, *fields):
        clone = self._clone()
        clone._order_spec = list(fields)
        return clone

    def first(self):
        items = self._evaluate(limit=1)
        return items[0] if items else None

    def count(self):
        return len(self._evaluate())

    def delete(self):
        docs = self._evaluate()
        return _store.delete_ids(self.model_cls._collection, [d.id for d in docs])

    def update(self, **updates):
        set_updates = {}
        for key, value in updates.items():
            if key.startswith("set__"):
                set_updates[key.split("set__", 1)[1]] = value

        changed = 0
        for doc in self._evaluate():
            for field, value in set_updates.items():
                setattr(doc, field, value)
            doc.save()
            changed += 1
        return changed

    def __iter__(self):
        return iter(self._evaluate())

    def __len__(self):
        return len(self._evaluate())

    def __getitem__(self, key):
        data = self._evaluate()
        return data[key]

    def _evaluate(self, limit=None):
        docs = self.model_cls._all_docs()
        for f in self._filters:
            docs = [doc for doc in docs if _doc_matches(doc, f)]

        for field in reversed(self._order_spec):
            reverse = field.startswith("-")
            name = field[1:] if reverse else field
            docs.sort(key=lambda d: _sort_key(_resolve_value(d, name)), reverse=reverse)

        if limit is not None:
            return docs[:limit]
        return docs


def _resolve_value(doc, name):
    if name == "id":
        return str(doc.id)
    if name in doc._fields:
        field = doc._fields[name]
        if isinstance(field, ReferenceField):
            return doc._data.get(name)
    return getattr(doc, name, None)


def _sort_key(value):
    if value is None:
        return (0, "")
    if isinstance(value, datetime.datetime):
        return (1, value.timestamp())
    return (1, str(value).lower())


def _doc_matches(doc, filter_dict):
    if not filter_dict:
        return True

    raw_clause = filter_dict.get("__raw__")
    if raw_clause is not None and not _match_raw(doc, raw_clause):
        return False

    for key, expected in filter_dict.items():
        if key == "__raw__":
            continue

        parts = key.split("__")
        field_name = parts[0]
        op = parts[1] if len(parts) > 1 else "eq"

        actual = _resolve_value(doc, field_name)

        if op == "eq":
            if not _eq_value(actual, expected):
                return False
        elif op == "in":
            expected_list = list(expected or [])
            if not any(_eq_value(actual, item) for item in expected_list):
                return False
        elif op == "icontains":
            if str(expected).lower() not in str(actual or "").lower():
                return False
        elif op == "iexact":
            if str(actual or "").lower() != str(expected or "").lower():
                return False
        else:
            return False

    return True


def _eq_value(actual, expected):
    if hasattr(expected, "id"):
        expected = expected.id
    if hasattr(actual, "id"):
        actual = actual.id
    if isinstance(actual, datetime.datetime) and isinstance(expected, datetime.datetime):
        return actual == expected
    return str(actual) == str(expected)


def _match_raw(doc, raw_clause):
    if not isinstance(raw_clause, dict):
        return True

    # Supports admin user search:
    # {'$or': [{'name': {'$regex': q, '$options': 'i'}}, {'email': {'$regex': q, '$options': 'i'}}]}
    if "$or" in raw_clause:
        rules = raw_clause.get("$or", [])
        for rule in rules:
            if _match_raw(doc, rule):
                return True
        return False

    for field, condition in raw_clause.items():
        actual = _resolve_value(doc, field)
        if isinstance(condition, dict):
            if "$regex" in condition:
                regex = str(condition.get("$regex", ""))
                flags = re.IGNORECASE if "i" in str(condition.get("$options", "")) else 0
                if not re.search(regex, str(actual or ""), flags=flags):
                    return False
            else:
                if "$gte" in condition:
                    gte = condition.get("$gte")
                    if not _gte(actual, gte):
                        return False
                if "$lte" in condition:
                    lte = condition.get("$lte")
                    if not _lte(actual, lte):
                        return False
        else:
            if not _eq_value(actual, condition):
                return False

    return True


def _to_dt(value):
    if isinstance(value, datetime.datetime):
        return value
    if isinstance(value, str):
        try:
            if value.endswith("Z"):
                value = value[:-1] + "+00:00"
            return datetime.datetime.fromisoformat(value)
        except ValueError:
            return None
    return None


def _gte(actual, expected):
    a = _to_dt(actual)
    e = _to_dt(expected)
    if a and e:
        return a >= e
    try:
        return actual >= expected
    except Exception:
        return False


def _lte(actual, expected):
    a = _to_dt(actual)
    e = _to_dt(expected)
    if a and e:
        return a <= e
    try:
        return actual <= expected
    except Exception:
        return False


def _serialize_dynamic(value):
    if isinstance(value, Document):
        return str(value.id)
    if isinstance(value, EmbeddedDocument):
        return value.to_dict()
    if isinstance(value, datetime.datetime):
        return value.isoformat()
    if isinstance(value, list):
        return [_serialize_dynamic(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _serialize_dynamic(v) for k, v in value.items()}
    return value


def _deserialize_dynamic(value):
    if isinstance(value, list):
        return [_deserialize_dynamic(v) for v in value]
    if isinstance(value, dict):
        return {k: _deserialize_dynamic(v) for k, v in value.items()}
    return value


def _new_id():
    return secrets.token_hex(12)
