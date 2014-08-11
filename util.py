import sys, os, logging, __main__
from ConfigParser import SafeConfigParser
import psycopg2
import psycopg2.pool
import psycopg2.extras


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


def connection_pool(*p, **kw):
    _kw = dict(cursor_factory=psycopg2.extras.RealDictCursor)
    _kw.update(kw)
    pool = psycopg2.pool.ThreadedConnectionPool(*p, **_kw)
    def wrapper(func):
        def wrapped(*p, **kw):
            conn = pool.getconn()
            kw['db'] = conn.cursor()
            try:
                result = func(*p, **kw)
                conn.commit()
                return result
            except:
                conn.rollback()
                raise
            finally:
                pool.putconn(conn)
        return wrapped
    return wrapper


