from bottle import HTTPResponse, HTTPError
import inspect
import psycopg2

class PgSQLPoolPlugin(object):
    """
    This plugin passes a pgsql database handle from pool to route callbacks
    that accept a `db` keyword argument. If a callback does not expect
    such a parameter, no connection is made.
    """

    name = 'pgsqlpool'

    def __init__(self, pool, keyword='db', autocommit=True):
        self.pool = pool
        self.keyword = keyword
        self.autocommit = autocommit

    def setup(self, app):
        """
        Make sure that other installed plugins don't affect the same keyword argument.
        """
        for other in app.plugins:
            if not isinstance(other, PgSQLPoolPlugin):
                continue
            if other.keyword == self.keyword:
                raise PluginError("Found another pgsqlpool plugin with conflicting settings (non-unique keyword).")

    def apply(self, callback, context):
        # Override global configuration with route-specific values.
        conf = context['config'].get(self.name) or {}
        autocommit = conf.get('autocommit', self.autocommit)
        keyword = conf.get('keyword', self.keyword)

        # Test if the original callback accepts a 'db' keyword.
        # Ignore it if it does not need a database handle.
        args = inspect.getargspec(context['callback'])[0]
        if keyword not in args:
            return callback

        def wrapper(*args, **kwargs):
            # Connect to the database
            con = None
            try:
                con = self.pool.getconn()
                cur = con.cursor()
            except HTTPResponse, e:
                raise HTTPError(500, "Database Error", e)

            # Add the connection handle as a keyword argument.
            kwargs[keyword] = cur

            try:
                rv = callback(*args, **kwargs)
                if autocommit:
                    con.commit()
            except psycopg2.ProgrammingError, e:
                con.rollback()
                raise HTTPError(500, "Database Error", e)
            except HTTPError, e:
                raise
            except HTTPResponse, e:
                if autocommit:
                    con.commit()
                raise
            finally:
                if con:
                    self.pool.putconn(con)
            return rv

        # Replace the route callback with the wrapped one.
        return wrapper