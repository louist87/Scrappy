#!/usr/bin/env python
import os
from glob import glob
from itertools import chain
from collections import defaultdict

import formatters

import guessit
import tvdb_api as tvdb

__version__ = '0.1.3 alpha'


def levenshtein_distance(s1, s2):
    s1 = s1.strip().lower()
    s2 = s2.strip().lower()

    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    if not s1:
        return len(s2)

    previous_row = xrange(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1  # j+1 instead of j since previous_row and current_row are one character longer than s2
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

    def __init__(self, media, tvdbid=None, lang='en'):
    #     assert check_language_settings(lang), 'Invalid language setting.'

        self._api = tvdb.Tvdb(apikey=self._api_key, language=lang)  # TODO:  render interactive and implement a custom UI

        self.files = self.process_paths(media)
        self.filemap = dict((fname, None) for fname in self.files)
        self.normalized_seriesname = ''
        self.series = None

        self.id = tvdbid
        self.language = lang

        if not self.id:
            self.get_series_name()

    def process_paths(self, media):
        """Validate paths and format into a flat list of full paths.
        """
        if isinstance(media, str):
            media = (media,)

        media = chain(*[glob(m) for m in media])

        fnames = []
        for path in media:
            if os.path.isdir(path):
                fnames.extend(glob(os.path.join(path, '*')))
            elif os.path.isfile(path):
                fnames.append(path)

        assert len(fnames), 'media contains no data.'
        assert all([os.path.isfile(f) for f in fnames]), 'One or more files could not be reached.  Check path names!'

        return [f for f in fnames if 'video' in guessit.guess_file_info(f, 'autodetect')['mimetype']]

    def get_series_name(self):
        """Guess series based on agreement between infered series names for each file.

        return: string
        """

        guesses = []
        for g in (guessit.guess_episode_info(self.get_path_element(f)) for f in self.files):
            if 'series' in g:
                guesses.append(g)  # dictionary of guessed information

        if guesses == []:
            print "DEBUG WARNING:  no guesses found!"  # DEBUG
            return None  # perhaps try looking at metadata?
        else:
            high_conf = defaultdict(float)
            normalCount = defaultdict(int)
            for guess in guesses:
                ntitle = guess['series'].strip().lower()  # normalize title

                normalCount[ntitle] += 1

                if guess.confidence('series') > high_conf[ntitle]:  # will initialize high_conf if no key
                    high_conf[ntitle] = guess.confidence('series')  # keep highest confidence for a given title-guess

            #   Select title with highest rating / occurrence
            ranked = dict((high_conf[series] * normalCount[series], series) for series in normalCount)

        self.normalized_seriesname = ranked[sorted(ranked.keys(), reverse=True)[0]] or None
        return self.normalized_seriesname

    def map_episode_info(self, thresh, comp_fn=compare_strings, lang='en'):
        """Map episode information to each file.

        thresh : int or float
            String difference threshold to accept a TVDB entry.  Parameter depends on comp_fn.
            float for default comp_fn parameter (compare_strings)

        comp_fn : fn
            String comparison function that returns a measure of the difference between two strings.

        lang : str
            Two-letter language code
            Default = 'en'

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
        is atomic.  Old filenames are stored in self.old_

        formatter : dict #### TO DO:  REPLACE WITH REGEX
            Dictionary used to format file names.
            The formatter **must** contain a key called 'order', which contains
                the keys that will be used in the construction of the new file name.
                Elements will be in the same order as this sequence.

            The formatter may then contain arbitrarily named keys that map to a tuple containing
                an associated function **AND** the names of the keys in a dictionary returned from
                `guessit.guess_episode_info` that map to its parameters.

                EXAMPLES:
                *  formatter['ecode'] = (lambda s, e: s.capitalize() + e.capitalize(), ('S', 'E'))
                *  formatter['sname'] - (lambda s: s.title(), 'seriesname')

            Lastly, the formatter may **optionally** contain a 'sep' field containing a separator that
                will delimit the above fields in the new file name.  If none is provided, the separator
                will default to '.'

        test : bool
            If True, no files are modified, but verbose output is provided for debugging

        return: bool
            True if rename is successful.
        """
        success = True
        old = {}

        try:
            for fname in self.files:
                ep = self.filemap[fname]
                if ep is not None:
                    newname = formatter(ep)
                    if not test:
                        os.rename(fname, newname)
                        old[newname] = fname
                    else:
                        print newname

            self.old_ = old  # dynamically add attribute
        except IOError:
            success = False
            if not test:
                self.revert_filenames(_override=old)

        finally:
            return success

    def revert_filenames(self, _override=None):
        """Undo a file rename.  Function performs no action unless files have been renamed

        _override : dict
            For internal use.  Do not use.
        """
        if hasattr(self, 'old_') or _override:
            old = _override or self.old_
            for key in old:
                os.rename(key, old[key])

    def get_path_element(self, path, fname=True):
        """Retrieve either the file name or the resident directory
        of a file.

        path : str
            /path/to/file.ext

        fname : bool
            If true, return file name
            else, return resident directory of file
        """
        return os.path.split(path)[fname]
