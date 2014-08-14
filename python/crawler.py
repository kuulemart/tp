from urllib2 import urlopen
from json import loads

def dict_recurse(data, search, results):
    if isinstance(data, dict):
        for key, value in data.items():
            if key == search:
                results.add(value)
            else:
                dict_recurse(value, search, results)
    elif isinstance(data, (list, tuple)):
        for value in data:
            dict_recurse(value, search, results)


def get_hrefs(url, seen=set()):
    print url
    seen.add(url)
    hrefs = set()
    data = loads(urlopen(url, timeout=5).read())
    dict_recurse(data, 'href', hrefs)
    result = []
    for href in hrefs:
        if not href in seen:
            result.append(href)
    return result

hrefs = ['http://localhost:8080/api/v1/index']
while hrefs:
    new = []
    map(new.extend, map(get_hrefs, hrefs))
    hrefs = new

