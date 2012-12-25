#!/usr/bin/env python
import os
import zipfile
import guessit
import requests
from glob import glob
from itertools import chain
from tempfile import mkdtemp
from bs4 import BeautifulSoup
from collections import defaultdict


APIKEY = 'D1BD82E2AE599ADD'
API = 'http://www.thetvdb.com/api/'
APIPATH = API + APIKEY


def getLanguages():
    """Get available language codes from thetvdb.com

    returns : list
    """
    resp = requests.get(os.path.join(APIPATH, '/languages.xml'))
    lang = BeautifulSoup(resp.content)
    return [node for node in (l.string for l in lang.find_all('abbreviation'))]


def checkLanguageSettings(lang, langfile):
    """Verrify that language code in config file is available in thetvdb API.
    lang : str
        2-digit language code, as found in output of getLanguages.

    langfile : str
        language.xml file location

    return : bool
        True if language code is available in API.
    """

    with open(langfile) as f:
        languages = BeautifulSoup(f)

    return lang in [l.string for l in languages.find_all('abbreviation')]


def levenshteinDistance(s1, s2):
    s1 = s1.strip().lower()
    s2 = s2.strip().lower()

    if len(s1) < len(s2):
        return levenshteinDistance(s2, s1)
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


class Series(object):
    """Class to encapsulate file(s) or directorie(s) containing media files from a
    single series.

    Series provides an interface for filesystem operations on these local files.
    """
    def __init__(self, media):
        self.files = self.processPaths(media)
        self.filemap = dict((fname, None) for fname in self.files)
        self.seriesname = None  # Don't change this.  Data must remain normalized!

    def processPaths(self, media):
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
        assert False not in [os.path.isfile(f) for f in fnames], 'One or more files could not be reached.  Check path names!'

        return [f for f in fnames if 'video' in guessit.guess_file_info(f, 'autodetect')['mimetype']]

    def getSeriesName(self):
        """Guess series based on agreement between infered series names for each file.

        return: string
        """

        guesses = []
        for g in (guessit.guess_episode_info(self.getPathElement(f)) for f in self.files):
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

        self.seriesname = ranked[sorted(ranked.keys(), reverse=True)[0]]

    def mapSeriesInfo(self, seriesxml):
        """Using the series information retrieved from getSeriesInfo,
        Associate XML node to a file based on file name and metadata.
        """
        assert seriesxml, 'Scrape instance has no seriesxml attribute.  Set with scrape.getSeriesInfo'

        epNodes = [node for node in (n for n in seriesxml.find_all('episode'))]  # episode nodes
        for fname in self.files:
            guess = guessit.guess_episode_info(self.getPathElement(fname))
            for en in epNodes:
                if guess['season'] == int(en.seasonnumber.string) and guess['episodeNumber'] == int(en.episodenumber.string):
                    self.filemap[fname] = {
                                           'S': en.seasonnumber.string,
                                           'E': en.episodenumber.string,
                                           'seriesname': seriesxml.seriesname.string,
                                           'episodename': en.episodename.string,
                                           'ext': fname.split('.')[-1]
                                          }

    def renameFiles(self):
        """Apply pending renames in self.filemap.  All file renaming
        is atomic.  Old filenames are stored in self.old_

        return: bool
            True if rename is successful.
        """
        success = True

        self.old_ = {}
        try:
            for fname in self.files:
                if self.filemap[fname] is not None:
                    sname = '.'.join(self.filemap[fname]['seriesname'].title().split(' '))
                    ename = '.'.join(self.filemap[fname]['episodename'].title().split(' '))
                    snum = "{0}{1}".format('S', self.filemap[fname]['S'].zfill(2))  # TODO: replace with config file settings
                    enum = "{0}{1}".format('E', self.filemap[fname]['E'].zfill(2))  # TODO: replace with config file settings
                    newname = '.'.join([sname, snum, enum, ename, self.filemap[fname]['ext']])
                    newname = os.path.join(self.getPathElement(fname, False), newname)

                    os.rename(fname, newname)
                    self.old_[newname] = fname
        except:
            success = False
            for key in self.old_:
                os.rename(key, self.old_[key])
        finally:
            return success

    @staticmethod
    def getPathElement(path, fname=True):
        """Retrieve either the file name or the resident directory
        of a file.

        path : str
            /path/to/file.ext

        fname : bool
            If true, return file name
            else, return resident directory of file
        """
        return os.path.split(path)[fname]


