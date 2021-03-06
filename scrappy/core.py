#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from glob import glob
from functools import wraps
from mimetypes import guess_type
from itertools import chain
from collections import defaultdict
from unicodedata import normalize as uninorm

import formatters

import guessit
import tvdb_api as tvdb
from tvdb_ui import BaseUI

from hachoir_core.error import HachoirError
from hachoir_core.cmd_line import unicodeFilename
from hachoir_parser import createParser
from hachoir_metadata import extractMetadata


def normalize_unicode(func, norm_type='NFC', encoding='utf-8'):
    decode = lambda s: s.decode(encoding) if isinstance(s, str) else s

    @wraps(func)
    def wrapper(*args, **kwargs):
        args_normed = []
        args = map(decode, args)
        for a in args:
            if isinstance(a, unicode):
                a = uninorm(norm_type, a)
            args_normed.append(a)

        kwargs_normed = {}
        kwargs = dict(zip(map(decode, kwargs.iterkeys()),
                          map(decode, kwargs.itervalues()))
                      )
        for k, v in kwargs.iteritems():
            if isinstance(k, unicode):
                k = uninorm(norm_type, k)
            if isinstance(v, unicode):
                v = uninorm(norm_type, v)
            kwargs_normed[k] = v
        return func(*args_normed, **kwargs_normed)
    return wrapper


def get_path(path):
    return os.path.split(path)[0]


def get_filename(path):
    return os.path.split(path)[1]


@normalize_unicode
def normalize(s):
    return s.strip().lower()


def levenshtein_distance(s1, s2):
    s1 = normalize(s1)
    s2 = normalize(s2)

    return _levenshtein_distance(s1, s2)


def _levenshtein_distance(s1, s2):
    if len(s1) < len(s2):
        return _levenshtein_distance(s2, s1)
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
    # mean = lambda seq: sum(seq) / float(len(seq))
    print levenshtein_distance(a, b), len(a), len(b)
    return max(0, levenshtein_distance(a, b) / float(max(len(a), len(b))))


class AbstractMediaInterface(object):
    """Base class for all media interfaces.

    Used when Scrappy does not have acccess to actual files on the local filesystem, and must
    deal instead with string-form file names from another program (e.g.: Flexget)
    """
    def __init__(self, media):
        if not hasattr(media, '__iter__'):
            media = (media,)

        self._files = self._process_files(media)
        self._old = dict((f, None) for f in self._files)

    def __repr__(self):
        return u"<{0}> containing {1} files".format(self.__class__.__name__, len(self._files))

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
        # filter duplicates
        seen = set()
        for f in media:
            if f not in seen:
                seen.add(f)

        # sort, filter video files
        files = []
        for f in seen:
            mime_type, _ = guess_type(f, False)  # (mimetype, encoding)
            if mime_type and 'video' in mime_type:
                files.append(self._to_unicode(f))

        return sorted(files)

    def _to_unicode(self, string):
        """Converts a string to Unicode"""
        if isinstance(string, unicode):  # Already unicode!
            return string

        import chardet
        encoding = chardet.detect(string)["encoding"]
        string = string.decode(encoding)
        return string

    def rename(self, old, new):
        self._replace_file_in_list(old, new)
        self._old[new] = old
        self._old.pop(old)

    def _replace_file_in_list(self, old, new):
        for i, f in enumerate(self._files):
            if f == old:
                self._files.pop(i)
                self._files.insert(i, new)

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
        self._files.extend(files)
        self._old.update(dict((k, None) for k in files))


class FileSystemInterface(AbstractMediaInterface):
    """Media Interface for dealing with local files.

    Includes additional checks to ensure that valid files are being
    tracked.
    """
    def __init__(self, media):
        super(FileSystemInterface, self).__init__(media)

        assert self._files, 'no data'
        assert False not in map(os.path.isfile, self._files), 'no file objects'

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
                files.append(self._to_unicode(f))

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
        self._replace_file_in_list(old, new)
        self._old[new] = old
        self._old.pop(old)

    def extend(self, files):
        files = self._process_files(files)
        files = [f for f in files if f not in self._files]
        assert filter(os.path.isfile, files), 'one or more files unreachable'
        self._files.extend(files)
        self._old.upate(dict((k, None) for k in files))


