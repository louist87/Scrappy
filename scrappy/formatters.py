#!/usr/bin/env python


def format_dot_title(s):
    """Convert "example title" to "Example.Title"
    """
    return '.'.join(s.title().split(' '))


def format_SXXEXX(season, episode):
    """Produce episode numbering (ecode) following the SXXEXX convention:
    e.g.:  S01E23
    """
    return 'S{0}E{1}'.format(season.zfill(2), episode.zfill(2))


default = {
            'sname': (format_dot_title, 'seriesname'),  # (fn, keys needed to get params from self.filemap[fname])
            'ename': (format_dot_title, 'episodename'),
            'ecode': (format_SXXEXX, ('S', 'E')),
            'order': ('sname', 'ecode', 'ename'),  # required
            'sep': '.'    # can be omitted. defaults to '.' in formatFileName
          }
