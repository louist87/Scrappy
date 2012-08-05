#!/usr/bin/env python
import urllib2
import zipfile
import curses
import guessit
# from unicodedata import normalize
from ConfigParser import ConfigParser
from tempfile import mkdtemp
from urllib import urlretrieve
from xml.dom.minidom import parse
from os.path import join, abspath, pardir
from os import rename

configFile = 'scrappy.conf'
CFG = ConfigParser()
CFG.read(configFile)

normalgo = 'NFKD'  # Unicode normalization algorithm
APIKEY = 'D1BD82E2AE599ADD'
API = 'http://www.thetvdb.com/api/'
APIPATH = API + APIKEY

langxml = 'languages.xml'


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
    lang = parse(urllib2.urlopen(join(APIPATH, langxml)))
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


class Scrappy(object):
    """Facade class for Scrape object.

    Most users will want to use this.
    """

    def autoScrape(self, filelist):
        """Perform automated scrape as per parameters in configuration file
        """
        self.scrape = Scrape(filelist)

        if not self.scrape.seriesname:
            self.scrape.seriesname = self.getSeriesName()
        if not self.scrape.id:
            self.scrape.id = self.scrape.getTVDBid(CFG.getint('Auto', 'showthresh'))

        self.scrape.getSeriesInfo()
        self.scrape.mapSeriesInfo()
        self.scrape.renameFiles()

    def interactiveScrape(self):
        curses.wrapper(self._interactive())

    def _interactive(self, scr):
        win = curses.newwin(3, 20, 10, 20)
        curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLUE)
        fn = self._main
        while True:
            win.clear()
            callback = fn(scr)  # execute current function and get callback dict
            keypress = scr.getch()

            if keypress == ord('q'):
                break

            fn = callback.get(keypress, fn)  # return current fn if keypress not in dict

    def _main(self, scr):
        scr.addstr(0, 0, "Main Menu:  Press 'q' to exit any time.", curses.color_pair(1))
        # item 1
        scr.addstr(2, 0, "1.", curses.color_pair(1))
        scr.addstr(2, 4, "Process directory")
        # item 2
        scr.addstr(3, 0, "2.", curses.color_pair(1))
        scr.addstr(3, 4, "Process single file")
        # item 3
        scr.addstr(4, 0, "3.", curses.color_pair(1))
        scr.addstr(4, 4, "Scrape with known series name")
        # item 4
        scr.addstr(5, 0, "4.", curses.color_pair(1))
        scr.addstr(5, 4, "Scrape with known TVDB id number")

        return {ord('1'): self._process_dir, ord('2'): self._process_file,
                ord('3'): self._scrape_with_series, ord('3'): self._scrape_with_TVDBid}  # dict containing callbacks

    def _process_dir(self, scr):
        pass
        # prompt for directory and extract filelist
        # create Scrape object with filelist
        # call _process method (which which just takes the constructed file lists and scrapes)

    def _process_file(self, scr):
        pass
        # prompt for single file
        # place single file into list (i.e.:  [fle] )
        # create scrape object with filelist
        # call _process method

    def _scrape_with_series(self, scr):
        pass

    def _scrape_with_TVDBid(self, scr):
        pass


