#!/usr/bin/env python

"""Scrappy:  Rename media files based on scraped information.

Usage:  scrappy [PATH] ... [options]

-a --auto               Automatically scrape and rename without user interaction.
-p --profile            User-specified profile
-i --tvdbid             Specify TVDB id
-l LANG --lang LANG     Specify language code [default: en].
--confidence            Lower bound to consider a guessed series name [default: 0.]
--thresh                Threshold for series name matching with TVDB query [default: 0.]
-t --test               Test run.  Do not modify files.
-c --cfg                Use alternate config file
"""

from ConfigParser import SafeConfigParser
from os.path import dirname, join
from docopt import docopt
import core as scrappy

ARGS = docopt(__doc__, version=scrappy.__version__)

CFG = SafeConfigParser()
cfg_file = ARGS['--cfg'] or join(dirname(__file__), 'scrappy.conf')
if not CFG.read(cfg_file):  # also loads file if it exists
    raise IOError('Configuration file not found.')


def parse_arguments():
    path = ARGS.pop('PATH')

    kwargs = {}
    coms = {}
    for k in ARGS:
        k = k.strip('-')
        if k not in ('auto', 'profile', 'scan-individual', 'cfg', 'test', 'verbose'):
            kwargs[k] = ARGS['--' + k]
        else:
            coms[k] = ARGS['--' + k]

    return path, kwargs, coms


def autoscrape():
    path, kwargs, coms = parse_arguments()
    kwargs.update(CFG.items('Auto'))
    if 'thresh' in kwargs:
        thresh = kwargs.pop('thresh')
    else:
        thresh = 0.0

    _execute_scrape(thresh, path, kwargs, coms)


def profile_scrape(profile):
    path, kwargs, coms = parse_arguments()
    kwargs.update(CFG.items(profile))
    if 'thresh' in kwargs:
        thresh = kwargs.pop('thresh')
    else:
        thresh = 0.0

    _execute_scrape(thresh, path, kwargs, coms)


def default_scrape():
    path, kwargs, coms = parse_arguments()
    kwargs.update(CFG.items('Default'))  # Get global defaults
    thresh = kwargs.pop('thresh')

    s = scrappy.Scrape(path, **kwargs)
    if s.map_episode_info(thresh):
        s.rename_files(test=coms['test'])


def _execute_scrape(thresh, path, kwargs, coms):
    s = scrappy.Scrape(path, **kwargs)
    if s.map_episode_info(thresh):
        s.rename_files(test=coms['test'])


def main():
    if ARGS['--auto']:
        autoscrape()
    elif ARGS['--profile']:
        profile_scrape()
    elif not ARGS['PATH']:
        import scrappy.gui as gui
        gui.start(CFG, ARGS)
    else:
        default_scrape()


if __name__ == '__main__':
    main()
