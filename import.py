from pipeline import *
import util

config = util.read_config('importer')
log = util.config_logging(config)

_, table, files = sys.argv

log.info('importing to table %s files %s' % (table, files))