class Scrape(object):
    """Class to encapsulate file(s) or directorie(s) containing media files from a
    single series.

    Series provides an interface for filesystem operations on these local files.
    """

    _api_key = 'D1BD82E2AE599ADD'

    @normalize_unicode
    def __init__(self,
                 media,
                 tvdbid=None,
                 series_name=None,
                 lang=None,
                 confidence=0.0,
                 query_thresh=1.0,
                 interactive=False,
                 grabber=None,
                 formatter=formatters.formatter_default,
                 interface=FileSystemInterface
                ):

        """media : str or unicode
            Path to file, directory or glob pattern to media files.

        interactive : bool
            When true, tvdb_api interactive console is used to select from
            multiple results.

        grabber : tvdb_ui.BaseUI sublcass instance or None
            Grabs appropriate TVDB query result.
            If None, uses default grabber.
            Else, this option overrides `interactive`.

            If None, uses default QueryGrabber.

        formatter : scrappy.formatters.Formatter instance
            Object defining file name format to output.
            The default `Formatter` outputs file names in `seriesname.SXXEXX.episodename.ext` format.

        tvdbid : int or str
            TVDB ID number for the show being queried.

        series_name : unicode or str
            Series name to query.  Note that this bypasses automatic series name inference.

        lang : str or None
            Two-character language abbreviation (e.g.: 'en')

        confidence : float or int
            Minimum confidence index to consider a series-name inference as valid.

        query_thresh : float or int
            Maximum error to accept a result returned by TheTVDB.
            Default 1.0:  accept all TVDB results.
            NOTE:  ignored if not using default grabber.

        interface : AbstractMediaInterface class object
            Object inhereting from AbstractMediaInterface base class.
            The interface object provides a layer of abstraction for working with
            local files or abstract files (strings representing file names).
            By default, the FileSystemInterface class object is selected.
        """
        if series_name:
            self.normalized_seriesname = normalize(series_name)
        else:
            self.normalized_seriesname = None

        # TVDB api
        # if not grabber and not interactive:
        #     grabber = partial(QueryGrabber, parent=self, thresh=query_thresh)

        self._api_params = {'language': lang,
                            'search_all_languages': lang is None,
                            'apikey': self._api_key,
                            'interactive': interactive,
                            'custom_ui': grabber}

        self._api = tvdb.Tvdb(**self._api_params)  # TODO:  render interactive and implement a custom UI

        # Other params
        self.id = tvdbid
        self.language = lang  # input validated in tvdb.Tvdb
        self.series = None
        if tvdbid:  # tolerate users who pass str
            if isinstance(tvdbid, str) or isinstance(tvdbid, unicode):
                tvdbid = int(tvdbid.strip())

        # Files
        self._files = interface(media)
        self.filemap = dict((fname, None) for fname in self._files)
        self.revert_filenames = self._files.revert
        self.formatter = formatter

        if not self.id and not self.normalized_seriesname:
            self._guess_series_name(confidence)

    def files():
        doc = "Files tracked for renaming."

        def fget(self):
            return tuple(f for f in self._files)

        def fset(self, value):
            raise TypeError('cannot modify attribute')

        def fdel(self):
            raise TypeError('cannot delete attribute')
        return locals()
    files = property(**files())

    def language():
        doc = "TVDB query language."

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
            ranked = dict(((high_conf[series] * normalCount[series], series) for series in normalCount))
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
            if not isinstance(filename, unicode):
                filename, realname = unicodeFilename(filename), filename
            else:
                realname = filename

            parser = createParser(filename, realname)
            if parser:
                try:
                    metadata = extractMetadata(parser)
                except HachoirError:
                    continue

                for line in metadata.exportPlaintext():
                    entries = dict((parse(normalize(l)) for l in line if 'comment' in l or 'title' in l))
                    entries = dict(((k, guessit.guess_episode_info(v)) for (k, v) in entries.items()))
                    if 'title' in entries:
                        guesses.append(entries['title'])
                    elif 'comment' in entries:
                        guesses.append(entries['comment'])
        return guesses

    def map_episode_info(self):
        """Map episode information to each file.

        return : tvdb_api.Show or None
            None indicates that no matching series was found
        """
        assert self.id or self.normalized_seriesname, 'could not identify TV series for scrape'
        lookup_key = self.id or self.normalized_seriesname

        try:
            self.series = self._api[lookup_key]  # lookup series name
        except tvdb.tvdb_shownotfound:
            return None

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

    def rename_files(self, test=False):
        """Apply pending renames in self.filemap.  All file renaming
        is atomic.
        """
        for fname in self.files:
            ep = self.filemap[fname]
            if ep is not None:
                newname = u'{0}.{ext}'.format(self.formatter(ep), ext=fname.split('.')[-1])
                newname = os.path.join(get_path(fname), newname)

                # Avoid frivolous renames.  This is important for flexget integration
                # where single files are renamed based on information scraped from titles
                # of other files in the same directory.
                if ep != newname:
                    if not test:
                        self._files.rename(fname, newname)
                    else:
                        print newname


class QueryGrabber(BaseUI):
    def __init__(self,
                 config,
                 log=None,
                 parent=None,
                 thresh=None,
                 round_precision=2,
                 comp_fn=compare_strings):

        BaseUI.__init__(self, config, log)

        if parent is None:
            raise ValueError('no reference to parent Scrape instance.')
        self.parent = parent
        self.thresh = thresh
        self.comp_fn = comp_fn
        self.round_precision = round_precision

    def selectSeries(self, allSeries):
        # Filter by threshold
        allSeries = self.threshold_filter(allSeries)
        if allSeries == []:
            return None
        elif len(allSeries) == 1:
            return allSeries[0]

        # Filter by popularity metrics
        return self.popularity_filter(allSeries)

    def threshold_filter(self, allSeries):
        return [s for s in allSeries if self.comp_fn(s['seriesname'].encode("UTF-8", "ignore"), self.parent.normalized_seriesname) <= self.thresh]

    def popularity_filter(self, allSeries):
        comp = lambda s: self.comp_fn(s['seriesname'].encode("UTF-8", "ignore"), self.parent.normalized_seriesname)
        match = map(self._rounded, map(comp, allSeries))

        unique = set()
        for m in match:
            if m not in unique:
                unique.add(m)
        highval = max(unique)
        highmatch = [allSeries[i] for i, m in enumerate(match) if m == highval]

        if len(highmatch) == 1:
            return highmatch[0]

        popularity = zip(highmatch, map(self._popularity, highmatch))
        return reduce(self._pop_contest, popularity)[0]

    def _rounded(self, factor):
        mvdec = 10 ** self.round_precision  # move decimal point
        return int(round(factor, self.round_precision) * mvdec)

    def _pop_contest(self, s1, s2):
        s1_show, s1_pop = s1
        s2_show, s2_pop = s2
        if s1_pop > s2_pop:
            return s2_show, s2_pop
        return s1_show, s1_pop

    def _popularity(self, show):
        tvdbid = show['id']
        showdat = tvdb.Tvdb(language=self.parent.language, apikey=self.parent._api_key)[tvdbid].data
        score = 1.0 - (float(showdat['rating']) / int(showdat['ratingcount']))
        if score > 0:
            return score
        return 0.0
