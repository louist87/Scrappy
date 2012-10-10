#!/usr/bin/env python

import scrappy


class Model(object):
    """Abstraction for the handling of Scrape objects.
    """
    def __init__(self, controller):
        self._scrape = None
        self.controller = controller

    def send_traffic(self, media, seriesname=None, tvdbid=None):
        """Issue a database query intelligently, weighing
        known information on the files to be scraped.

        media : str or list of str
            Files or directories to rename.  Must all be for the
            same TV series!

        seriesname : str
            Optional. Name of the series, if known.

        tvdbid : str or int
            Optional.  TVDB id number, if known.  Provides
            best results.

        return: bool
            True if successful
            False if failed
        """
        self._scrape = scrappy.scrape(media, seriesname, tvdbid)
        # Check if TVDB id yields result.
        #   If so, proceed.  If not, fall back to seriesname if present (else abandon)
        ok = False
        if self._scrape.id:
            if self._scrape.getSeriesInfo():
                ok = True
        if not ok and self._scrape.seriesname:
                if not self._scrape.querySeriesName() == []:
                    ok = True
        if not ok:
                ok = self._scrape.getSeriesName() is not None

        return ok

    def commit(self):
        """Rename files atomically.

        return: bool
            True if successful
        """
        return self._scrape.renameFiles()

    def close_scrape(self):
        """Delete Scrape object and release resources.
        """
        self._scrape = None


class CLIView(object):
    """CLI interface for scrappy.
    """
    pass


class GUIView(object):
    """GUI interface for scrappy.
    """
    pass


class Controller(object):
    """Controller interfacing the model and the selected view.
    """
    def __init__(self, view):
        self.view = view
        self.model = Model(self)
    # remember to put autoscrape in here...
