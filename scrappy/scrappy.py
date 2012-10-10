#!/usr/bin/env python
import zipfile
import os.path as path
from os import rename, listdir
from ConfigParser import ConfigParser
from tempfile import mkdtemp
import requests
import guessit
from bs4 import BeautifulSoup

CFG = ConfigParser()
CFG.read('scrappy.conf')

APIKEY = 'D1BD82E2AE599ADD'
API = 'http://www.thetvdb.com/api/'
APIPATH = API + APIKEY


def getLanguages():
    """Get available language codes from thetvdb.com

    returns : list
    """
    resp = requests.get(path.join(APIPATH, 'languages.xml'))
    lang = BeautifulSoup(resp.content)
    return [node for node in (l.string for l in lang.find_all('abbreviation'))]


def checkLanguageSettings():
    """Verrify that language code in config file is available in thetvdb API.

    return : bool
        True if language code is available in API.
    """
    return CFG.get('General', 'language') in getLanguages()


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


def listdir_fullpath(d):
    return [path.join(d, f) for f in listdir(d)]


class Scrape(object):
    """Class to handle file renaming based on TVDB queries.

    Parameters:
    media : string or list of strings.
        List of filenames or single directory containing files **of the same series**.
    """
    def __init__(self, media, seriesname=None, tvdbid=None):
        assert media != [] or media != '', 'media variable contains no data.'
        if isinstance(media, str):
            media = [media]

        # Flatten directories, get full paths for all files.
        fnames = []
        for item in media:
            if path.isdir(item):
                for fullpath in listdir_fullpath(item):
                    fnames.append(fullpath)
            elif path.isfile(item):
                fnames.append(item)

        assert False not in [path.isfile(f) for f in fnames], 'One or more files could not be reached.  Check path names!'
        self.files = fnames
        self.filemap = dict((fname, None) for fname in self.files)
        self.seriesname = seriesname  # Do not use this to set filename -- data is normalized!  Get data from XML instead.
        self.id = tvdbid
        self.seriesxml = None  # placeholder for XML object from TVDB

        self.tmpdir = mkdtemp()

    def getSeriesName(self):
        """Guess series name based on filename.

        return: string
        """
        guesses = [guessit.guess_episode_info(path.split(f)[1]) for f in self.files]
        guesses = [guess for guess in guesses if 'series' in guess]
        if guesses == []:
            print "DEBUG WARNING:  no guesses found!"  # DEBUG
            return None  # perhaps try looking at metadata?
        else:
            high_conf = {}
            normalCount = {}
            for guess in guesses:
                guess['normalized'] = guess['series'].strip().lower()  # Normalize titles
                if guess['normalized'] in normalCount:
                    normalCount[guess['normalized']] += 1
                else:
                    normalCount[guess['normalized']] = 1
                    high_conf[guess['normalized']] = 0.

                if guess.confidence('series') > high_conf[guess['normalized']]:
                    high_conf[guess['normalized']] = guess.confidence('series')  # Reject all but highest-rated title among identical titles

                #   Select title with highest rating / occurrence
                score = dict((key, high_conf[key] * normalCount[key]) for key in normalCount)
                bestguess = None
                oldscore = 0.
                for key in score:
                    if score[key] > oldscore:
                        bestguess = key
                        oldscore = score[key]

        self.seriesname = bestguess

    def querySeriesName(self):
        """Query THETVDB for series name.

        return:
            List
        """
        assert self.seriesname, 'Scrape instance has no seriesname attribute.  Did you run Scrape.getSeriesName?'

        payload = {'seriesname': self.seriesname, 'language': CFG.get('General', 'language')}
        resp = requests.get(path.join(API, "GetSeries.php"), params=payload)
        if resp.status_code != requests.codes.ok:
            return ()

        return BeautifulSoup(resp.content).find_all('series')

    def urlretrieve(self, url, outdir):
        flag = False

        resp = requests.get(url)
        if resp.status_code != requests.codes.ok:
            return flag

        with open(outdir, 'wb') as f:
            f.write(resp.content)
            flag = True

        return flag

    def getSeriesInfo(self):
        """Get information on the series once it has been identified (self.id is not None)

        return:
            Parsed XML object.
        """
        assert self.id, "Scrape instance has no id attribute."

        zfname = CFG.get('General', 'language') + ".zip"
        searchstring = path.join(APIPATH, 'series', self.id, 'all', zfname)

        assert self.urlretrieve(searchstring, path.join(self.tmpdir, zfname)), 'Could not fetch series information.'
        with zipfile.ZipFile(path.join(self.tmpdir, zfname)) as zipf:
            xmlname = CFG.get('General', 'language') + '.xml'
            zipf.extract(xmlname, self.tmpdir)

        with open(path.join(self.tmpdir, xmlname), 'rt') as f:
            self.seriesxml = BeautifulSoup(f)

    def mapSeriesInfo(self):
        """Using the series information retrieved from getSeriesInfo,
        Associate XML node to a file based on file name and metadata.
        """
        assert self.seriesxml, 'Scrape instance has no seriesxml attribute.  Set with scrape.getSeriesInfo'

        ep = [node for node in (n for n in self.seriesxml.find_all('episode'))]
        for fname in self.files:
            guess = guessit.guess_episode_info(path.split(fname)[1])
            for epNode in ep:
                if guess['season'] == int(epNode.seasonnumber.string):
                    if guess['episodeNumber'] == int(epNode.episodenumber.string):
                        newname = {}  # When found, populate iwth information
                        newname['S'] = epNode.seasonnumber.string
                        newname['E'] = epNode.episodenumber.string
                        newname['seriesname'] = self.seriesxml.seriesname.string
                        newname['episodename'] = epNode.episodename.string
                        newname['ext'] = fname.split('.')[-1]
                        self.filemap[fname] = newname

    def renameFiles(self):
        """Apply pending renames in self.filemap.  All file renaming
        is atomic.  Old filenames are stored in self.old_

        return: bool
            True if rename is successful.
        """
        success = False

        self.old_ = {}
        for fname in self.files:
            if self.filemap[fname] is not None:
                sname = '.'.join(self.filemap[fname]['seriesname'].title().split(' '))
                ename = '.'.join(self.filemap[fname]['episodename'].title().split(' '))
                snum = "{0}{1}".format('S', self.filemap[fname]['S'].zfill(2))  # TODO: replace with config file settings
                enum = "{0}{1}".format('E', self.filemap[fname]['E'].zfill(2))  # TODO: replace with config file settings
                newname = '.'.join([sname, snum, enum, ename, self.filemap[fname]['ext']])
                newname = path.join(path.split(fname)[0], newname)
                try:
                    rename(fname, newname)
                    self.old_[newname] = fname
                    success = True
                except:
                    for key in self.old_:
                        rename(key, self.old_[key])
                finally:
                    return success

    def getTVDBid(self, thresh):
        """Get TVDB id number for detected series name.

        return : {string, None}
            Return either ID number or None if none is found.
        """
        hits = self.querySeriesName()
        if not len(hits):
            self.id = None
            return self.id

        # if there's only one result, check lev dist and return if it's within acceptable norms
        if len(hits) == 1:
            hit = hits[0]
            seriesname = hit.seriesname.string.strip().lower()
            ld = levenshteinDistance(seriesname, self.seriesname)
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
                if name.strip().lower() == self.seriesname:
                    self.id = series.id.string
                    return self.id
                else:
                    seriesname = series.SeriesName.string.strip().lower()
                    levd = levenshteinDistance(seriesname, self.seriesname)  # Store lev distance
                    levd_dict[levd] = series
            # Get lowest lev distance here, lookup, assing, return.
            self.id = levd_dict[min(levd_dict.keys)].id.string
