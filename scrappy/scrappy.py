#!/usr/bin/env python

"""Scrappy:  Rename media files based on scraped information.

Usage:  scrappy [PATH] ... [options]

-a --auto               Automatically scrape and rename without user interaction.
-p --profile            User-specified profile
-l LANG --lang LANG     Specify language code [default: en].
--scan-individual       Evaluate series information individually for each file.
-c CONF --cfg CONF      User alternate config file [default: scrappy.conf]
-t --test               Test run.  Do not modify files.
-v --verbose            Print verbose output
"""

from ConfigParser import SafeConfigParser
from docopt import docopt
import core as scrappy

ARGS = docopt(__doc__, version=scrappy.__version__)
if not ARGS['PATH']:
    ARGS['PATH'] = './'

# load config file
CFG = SafeConfigParser()
if not CFG.read(ARGS['--cfg']):  # call to CFG.read also loads file if it exists
    raise IOError('Configuration file not found.')


def parse_arguments():
    path = ARGS.pop('PATH')

    kwargs = {}
    cli = {}
    for k in ARGS:
        k = k.strip('-')
        if k not in ('auto', 'profile', 'scan-individual', 'cfg', 'test', 'verbose'):
            kwargs[k] = ARGS['--' + k]
        else:
            cli[k] = ARGS['--' + k]

    return path, kwargs, cli


def autoscrape():
    path, kwargs, cli = parse_arguments()

    if 'thresh' in kwargs:
        thresh = kwargs.pop('thresh')
    else:
        thresh = 0.0

    s = scrappy.Scrape(path, **kwargs)
    if s.map_episode_info(thresh):
        s.rename_files(test=cli['test'])


def profile_scrape(profile):
    pass


if __name__ == '__main__':
    if ARGS['--auto']:
        autoscrape()
    elif ARGS['--profile']:
        profile_scrape()
    else:
        import scrappy.gui
        scrappy.gui.start(CFG, ARGS)
