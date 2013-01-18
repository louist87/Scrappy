Scrappy
=======

Scrappy provides an intuitive interface for renaming video files based on information scraped from thetvdb.com!
In short, you can turn something like ``bsg_301.avi`` into ``Battlestar.Galactica.S03.E01.Occupation``.

Scrappy provides a command-line app and a GUI app (coming soon), as well as a documented API for integrating
scrape-based renaming into 3rd party applications.

.. image:: https://api.travis-ci.org/louist87/Scrappy.png?branch=master

Installation
============

::

    pip install Scrappy --user


*Note*:  tests can be run by invoking ``nosetests -w tests/`` from Scrappy's root directory.

API
===

Simple API Call
~~~~~~~~~~~~~~~

::

    import scrappy.core as scrappy

    # Initialize a scrape
    # Series name is automatically inferred
    scrape = scrappy.Scrape('its always sunny in philadelphia 101.mkv')

    # Query TheTVDB for data and rename
    err = .2  # Max error (difference coefficient) to accept result
    if scrape.map_episode_info(err):  # Returns false if series not found.  Try increasing err.
      scrape.rename_files(test=True)  # test file rename (no changes committed when test == True)

Advanced API Use
~~~~~~~~~~~~~~~~

The scrappy API provides options for:

- Glob pattern matching
- Selecting from file name formats (and defining custom formatters)
- Selecting from multiple TVDB query results
- Fixing errors

Documentation for these functions can be found on the `API wiki page <https://github.com/louist87/Scrappy/wiki/API>`_.

Application
===========

Manual Scraping
~~~~~~~~~~~~~~~

Scrappy also functions as a command-line and GUI application.

To start the interactive GUI application, invoke the ``scrappy.py``
script without specifying any files.

Launching Scrappy while passing files will launch the command-line app.
When using the command-line app, you are free to either define all of
the parameters in the form of command-line arguments, or use
settings defined in the `configuration file <https://github.com/louist87/Scrappy/wiki/Configuration-File>`_.

The Scrappy application docstring is as follows:

::

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

Full documentation for the command-line application can be found `here <https://github.com/louist87/Scrappy/wiki/Command-Line-Application>`_.

Documentation
=============

`Scrappy wiki <https://github.com/louist87/Scrappy/wiki/Documentation>`_
