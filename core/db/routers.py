class SQLiteRouter:
    """Route models có __db_alias__ = 'sqlite' sang SQLite, tất cả còn lại sang Cassandra."""

    def db_for_read(self, model, **hints):
        if getattr(model, '__db_alias__', None) == 'sqlite':
            return 'sqlite'
        return None

    def db_for_write(self, model, **hints):
        if getattr(model, '__db_alias__', None) == 'sqlite':
            return 'sqlite'
        return None

    def allow_relation(self, obj1, obj2, **hints):
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if db == 'sqlite':
            return True
        if db == 'default':
            return False
        return None
