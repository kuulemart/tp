import sys
from urllib2 import urlopen
from json import loads

def dict_recurse(data, search, results=None):
    # init results on first call
    if results is None:
        results = set()
    if isinstance(data, dict):
        for key, value in data.items():
            if key == search:
                results.add(value)
            else:
                dict_recurse(value, search, results)
    elif isinstance(data, (list, tuple)):
        for value in data:
            dict_recurse(value, search, results)
    return results


def get_hrefs(url, seen=set()):
    if url in seen:
        return []
    print url
    seen.add(url)
    data = loads(urlopen(url, timeout=5).read())
    hrefs = dict_recurse(data, 'href')
    return [href for href in hrefs if href not in seen]


hrefs = [sys.argv[1] if len(sys.argv) > 1 else 'http://localhost:8080/api/v1/index']
while hrefs:
    new = set()
    map(new.update, map(get_hrefs, hrefs))
    hrefs = new

