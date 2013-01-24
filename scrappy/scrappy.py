#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Scrappy:  Rename media files based on scraped information.

Usage:  scrappy [PATH] ... [options]

-a --auto               Automatically scrape and rename without user interaction.
-p PROF --profile PROF  User-specified profile
-i ID --tvdbid ID       Specify TVDB id
-l LANG --lang LANG     Specify language code [default: en].
--confidence            Lower bound to consider a guessed series name [default: 0.]
--thresh                Threshold for series name matching with TVDB query [default: 0.]
--interactive           Manually select show from TVDB query results.
--formatter             Name of formatter to use.  Can be name of formatter in formatters module.
                        or /path/to/file/module.py:formatter_name
-t --test               Test run.  Do not modify files.
--cfg                   Use alternate config file
"""

from yaml import load
from os.path import dirname, join
from docopt import docopt
import core as scrappy
import formatters

ARGS = docopt(__doc__, version="0.3.0 alpha 3")
scrapeargs = ('tvdbid', 'lang', 'confidence', 'interactive', 'formatter', 'query_thresh')
# controlargs = ('auto', 'profile', 'cfg', 'PATH')


ARGS = dict((k.strip('-'), v) for (k, v) in ARGS.items())
with open(ARGS['cfg'] or join(dirname(__file__), 'scrappy.yml')) as f:
    CFG = load(f)

cfg_general = CFG['General'] or {}


class FormatterError(Exception):
    pass


def load_profile(params, profile_name):
    params.update(CFG['Profiles'][profile_name])
    return params


def parse_arguments(args, params):
    params.update(args)
    if 'thresh' in params:
        params['query_thresh'] = params.pop('thresh')
    for k in scrapeargs:
        if params[k] is False or params[k] is None:
            params.pop(k)
    return params


def do_scrape(params):
    s = scrappy.Scrape((ARGS['PATH'], **dict(k, v for (k, v)) in params.items() if k in scrapeargs))
    if s.map_episode_info():
        s.rename_files(test=params['test'])


def get_formatter(formname):
    if '.py:' not in formname:  # assume formatter from scrappy.formatters
        formatter = formatters.__dict__.get(formname)
    else:
        script, name = formname.split(':')
        script = join(dirname(__file__), script)
        import imp
        imp.load_source('formmod', script)
        formmod.__dict__.get(formname)

    if not formatter:
        raise FormatterError('formatter not found')

    return formatter


def main():
    if not ARGS['PATH']:
        raise NotImplementedError('GUI application will be implemented in version 1')
        import scrappy.gui as gui
        gui.start()

    # Set formatter
    if not ARGS['formatter']:
        ARGS['formatter'] = formatters.formatter_default
    else:
        ARGS['formatter'] = get_formatter(ARGS['formatter'])

    # Check if Auto or Profile has been invoked, load as needed
    if ARGS['auto']:
        params = parse_arguments(ARGS, CFG['Auto'])
    elif ARGS['profile']:
        params = parse_arguments(ARGS, load_profile(cfg_general, ARGS['profile']))

    # send traffic
    do_scrape(params)

if __name__ == '__main__':
    main()
