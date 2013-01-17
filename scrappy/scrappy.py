#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Scrappy:  Rename media files based on scraped information.

Usage:  scrappy [PATH] ... [options]

-a --auto               Automatically scrape and rename without user interaction.
-p --profile            User-specified profile
-i ID --tvdbid ID       Specify TVDB id
-l LANG --lang LANG     Specify language code [default: en].
--confidence            Lower bound to consider a guessed series name [default: 0.]
--thresh                Threshold for series name matching with TVDB query [default: 0.]
--interactive           Manually select show from TVDB query results.
-t --test               Test run.  Do not modify files.
-c --cfg                Use alternate config file
"""

from yaml import load
from os.path import dirname, join
from docopt import docopt
import core as scrappy

ARGS = docopt(__doc__, version="0.2.10 beta 7")
scrapeargs = ('tvdbid', 'lang', 'confidence', 'interactive')
# controlargs = ('auto', 'profile', 'cfg', 'PATH')


ARGS = {k.strip('-'): v for k, v in ARGS.items()}
with open(ARGS['cfg'] or join(dirname(__file__), 'scrappy.yml')) as f:
    CFG = load(f)

params = CFG['General'] or {}


def load_profile(params, profile_name):
    return params.update(CFG['Profiles'][profile_name])


def parse_arguments(args, params):
    params.update(args)
    return params


def do_scrape(params):
    s = scrappy.Scrape(ARGS['PATH'], **{k: v for k, v in params.items() if k in scrapeargs})
    if s.map_episode_info(thresh=params['thresh']):
        s.rename_files(test=params['test'])


def main():
    if not ARGS['PATH']:
        raise NotImplementedError('GUI application will be implemented in version 1')
        import scrappy.gui as gui
        gui.start()

    if ARGS['auto']:
        ARGS.update(CFG['Auto'])
        params = ARGS
    elif ARGS['profile']:
        params = parse_arguments(ARGS, load_profile(ARGS['profile']))

    do_scrape(params)

if __name__ == '__main__':
    main()
