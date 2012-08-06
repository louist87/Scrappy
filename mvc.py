#!/usr/bin/env python

import scrappy
import curses


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
    def __init__(self):
        self.controller = Controller(self)

        curses.init_pair(1, curses.COLOR_WHITE, curses.COLOR_BLUE)
        self.menuhead = curses.color_pair(1)
        curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_GRAY)
        self.menunum = curses.color_pair(2)
        curses.init_pair(3, curses.COLOR_GRAY, curses.COLOR_RED)
        self.menuwarn = curses.color_pair(3)

        self.menu = self._main
        curses.wrapper(self._interactive)

    def _interactive(self, scr):
        self.win = curses.newwin(3, 20, 10, 20)  # consider doing this less hackishly
        choices = self.menu()
        running = True
        while running:
            keypress = scr.getch()
            running = self.check_halt(scr, keypress)
            if keypress != -1:
                self.win.clear()
                self.menu = choices[keypress]  # calls to controller methods are done as we enter a menu method
                choices = self.menu()

    def check_halt(self, scr, key):
        if key == ord('q'):
            self.win.clear()
            scr.addstr(0, 0, "Quit? y/[N]", self.menuwarn)
            while True:
                key = scr.getch()
                if key != -1:
                    if key == ord('y'):
                        return False
                    else:
                        return True

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

    def _process_file(self, scr):
        pass

    def _scrape_with_series(self, scr):
        pass

    def _scrape_with_TVDBid(self, scr):
        pass


class Controller(object):
    """Controller interfacing the model and the selected view.
    """
    def __init__(self, view):
        self.view = view
        self.model = Model(self)
    # remember to put autoscrape in here...
