import threading
from tinydb import TinyDB, Query
from tinydb.storages import JSONStorage
from tinydb.middlewares import CachingMiddleware


class TinyDBWrapper:
    # Input: none
    # Output: singleton instances per (path, table_name)
    # Description: Thread-safe singleton wrapper around TinyDB.
    _instances: dict[tuple[str, str], "TinyDBWrapper"] = {}
    _instances_lock = threading.Lock()

    # Input: path (str), table_name (str)
    # Output: TinyDBWrapper instance
    # Description: Ensures only one instance exists per database path and table.
    def __new__(cls, path: str = "db.json", table_name: str = "games"):
        key = (path, table_name)
        with cls._instances_lock:
            if key not in cls._instances:
                inst = super().__new__(cls)
                cls._instances[key] = inst
                inst._initialized = False
            return cls._instances[key]

    # Input: path (str), table_name (str)
    # Output: none
    # Description: Initializes TinyDB connection and table if not already initialized.
    def __init__(self, path: str = "db.json", table_name: str = "games"):
        if getattr(self, "_initialized", False):
            return

        self._db = TinyDB(path, storage=CachingMiddleware(JSONStorage))
        self._table = self._db.table(table_name)
        self._Q = Query()

        self._lock = threading.RLock()

        self._initialized = True

    # Input: document (dict)
    # Output: document ID (int)
    # Description: Inserts a document into the database table.
    def insert(self, document: dict) -> int:
        if not isinstance(document, dict):
            raise TypeError("document must be a dict")
        with self._lock:
            return self._table.insert(document)
        
    # Input: none
    # Output: none
    # Description: Flushes cached data to disk.
    def flush(self) -> None:
        with self._lock:
            storage = getattr(self._db, "storage", None)
            if storage and hasattr(storage, "flush"):
                storage.flush()
        
    # Input: none
    # Output: none
    # Description: Closes the database connection.
    def close(self) -> None:
        with self._lock:
            self._db.close()