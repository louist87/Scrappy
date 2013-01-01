Scrappy
=======

Rename video files based on information scraped from thetvdb.com!

#Installation

Cloning the repository is the preferred way of installing Scrappy, for the time being.  PIP package coming soon.

#Usage

##Simple API Call

```Python
import scrappy.core as scrappy

# Initialize a scrape
# Series name is automatically inferred
scrape = scrappy.Scrape('its always sunny in philadelphia 101.mkv')

# Query TheTVDB for data and rename
err = .2  # Max error (difference coefficient) to accept result
if scrape.map_episode_info(err):  # Returns false if series not found.  Try increasing err.
    scrape.rename_files(test=True)  # test file rename (no changes committed when test == True)
```

```
It's.Always.Sunny.In.Philadelphia.S01E01.The.Gang.Gets.Racist.mkv
```

##Advanced API Use

###Selecting Video Files

You can use glob matching with the scrape constructor.  Note that **all** video files included in the wildcard (or sequence, as per the examples below) **must be from the same series.**

Again, for good measure:  Create a `Scrape` object **for each series**.

```python
scrape = scrappy.Scrape('*.mkv')
print scrape.files
```

```python
['its always sunny in philadelphia 101.mkv']
```

You can also pass sequences to the constructor.  Sequences can be a mix of:

- Paths to individual files
- Glob patterns
- Directories  (**note:**  experimental.  No nested directories.  No simlinks.  No non-media files.)

```python
scrape = scrappy.Scrape(['it's always sunny in philadelphia 101.mkv', '*.avi'])
print scrape.files
```

```python
['its always sunny in philadelphia 101.mkv', 'its always sunny in philadelphia 102.avi']
```

###Eliminating Guesswork

On rare occasions, scrappy has trouble inferring the TV series.  When this happens, simply pass the TVDB id number to the `tvdbid` argument when initializing `Scrape`.
Doing so guaratees that the series is correctly detected.

Be sure to set the `lang` parameter to the correct value, as well.  Shows will likely not be found on TheTVDB if you're searching for a show with the incorrect language!  This parameter defaults to `en`.

```python
scrape = scrappy.Scrape('*kaamelott*', tvdbid='79175', lang='fr')  # tvdbid should be str
if scrape.map_episode_info(.1):
    scrape.rename_files(test=True)
```

```
Kaamelott.S01.E03.La.Table.De.Breccan.avi
```

###Fixing goofs

If you make a mistake, you can always revert changes made on the local filesystem.

```python
scrape = scrappy.Scrape('its always sunny in philadelphia 101.mkv')
err = .2  # Max error (difference coefficient) to accept result
if scrape.get_series_info(err):
    scrape.rename_files()  # No test this time!

print scrape.files
scrape.revertFilenames()
print scrape.files
```

```
It'S.Always.Sunny.In.Philadelphia.S01E01.The.Gang.Gets.Racist.mkv
['its always sunny in philadelphia 101.mkv']
```

##Application

Coming Soon