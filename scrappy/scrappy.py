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
import scrappy.core as scrappy

ARGS = docopt(__doc__, version='0.1.0 alpha')
if not ARGS['PATH']:
    ARGS['PATH'] = './'

# load config file
CFG = SafeConfigParser()
if not CFG.read(ARGS['--cfg']):  # call to CFG.read also loads file if it exists
    raise IOError('Configuration file not found.')


def autoscrape():
    pass


def profile_scrape(profile):
    pass

if ARGS['--auto']:
    autoscrape()
elif ARGS['--profile']:
    profile_scrape()
else:
    import scrappy.gui
    scrappy.gui.start(CFG, ARGS)
