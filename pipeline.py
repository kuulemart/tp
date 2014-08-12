from pprint import pprint
import string


class cat:
    """
    >>> p = cat((1,2,3))|foreach(lambda item: item+1)
    >>> p(list)
    [2, 3, 4]
    """
    def __init__(self, pipe):
        self.pipe = iter(pipe)

    def __or__(self, right):
        self.pipe = right(self.pipe)
        return self

    def __iter__(self):
        return self.pipe

    def __call__(self, *p):
        res = self.pipe
        for func in p:
            res = func(res)
        return res

def foreach(func):
    def process(pipe):
        for item in pipe:
            yield func(item)
    return process

def tee(func):
    """
    >>> items = [1, 2, 3]
    >>> target = []
    >>> list(tee(target.append)(items))
    [1, 2, 3]
    >>> target
    [1, 2, 3]
    """
    def process(pipe):
        for obj in pipe:
            func(obj)
            yield obj
    return process

def null(pipe):
    """
    >>> null([1,2,3])

    """
    for obj in pipe:
        pass

def skip(head=0, tail=0):
    """
    >>> list(skip(head=1,tail=2)([1,2,3,4,5]))
    [2, 3]
    >>> list(skip(head=3)([1,2,3,4,5]))
    [4, 5]
    >>> list(skip(tail=3)([1,2,3,4,5]))
    [1, 2]
    """
    def process(pipe):
        buf = []
        for i, line in enumerate(pipe):
            if i < head:
                continue
            if tail > len(buf):
                buf.append(line)
                continue
            buf.append(line)
            yield buf.pop(0)
    return process

def head(count):
    """
    >>> list(head(count=2)([1,2,3,4,5]))
    [1, 2]
    """
    def process(pipe):
        for i, line in enumerate(pipe):
            if i < count:
                yield line
    return process

def tail(count):
    """
    >>> list(tail(count=2)([1,2,3,4,5]))
    [4, 5]
    """
    def process(pipe):
        buf = []
        for line in pipe:
            if len(buf) >= count:
                buf.pop(0)
            buf.append(line)
        for line in buf:
            yield line
    return process

def split(sep='|', cols=None, proc=string.strip):
    """
    >>> items = ['a | b ', 'c |d']
    >>> list(split()(items))
    [['a', 'b'], ['c', 'd']]
    >>> list(split(cols=['f1', 'f2'])(items))
    [{'f1': 'a', 'f2': 'b'}, {'f1': 'c', 'f2': 'd'}]
    """
    def process(pipe):
        for line in pipe:
            row = line.split(sep)
            if proc:
                row = map(proc, row)
            if cols:
                row = dict(zip(cols, row))
            yield row
    return process

def join(sep='\t', cols=None):
    """
    >>> items = [['a', 'b'], ['c', 'd']]
    >>> list(join(sep=',')(items))
    ['a,b', 'c,d']
    >>> list(join(sep=',', cols=[1,0])(items))
    ['b,a', 'd,c']
    >>> items = [{'f1': 'a', 'f2': 'b'}, {'f1': 'c', 'f2': 'd'}]
    >>> list(join(sep='|', cols=['f2', 'f1'])(items))
    ['b|a', 'd|c']
    """
    def process(pipe):
        for row in pipe:
            if cols:
                row = [row[col] for col in cols]
            yield sep.join(row)
    return process

def header(*p):
    """
    >>> items = ['c', 'd']
    >>> list(header('a', 'b')(items))
    ['a', 'b', 'c', 'd']
    """
    def process(pipe):
        for item in p:
            yield item
        for item in pipe:
            yield item
    return process

def footer(*p):
    """
    >>> items = ['a', 'b']
    >>> list(footer('c', 'd')(items))
    ['a', 'b', 'c', 'd']
    """
    def process(pipe):
        for item in pipe:
            yield item
        for item in p:
            yield item
    return process

if __name__ == "__main__":
    import doctest
    doctest.testmod()