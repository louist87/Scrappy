#!/usr/bin/env python
from re import findall
from itertools import repeat
from titlecase import titlecase


class Formatter(object):
    def __init__(self, format, sep='', parser=None):
        self.args = tuple(s for s in findall(r"{(\w+)}", format) if s != 'sep')
        self.format = format
        self.sep = sep
        self.parser = parser

    def __str__(self):
        return self.sep.join(self.format)

    def __repr__(self):
        return "<Formatter object> {0}, sep='{1}', parser={2}".format(self.format,
                                                                      self.sep,
                                                                      self.parser)

    def __call__(self, ep):
        arg_pairs = [(a, v) for a, v in zip(self.args, map(self.lookup, repeat(ep, len(self.args)), self.args))]
        arg_pairs = [(arg, self.chain_fn(self.parser.get(arg, lambda x: x), (av))) for arg, av in arg_pairs] + [('sep', self.sep)]

        # join into a string and replace arguments with their formatted values
        return self.format.format(**dict(arg_pairs))

    def lookup(self, ep, target):
        if target in ep.keys():
            return ep[target]
        elif target in ep.season.show.data.keys():
            return ep.season.show.data[target]

        return ''

    def chain_fn(self, chain, arg):
        for fn in chain:
            arg = fn(arg)

        return arg


stripper = lambda s: s.strip()
zfiller = lambda s: s.zfill(2)
all_lower = lambda s: s.lower()
all_upper = lambda s: s.capitalize()
dot_sep = lambda s: '.'.join([c for c in s.split(' ') if c])


def create_SXXEXX_ecode(snum, enum):
    """e.g.: S01E22
    """
    return ''.join(('S', snum, 'E', enum))


default_parser = {
                  'seriesname': [stripper, zfiller, titlecase, dot_sep],
                  'seasonnumber': [stripper, zfiller],
                  'episodenumber': [stripper, zfiller],
                  'episodename': [stripper, zfiller, titlecase, dot_sep]
                 }

default = Formatter('{seriesname}{sep}S{seasonnumber}{sep}E{episodenumber}{sep}{episodename}',
                    sep='.', parser=default_parser
                   )