class Scrape(object):
    """Class to encapsulate TVDB queries.

    Parameters:
    media : string or list of strings.
        List of filenames or single directory containing files **of the same series**.
    """
    badresp_msg = "Bad response when querying for {0}: <{1}>"

    def __init__(self, tvdbid=None, lang='en'):
        # assert checkLanguageSettings(lang), 'Invalid language setting.'

        self.id = tvdbid
        self.language = lang
        self.seriesxml = None
        self.tmpdir = mkdtemp()

    def querySeriesName(self, seriesname):
        """Query THETVDB for series name.

        return:
            BeautifulSoup instance
        """
        assert seriesname, 'Scrape instance has no seriesname attribute.  Did you run Scrape.getSeriesName?'

        payload = {'seriesname': seriesname, 'language': self.language}
        resp = requests.get(os.path.join(API, "GetSeries.php"), params=payload)
        assert resp.status_code == requests.codes.ok, self.badresp_msg.format("series name", resp.status_code)

        return BeautifulSoup(resp.content).find_all('series')

    def urlretrieve(self, url, outdir):
        """Retrieve binary file at a given url.

        url : str
            url pointing to file to retreive
        outdir : str
            output directory

        return:  bool
            True if successful
        """
        flag = False

        resp = requests.get(url)
        if resp.status_code != requests.codes.ok:
            return flag

        with open(outdir, 'wb') as f:
            f.write(resp.content)
            flag = True

        return flag

    def getSeriesInfo(self, lang='en'):
        """Get information on the series once it has been identified (self.id is not None)

        return:
            Parsed XML object.
        """
        assert self.id, "Scrape instance has no id attribute."

        zfname = lang + ".zip"
        searchstring = os.path.join(APIPATH, 'series', self.id, 'all', zfname)

        assert self.urlretrieve(searchstring, os.path.join(self.tmpdir, zfname)), 'Could not fetch series information.'
        with zipfile.ZipFile(os.path.join(self.tmpdir, zfname)) as zipf:
            xmlname = lang + '.xml'
            zipf.extract(xmlname, self.tmpdir)

        with open(os.path.join(self.tmpdir, xmlname), 'rt') as f:
            self.seriesxml = BeautifulSoup(f)

        return self.seriesxml

    def getTVDBid(self, seriesname, thresh):
        """Get TVDB id number for detected series name.
        """
        hits = self.querySeriesName(seriesname.strip().lower())
        if not len(hits):
            self.id = None
            return self.id

        # if there's only one result, check lev dist and return if it's within acceptable norms
        if len(hits) == 1:
            hit = hits[0]
            sname = hit.seriesname.string.strip().lower()
            ld = levenshteinDistance(sname, seriesname)
            if ld <= thresh:
                self.id = hit.id.string.encode('ascii')
                return self.id
            else:
                self.id = None
                return self.id
        else:
            # else it's longer loop through, checking for exact match (normalized -> stripped/lowered).  If none is found, store lev dist somewhere
            #   then select option with lowest lev dist.
            levd_dict = {}
            for series in hits:  # These are already parsed.
                name = series.SeriesName.string
                if name.strip().lower() == seriesname:
                    self.id = series.id.string
                    return self.id
                else:
                    sname = series.SeriesName.string.strip().lower()
                    levd = levenshteinDistance(sname, seriesname)  # Store lev distance
                    levd_dict[levd] = series
            # Get lowest lev distance here, lookup, assing, return.
            self.id = levd_dict[min(levd_dict.keys)].id.string