class Scrape(object):
    """Class to handle file renaming based on TVDB queries.

    Parameters:
    filelist : list of strings
        List of video files **of the same series**.
    """
    def __init__(self, filelist, seriesname=None, tvdbid=None):
        if filelist == [] or filelist == '':
            raise AttributeError('filelist variable contains no data.')

        if isinstance(filelist, str):
            filelist = [filelist]

        self.files = filelist
        self.filemap = {fname: None for fname in self.files}
        self.seriesname = seriesname  # Do not use this to set filename -- data is normalized!  Get data from XML instead.
        self.id = tvdbid
        self.seriesxml = None  # placeholder for XML object from TVDB

        self.tmpdir = mkdtemp()

    def querySeriesName(self):
        """Query THETVDB for series name.

        return:
            List
        """
        if not self.seriesname:
            raise AttributeError('Scrape instance has no seriesname attribute.')

        searchstring = "GetSeries.php?seriesname=" + urllib2.quote(self.seriesname) + "&language=" + urllib2.quote(CFG.get('General', 'language'))
        try:
            series_hits = parse(urllib2.urlopen(join(API, searchstring)))
        except:
            return []

        return [node for node in series_hits.getElementsByTagName('Series')]

    def getSeriesInfo(self):
        """Get information on the series once it has been identified (self.id is not None)

        return:
            Parsed XML object.
        """
        if not self.id:
            raise AttributeError('Scrape instance has no id attribute.')

        zfname = CFG.get('General', 'language') + ".zip"
        searchstring = APIPATH + "/series/" + self.id + "/all/" + zfname
        try:
            urlretrieve(searchstring, join(self.tmpdir, zfname))
        except:
            return None

        with zipfile.ZipFile(join(self.tmpdir, zfname)) as zipf:
            xmlname = CFG.get('General', 'language') + '.xml'
            zipf.extract(xmlname, self.tmpdir)

        self.seriesxml = parse(join(self.tmpdir, xmlname))
        return self.seriesxml

    def mapSeriesInfo(self):
        """Using the series information retrieved from getSeriesInfo,
        Associate XML node to a file based on file name and metadata.
        """
        if not self.seriesxml:
            raise AttributeError('Scrape instance has no seriesxml attribute.  Set with scrape.getSeriesInfo')

        ep = [node for node in self.seriesxml.getElementsByTagName('Episode')]
        for fname in self.files:
            guess = guessit.guess_episode_info(fname)
            # TODO:  CFG entries for all the weird episode ordering (default to above)
            for epNode in ep:
                if guess['season'] == int(stripTags(epNode.getElementsByTagName('SeasonNumber')[0].toxml())):
                    if guess['episodeNumber'] == int(stripTags(epNode.getElementsByTagName('EpisodeNumber')[0].toxml())):
                        rename = {}  # When found, populate iwth information
                        rename['S'] = stripTags(epNode.getElementsByTagName('SeasonNumber')[0].toxml())
                        rename['E'] = stripTags(epNode.getElementsByTagName('EpisodeNumber')[0].toxml())
                        rename['Series'] = stripTags(self.seriesxml.getElementsByTagName('SeriesName')[0].toxml())
                        rename['Title'] = stripTags(epNode.getElementsByTagName('EpisodeName')[0].toxml())
                        rename['ext'] = fname.split('.')[-1]
                        self.filemap[fname] = rename

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
                snum = self.format(self.filemap[fname]['S'], 'S')  # TODO: replace with config file values
                enum = self.format(self.filemap[fname]['E'], 'E')
                newname = '.'.join([sname, snum, enum, ename, self.filemap[fname]['ext']])
                try:
                    rename(fname, newname)
                    self.old_[newname] = fname
                except:
                    for key in self.old_:
                        rename(key, self.old_[key])
                    return False
        return True

    def format(self, n, prefix):
        """Apply formatting to either series or episode number.

        n : str or int
            Series or episode number to be formatted

        prefix : str
            Series or episode label, e.g.:  'E' for 'S01E02' type labelling.
            Pass empty string if no prefix is desired

        return: string
        """
        if not isinstance(n, str):
            n = str(n)

        if int(n) < 10:
            n = '0' + n

        return prefix + n

    def getSeriesName(self):
        """Guess series name based on filename.

        return: string
        """
        guesses = [guessit.guess_episode_info(f) for f in self.files]
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
                score = {key: high_conf[key] * normalCount[key] for key in normalCount}
                bestguess = None
                oldscore = 0.
                for key in score:
                    if score[key] > oldscore:
                        bestguess = key
                        olsdcore = score[key]
        return bestguess

    def getTVDBid(self, thresh):
        """Get TVDB id number for detected series name.

        return : {string, None}
            Return either ID number or None if none is found.
        """
        hits = self.querySeriesName()
        if hits == []:
            print "Failed at 1"
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
                print "Failed at 2"
                self.id = None
                return self.id
        else:
            # else it's longerloop through, checking for exact match (normalized -> stripped/lowered).  If none is found, store lev dist somewhere
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
