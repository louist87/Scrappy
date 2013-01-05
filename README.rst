Scrappy
=======

Rename video files based on information scraped from thetvdb.com!

Installation
============

::

    pip install Scrappy --user

::

Usage
=====

Simple API Call
---------------

::

    import scrappy.core as scrappy

    # Initialize a scrape
    # Series name is automatically inferred
    scrape = scrappy.Scrape('its always sunny in philadelphia 101.mkv')

    # Query TheTVDB for data and rename
    err = .2  # Max error (difference coefficient) to accept result
    if scrape.map_episode_info(err):  # Returns false if series not found.  Try increasing err.
        scrape.rename_files(test=True)  # test file rename (no changes committed when test == True)

::

    It's.Always.Sunny.In.Philadelphia.S01E01.The.Gang.Gets.Racist.mkv

Advanced API Use
----------------

Selecting Video Files
~~~~~~~~~~~~~~~~~~~~~

You can use glob matching with the scrape constructor. Note that **all**
video files included in the wildcard (or sequence, as per the examples
below) **must be from the same series.**

Again, for good measure: Create a ``Scrape`` object **for each series**.

::

    scrape = scrappy.Scrape('*.mkv')
    print scrape.files

::

    ['its always sunny in philadelphia 101.mkv']

You can also pass sequences to the constructor. Sequences can be a mix
of:

-  Paths to individual files
-  Glob patterns
-  Directories

Directories are recursively searched for all files with a video
mimetype, and duplicate paths are automatically filtered.

::

    scrape = scrappy.Scrape(['it's always sunny in philadelphia 101.mkv', '*.avi'])
    print scrape.files

::

    ['its always sunny in philadelphia 101.mkv', 'its always sunny in philadelphia 102.avi']

Eliminating Guesswork
~~~~~~~~~~~~~~~~~~~~~

On rare occasions, scrappy has trouble inferring the TV series. When
this happens, simply pass the TVDB id number to the ``tvdbid`` argument
when initializing ``Scrape``. Doing so guaratees that the series is
correctly detected.

Be sure to set the ``lang`` parameter to the correct value, as well.
Shows will likely not be found on TheTVDB if you're searching for a show
with the incorrect language! By default, all languages are searched.

::

    scrape = scrappy.Scrape('*kaamelott*', tvdbid='79175', lang='fr')  # tvdbid should be str
    if scrape.map_episode_info(.1):
        scrape.rename_files(test=True)

::

    Kaamelott.S01.E03.La.Table.De.Breccan.avi

Fixing goofs
~~~~~~~~~~~~

If you make a mistake, you can always revert changes made on the local
filesystem.

::

    scrape = scrappy.Scrape('its always sunny in philadelphia 101.mkv')
    err = .2  # Max error (difference coefficient) to accept result
    if scrape.get_series_info(err):
        scrape.rename_files()  # No test this time!

    print scrape.files
    scrape.revertFilenames()
    print scrape.files

::

    It's.Always.Sunny.In.Philadelphia.S01E01.The.Gang.Gets.Racist.mkv
    ['its always sunny in philadelphia 101.mkv']

Application
-----------

Scrappy also functions as a command-line and GUI application.

To start the interactive GUI application, invoke the ``scrappy.py``
script without any arguments.

Launching Scrappy *with* command-line arguments will launch the CLI app.
When using the command-line app, you are free to either define all of
the parameters in the form of command-line arguments, or use the
settings defined in the config file (``scrappy/scrappy.conf``)

The Scrappy application docstring is as follows:

::

    Usage:  scrappy [PATH] ... [options]

    -a --auto               Automatically scrape and rename without user interaction.
    -p --profile            User-specified profile
    -l LANG --lang LANG     Specify language code [default: en].
    --confidence            Lower bound to consider a guessed series name [default: 0.]
    --thresh                Threshold for series name matching with TVDB query [default: 0.]
    -t --test               Test run.  Do not modify files.
    -c CONF --cfg CONF      Use alternate config file [default: scrappy.conf]

The ``Auto`` settings defined in ``scrappy.conf`` should work well under
most circumstances, and it is highly recommended that you first attempt
to rename files using the ``--auto`` flag. Passing arguments in addition
to ``--auto`` (or ``--profile``) will override the vaules defined in the
configuration file. This notably offers the possibility of passing the
``--test`` flag in order to see how files will be renamed before
modifying the local filesystem.

The ``--profile`` flag should be followed with the name of a profile
defined in ``scrappy.conf``. By default, two profiles are provided:

-  ``strict_match``: Strict matching requirements
-  ``english``: Search for english-language series and metadata

You are encouraged to define your own profiles or to modify existing
ones to suit your needs. Do so by defining values fo any of the
following variables:

-  ``confidence``: Minimum acceptable confidence in guess when inferring
   series name [float: 0.0 to 1.0]
-  ``lang``: Two-letter language code for TheTVDB lookups [str: 'en',
   'fr', 'pl', ...]
-  ``thresh``: Maximum difference factor between inferred series name
   and TheTVDB query results in order to accept a match [float: 0.0 to
   1.0]
