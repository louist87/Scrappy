#!/usr/bin/env python
import os
from glob import glob
from itertools import chain, repeat
from collections import defaultdict, deque
from mimetypes import guess_type

import formatters

import guessit
import tvdb_api as tvdb

from hachoir_core.error import HachoirError
from hachoir_core.cmd_line import unicodeFilename
from hachoir_parser import createParser
from hachoir_metadata import extractMetadata

__version__ = '0.2.5 alpha'


def get_path(path):
    return os.path.split(path)[0]


def get_filename(path):
    return os.path.split(path)[1]


def normalize(s):
    return s.strip().lower()


def levenshtein_distance(s1, s2):
    s1 = normalize(s1)
    s2 = normalize(s2)

    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    if not s1:
        return len(s2)

    previous_row = xrange(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def compare_strings(a, b):
    """
    Makes the levenshtein into simple difference coefficient, so that it can be rated as a 0 to 1 value.

    a, b: str
        Strings to compare

    return : float
        Coefficient representing the amount of **difference** between a and b.
    """
    mean = lambda seq: sum(seq) / float(len(seq))
    return max(0, levenshtein_distance(a, b) / mean((len(a), len(b))))


class Scrape(object):
    """Class to encapsulate file(s) or directorie(s) containing media files from a
    single series.

    Series provides an interface for filesystem operations on these local files.
    """

    _api_key = 'D1BD82E2AE599ADD'

    def __init__(self, media, tvdbid=None, lang=None, confidence=0.0):
        # TVDB api
        all_lang = lang or False
        self._api_params = {'language': lang,
                            'search_all_languages': all_lang,
                            'apikey': self._api_key
                           }
        self._api = tvdb.Tvdb(**self._api_params)  # TODO:  render interactive and implement a custom UI

        # self._api = tvdb.Tvdb(apikey=self._api_key,
        #                       language=lang,
        #                       search_all_languages=all_lang
        #                      )  # TODO:  render interactive and implement a custom UI

        # Files
        self._files = FileSystemInterface(media)
        self.filemap = dict((fname, None) for fname in self._files)
        self.revert_filenames = self._files.revert

        self.normalized_seriesname = ''
        self.series = None

        if tvdbid:  # tolerate users who pass ints
            tvdbid = str(tvdbid)
        self.id = tvdbid
        self.language = lang  # input validated in tvdb.Tvdb

        if not self.id:
            self._guess_series_name(confidence)

    def files():
        doc = "The files property."

        def fget(self):
            return tuple(f for f in self._files)

        def fset(self, value):
            raise TypeError('cannot modify attribute')

        def fdel(self):
            raise TypeError('cannot delete attribute')
        return locals()
    files = property(**files())

    def language():
        doc = "The language property."

        def fget(self):
            return self._language

        def fset(self, value):
            self._api_params['language'] = value
            self._api = tvdb.Tvdb(**self._api_params)
            self._language = value

        def fdel(self):
            del self._language
        return locals()
    language = property(**language())

    def _guess_series_name(self, confidence):
        """Guess series based on agreement between infered series names for each file.

        return: string
        """
        guesses = self._guess_from_filename() or self._guess_from_metadata()

        if guesses:
            guesses = [g for g in guesses if g.confidence('series') > confidence]
            high_conf = defaultdict(float)
            normalCount = defaultdict(int)
            for guess in guesses:
                ntitle = normalize(guess['series'])

                normalCount[ntitle] += 1

                if guess.confidence('series') > high_conf[ntitle]:  # will initialize high_conf if no key
                    high_conf[ntitle] = guess.confidence('series')  # keep highest confidence for a given title-guess

            #   Select title with highest rating / occurrence
            ranked = dict((high_conf[series] * normalCount[series], series) for series in normalCount)
            self.normalized_seriesname = ranked[sorted(ranked.keys(), reverse=True)[0]] or None
        else:
            self.normalized_seriesname = None

        return self.normalized_seriesname

    def _guess_from_filename(self):
        guesses = (guessit.guess_episode_info(get_filename(f)) for f in self.files)
        return [g for g in guesses if 'series' in g]

    def _guess_from_metadata(self):
        parse = lambda s: s.split(":")
        guesses = []
        for filename in self.files:
            filename = get_filename(filename)
            filename, realname = unicodeFilename(filename), filename
            parser = createParser(filename, realname)
            if parser:
                try:
                    metadata = extractMetadata(parser)
                except HachoirError:
                    continue

                for line in metadata.exportPlaintext():
                    entries = dict([parse(normalize(l)) for l in line if 'comment' in l or 'title' in l])
                    entries = {k: guessit.guess_episode_info(v) for k, v in entries.items()}
                    if 'title' in entries:
                        guesses.append(entries['title'])
                    else:
                        guesses.append(entries['comment'])
        return guesses

    def map_episode_info(self, thresh, comp_fn=compare_strings):
        """Map episode information to each file.

        thresh : int or float
            String difference threshold to accept a TVDB entry.  Parameter depends on comp_fn.
            float for default comp_fn parameter (compare_strings)

        comp_fn : fn
            String comparison function that returns a measure of the difference between two strings.

        return : tuple or None
            None indicates that no matching series was found
        """
        tvdbid = self.id or False  # Do **not** use None.  Conversion to int fails.

        assert self.id or self.normalized_seriesname is not '', 'could not identify TV series for scrape'
        lookup_key = int(tvdbid) or self.normalized_seriesname

        try:
            self.series = self._api[lookup_key]  # lookup series name
        except tvdb.tvdb_shownotfound:
            pass

        #TODO: pick best series if multiple hits

        self.filemap = dict((f, s) for f, s in zip(self.files, map(self._get_episode_info, self.files)))

        if not self.id:
            self.id = self.series.data['id']

        if not self.normalized_seriesname:
            self.normalized_seriesname = self.series.data['seriesname'].lower()

        return self.series

    def _get_episode_info(self, f):
        """Get episode information for each file from from the tvdb.Series object.

        return : dict or None
            Dict of episode information.
            None indicates that no such episode exists.
        """
        g = guessit.guess_episode_info(f)
        ep = self.series.get(g['season'])
        if ep:
            ep = ep.get(g['episodeNumber'])

        return ep

    def rename_files(self, formatter=formatters.default, test=False):
        """Apply pending renames in self.filemap.  All file renaming
        is atomic.
        """
        for fname in self.files:
            ep = self.filemap[fname]
            if ep is not None:
                newname = '{0}.{ext}'.format(formatter(ep), ext=fname.split('.')[-1])
                if not test:
                    self._files.rename(fname, newname)
                else:
                    print newname


class FileSystemInterface(object):
    def __init__(self, media):
        if not hasattr(media, '__iter__'):
            media = (media,)

        self._files = self._process_files(media)
        assert self._files, 'no data'
        assert filter(os.path.isfile, self._files), 'one or more files unreachable'
        self._old = {f: None for f in self._files}

    def __repr__(self):
        return "<FileSystemInterface> containing {0} files".format(len(self._files))

    def __iter__(self):
        for f in self._files:
            yield f

    def files():
        doc = "Tracked files"

        def fget(self):
            return list(self._files)  # deep copy

        def fset(self, value):
            raise TypeError('use add, extend or pop methods to modify files')

        def fdel(self):
            raise TypeError('use pop or clear to remove items')
        return locals()
    files = property(**files())

    def _process_files(self, media):
        seen = set()
        for f in self._flatten_dirs(chain(*[glob(m) for m in media])):
            if f not in seen:
                seen.add(f)

        # sort, filter video files
        files = []
        for f in seen:
            mtype = guess_type(f, False)[0]
            if mtype and 'video' in mtype:
                files.append(f)

        return sorted(files)

    def _flatten_dirs(self, media):
        for path in media:
            if os.path.isfile(path):
                yield os.path.join(path)
            for d, dirs, files in os.walk(path):
                for f in files:
                    yield os.path.join(path, f)

    def rename(self, old, new):
        os.rename(old, new)
        self._old[new] = old
        self._old.pop(old)

    def revert(self, files=None):
        files = files or self._old.keys()
        if not hasattr(files, '__iter__'):
            files = (files,)

        for k in files:
            self.rename(k, self._old[k])

    def add(self, new):
        new = self._process_files(new)
        if new not in self._files:
            assert os.path.isfile(new), 'file is unreachable'
            self._files = sorted(self._files.append(new))
            self._old[new] = None

    def pop(self, f):
        if isinstance(f, int):
            key = self._files.pop(f)
        else:
            for i, key in enumerate(self._files):
                if key == f:
                    self._files.pop(i)

        self._old.pop(key)

    def clear(self):
        for i in list(self):
            self.pop(i)

    def extend(self, files):
        files = self._process_files(files)
        files = [f for f in files if f not in self._files]
        assert filter(os.path.isfile, files), 'one or more files unreachable'
        self._files.extend(files)
        self._old.update({k: None for k in files})
