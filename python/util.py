import sys, os, logging, __main__, string
import json
import inspect
from ConfigParser import SafeConfigParser
from StringIO import StringIO
import psycopg2
import psycopg2.pool
import psycopg2.extras


class AttrDict(dict):
    """
    Extended dict with items accessible as attributes
    """
    def __getattr__(self, name):
        return self.get(name)

    def __setattr__(self, name, value):
        self[name] = value

    def getint(self, key, default=0):
        return int(self.get(key, default))

    def getstr(self, key, default=''):
        return str(self.get(key, default))

    def getfloat(self, key, default=0.0):
        return float(self.get(key, default))

    def getlist(self, key, default=None, itemtype=None):
        value = self.get(key, default or [])
        if isinstance(value, tuple):
            value = list(value)
        elif isinstance(value, str):
            value = map(string.strip, value.split(','))
        elif not isinstance(value, list):
            value = [value]
        if itemtype:
            value = map(itemtype, value)
        return value


def script_dir():
    """
    Current script dir
    """
    try:
        script = __main__.__file__
        return os.path.dirname(os.path.abspath(script))
    except AttributeError:
        return os.getcwd()


def read_config(section, config_file=None, defaults=None):
    """
    Reads config file and returns configuration.
    config file name defaults to config.ini when not given as program arg
    """
    if not config_file:
        if len(sys.argv) > 1:
            config_file = sys.argv[1]
        else:
            path = script_dir()
            config_file = os.path.join(path, "config.ini")
    if not os.path.isfile(config_file):
        raise Exception("File %s not found" % config_file)
    cp = SafeConfigParser()
    cp.read(config_file)
    config = AttrDict(defaults or {})
    if cp.has_section(section):
        config.update(cp.items(section))
    return config


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


def db_wrapper(dsn, keyword='db', autocommit=True):
    def wrapper(func):
        args = inspect.getargspec(func)[0]
        if keyword not in args:
            return func

        def wrapped(*p, **kw):
            conn = psycopg2.connect(dsn, cursor_factory=psycopg2.extras.RealDictCursor)
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
                conn.close()
        return wrapped
    return wrapper


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


class DB:
    """
    Database connection helper
    """
    def __init__(self, dsn, **kwargs):
        kwargs.setdefault('cursor_factory', psycopg2.extras.RealDictCursor)
        self.dsn = dsn
        self.kwargs = kwargs
        self._con = None

    @property
    def con(self):
        """
        lazy connect
        """
        if not self._con:
            self._con = psycopg2.connect(self.dsn, **self.kwargs)
        return self._con

    @classmethod
    def from_config(cls, config):
        return cls(config.db)

    def __getattr__(self, name):
        return getattr(self.con, name)

    def load_data(self, data, table, columns=None, clean=False, transactional=False):
        try:
            if columns:
                # get column data from dict
                data = ([row[col] for con in columns] if isinstance(row, dict) else row
                    for row in data)
            # join columns
            data = (row if isinstance(row, str) else '\t'.join(row) for row in data)
            # join lines and make StringIO object
            f = StringIO('\n'.join(data))
            if clean:
                self.truncate(table)
            cur = self.cursor()
            cur.copy_from(f, table, columns=columns)
            if transactional:
                self.commit()
        except:
            if transactional:
                self.rollback()
            raise

    copy_from = load_data

    def truncate(self, table):
        return self.execute('truncate table %s' % table)

    def query(self, sql, params=()):
        cur = self.con.cursor()
        cur.execute(sql, params)
        return cur.fetchall()

    select = query

    def execute(self, sql, params=()):
        cur = self.con.cursor()
        cur.execute(sql, params)
        return cur

    def queryproc(self, proc, params=()):
        cur = self.con.cursor()
        cur.callproc(proc, params)
        return cur.fetchall()

    callproc = queryproc

    def execproc(self, proc, params=()):
        cur = self.con.cursor()
        cur.callproc(proc, params)
        return cur


class Query:
    """
    SQL query builder

    Builds sql from given parts
    """

    def __init__(self, db, sql=None, params=None):
        """
        db - database cursor object
        sql - initial sql part
        params - initial params value
        """
        self.db = db
        self.sql = []
        # result row map. when col name is in map, value is replaced with result
        # of mapping function
        self.map = {}
        # query parameters
        self.params = AttrDict(params or {})
        self.add(sql, sql)

    def add(self, sql, cond=True, params=None):
        """
        Adds SQL part if condition is True
        """
        if cond:
            self.sql.append(sql)
            params and self.params.update(params)
        return self

    def get_sql(self):
        """
        Returns SQL string
        """
        return "\n".join(self.sql)

    def execute(self, **kw):
        """
        Execute SQL with self.params + call params and map result values
        """
        params = {}
        params.update(self.params)
        params.update(kw)
        self.db.execute(self.get_sql(), params)
        result = self.db.fetchall()
        map(
            lambda r: r.update((k, f(r[k])) for k,f in self.map.items()),
            result
        )
        return result

    __call__ = execute

    def first(self, **kw):
        result = self.execute(**kw)
        if result:
            return result[0]
        else:
            return {}


# geometry object conversions


def geojson_to_arr_coord(geojson):
    """
    converts geojson to array of coordinates
    """
    geojson = json.loads(geojson)
    coords = geojson['coordinates']
    if geojson['type'] == 'Polygon':
        coords = coords[0]
    return coords

def arr_coord_to_area(arr_coord):
    """
    converts coordinate array to json containing {sw:..., ne:...}
    """
    # convert coordinates to string
    join = ','.join
    coords = map(join, [map(str, coord) for coord in arr_coord])
    return json.dumps({
        'sw': coords[0],
        'ne': coords[2]
    })

def geojson_to_area(geojson):
    return arr_coord_to_area(geojson_to_arr_coord(geojson))

def geojson_to_lng_lat_dict(geojson):
    coords = map(str, geojson_to_arr_coord(geojson))
    return {
        "lng": coords[0],
        "lat": coords[1],
        "point": ','.join(coords),
    }

def geojson_to_point(geojson):
    return ','.join(map(str, geojson_to_arr_coord(geojson)))

