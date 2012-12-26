#!/usr/bin/env python


def formatDotTitle(s):
    """Convert "example title" to "Example.Title"
    """
    return '.'.join(s.title().split(' '))


def formatSXXEXX(season, episode):
    """Produce episode numbering (ecode) following the SXXEXX convention:
    e.g.:  S01E23
    """
    return 'S{0}E{1}'.format(season.zfill(2), episode.zfill(2))


default = {
            'sname': (formatDotTitle, 'seriesname'),  # (fn, keys needed to get params from self.filemap[fname])
            'ename': (formatDotTitle, 'episodename'),
            'ecode': (formatSXXEXX, ('S', 'E')),
            'order': ('sname', 'ecode', 'ename'),  # required
            'sep': '.'    # can be omitted. defaults to '.' in formatFileName
          }
