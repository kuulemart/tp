import sys, os, logging, __main__
import inspect
from ConfigParser import SafeConfigParser
import psycopg2
import psycopg2.pool
import psycopg2.extras
from bottle import HTTPResponse, HTTPError


class AttrDict(dict):
    def __getattr__(self, name):
        return self.get(name)

    def __setattr__(self, name, value):
        self[name] = value


def read_config(section, config_file=None):
    """
    Reads config file and returns configuration.
    config file name defaults to config.ini when not given as program arg
    """
    if not config_file:
        if len(sys.argv) > 1:
            config_file = sys.argv[1]
        else:
            script = __main__.__file__
            path = os.path.dirname(os.path.abspath(script))
            config_file = os.path.join(path, "config.ini")
    if not os.path.isfile(config_file):
        raise Exception("File %s not found" % config_file)
    cp = SafeConfigParser()
    cp.read(config_file)
    return AttrDict(cp.items(section))


def config_logging(config):
    """
    Configures logging based on config data
    """
    params = {}
    if 'log_file' in config:
        params['filename'] = config['log_file']
    else:
        params['stream'] = sys.stdout
    config.setdefault('log_level', 'info')
    params['level'] = getattr(logging, config['log_level'].upper())
    if 'log_format' in config:
        params['format'] = config['log_format']
    # remove existing handlers
    handlers = logging.root.handlers
    while handlers:
        handlers.pop()
    # do config
    logging.basicConfig(**params)
    return logging


def pool_wrapper(pool, keyword='db', autocommit=True):
    def wrapper(func):
        args = inspect.getargspec(func)[0]
        if keyword not in args:
            return func

        def wrapped(*p, **kw):
            conn = pool.getconn()
            kw[keyword] = conn.cursor()
            try:
                result = func(*p, **kw)
                if autocommit:
                    conn.commit()
                return result
            except:
                conn.rollback()
                raise
            finally:
                pool.putconn(conn)
        return wrapped
    return wrapper


class PgSQLPoolPlugin(object):
    '''
    This plugin passes a pgsql database handle from pool to route callbacks
    that accept a `db` keyword argument. If a callback does not expect
    such a parameter, no connection is made.
    '''

    name = 'pgsqlpool'

    def __init__(self, pool, keyword='db', autocommit=True):
        self.pool = pool
        self.keyword = keyword
        self.autocommit = autocommit

    def setup(self, app):
        '''
        Make sure that other installed plugins don't affect the same keyword argument.
        '''
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
            conn = None
            try:
                conn = self.pool.getconn()
                cur = conn.cursor()
            except HTTPResponse, e:
                raise HTTPError(500, "Database Error", e)

            # Add the connection handle as a keyword argument.
            kwargs[keyword] = cur

            try:
                rv = callback(*args, **kwargs)
                if autocommit:
                    conn.commit()
            except psycopg2.ProgrammingError, e:
                con.rollback()
                raise HTTPError(500, "Database Error", e)
            except HTTPError, e:
                raise
            except HTTPResponse, e:
                if autocommit:
                    conn.commit()
                raise
            finally:
                if conn:
                    self.pool.putconn(conn)
            return rv

        # Replace the route callback with the wrapped one.
        return wrapper