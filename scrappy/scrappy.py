#!/usr/bin/env python
import zipfile
import os.path as path
from ConfigParser import ConfigParser
from tempfile import mkdtemp
from xml.dom.minidom import parse, parseString
from os import rename, listdir
import requests
import guessit

configFile = 'scrappy.conf'
CFG = ConfigParser()
CFG.read(configFile)

APIKEY = 'D1BD82E2AE599ADD'
API = 'http://www.thetvdb.com/api/'
APIPATH = API + APIKEY


def stripTags(node):
    """Removes all <> style tags.

    node : unicode string

    return : unicode string
    """
    # convert in_text to a mutable object (e.g. list)
    nodelist = list(node)
    i, j = 0, 0
    while i < len(nodelist):
        if nodelist[i] == '<':
            while nodelist[i] != '>':
                nodelist.pop(i)
            nodelist.pop(i)
        else:
            i = i + 1
    return ''.join(nodelist)


def getLanguages():
    """Get available language codes from thetvdb.com

    returns : list
    """
    resp = requests.get(path.join(APIPATH, 'languages.xml'))
    lang = parseString(resp.content)
    return [stripTags(node.toxml()) for node in lang.getElementsByTagName('abbreviation')]


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

        series_hits = parseString(resp.content)
        return [node for node in series_hits.getElementsByTagName('Series')]

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

        self.seriesxml = parse(path.join(self.tmpdir, xmlname))
        return self.seriesxml

    def mapSeriesInfo(self):
        """Using the series information retrieved from getSeriesInfo,
        Associate XML node to a file based on file name and metadata.
        """
        assert self.seriesxml, 'Scrape instance has no seriesxml attribute.  Set with scrape.getSeriesInfo'

        ep = (node for node in self.seriesxml.getElementsByTagName('Episode'))
        for fname in self.files:
            guess = guessit.guess_episode_info(path.split(fname)[1])
            # TODO:  CFG entries for all the weird episode ordering (default to above)
            for epNode in ep:
                if guess['season'] == int(stripTags(epNode.getElementsByTagName('SeasonNumber')[0].toxml())):
                    if guess['episodeNumber'] == int(stripTags(epNode.getElementsByTagName('EpisodeNumber')[0].toxml())):
                        newname = {}  # When found, populate iwth information
                        newname['S'] = stripTags(epNode.getElementsByTagName('SeasonNumber')[0].toxml())
                        newname['E'] = stripTags(epNode.getElementsByTagName('EpisodeNumber')[0].toxml())
                        newname['Series'] = stripTags(self.seriesxml.getElementsByTagName('SeriesName')[0].toxml())
                        newname['Title'] = stripTags(epNode.getElementsByTagName('EpisodeName')[0].toxml())
                        newname['ext'] = fname.split('.')[-1]
                        self.filemap[fname] = newname

    def renameFiles(self):
        """Apply pending renames in self.filemap.  All file renaming
        is atomic.  Old filenames are stored in self.old_

        return: bool
            True if rename is successful.
        """
        self.old_ = {}
        for fname in self.files:
            if self.filemap[fname] is not None:
                sname = '.'.join(self.filemap[fname]['Series'].title().split(' '))
                ename = '.'.join(self.filemap[fname]['Title'].title().split(' '))
                snum = "{0}{n.zfill(2)}".format('S', n=self.filemap[fname]['S'])  # TODO: replace n with config file values
                enum = "{0}{n.zfill(2)}".format('E', n=self.filemap[fname]['E'])  # TODO: replace n with config file values
                newname = '.'.join([sname, snum, enum, ename, self.filemap[fname]['ext']])
                newname = path.join(path.split(fname)[0], newname)
                try:
                    rename(fname, newname)
                    self.old_[newname] = fname
                except:
                    for key in self.old_:
                        rename(key, self.old_[key])
                    return False
        return True

    def getSeriesName(self):
        """Guess series name based on filename.

        return: string
        """
        guesses = [guessit.guess_episode_info(path.split(f)[1]) for f in self.files]
        guesses = [guess for guess in guesses if 'series' in guess]
        if guesses == []:
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
                        olsdcore = score[key]
        self.seriesname = bestguess
        return self.seriesname

    def getTVDBid(self, thresh):
        """Get TVDB id number for detected series name.

        return : {string, None}
            Return either ID number or None if none is found.
        """
        hits = self.querySeriesName()
        if not len(hits):
            print "Failed at 1"  # DEBUG
            self.id = None
            return self.id

        # if there's only one result, check lev dist and return if it's within acceptable norms
        if len(hits) == 1:
            seriesname = stripTags(hits[0].getElementsByTagName('SeriesName')[0].toxml()).strip().lower()
            ld = levenshteinDistance(seriesname, self.seriesname)
            if ld <= thresh:
                self.id = stripTags(hits[0].getElementsByTagName('id')[0].toxml()).encode('ascii')
                return self.id
            else:
                print "Failed at 2"  # DEBUG
                self.id = None
                return self.id
        else:
            # else it's longer loop through, checking for exact match (normalized -> stripped/lowered).  If none is found, store lev dist somewhere
            #   then select option with lowest lev dist.
            levd_dict = {}
            for series in hits:  # These are already parsed.
                name = stripTags(series.getElementsByTagName('SeriesName')[0].toxml())
                if name.strip().lower() == self.seriesname:
                    self.id = stripTags(series.getElementsByTagName('id')[0].toxml())
                    return self.id
                else:
                    seriesname = stripTags(series.getElementsByTagName('SeriesName')[0].toxml()).strip().lower()
                    levd = levenshteinDistance(seriesname, self.seriesname)  # Store lev distance
                    levd_dict[levd] = series
            # Get lowest lev distance here, lookup, assing, return.
            self.id = stripTags(levd_dict[min(levd_dict.keys())].getElementsByTagName('id')[0].toxml())
            return self.id
