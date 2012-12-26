Scrappy
=======

Rename video files based on information scraped from thetvdb.com!

##Installation

Cloning the repository is the preferred way of installing Scrappy, for the time being.  PIP package coming soon.

##Usage

###Simple API Call

```Python
import scrappy.core as scrappy

# Initialize a scrape
# Series name is automatically inferred
scrape = scrappy.Scrape('its always sunny in philadelphia 101.mkv')

# Query TheTVDB for data and rename
err = 3  # Max error (number of edits) to accept a hit
if scrape.getSeriesInfo(err):  # Returns false if series not found.  Try increasing err.
    scrape.renameFiles(test=True)  # test file rename (no changes committed when test == True)
```

```python
It'S.Always.Sunny.In.Philadelphia.S01E01.The.Gang.Gets.Racist.mkv
```

###Advanced API Use

You can pass wildcards to the `Scrape` constructor:

```python
scrape = scrappy.Scrape('*.mkv')
print scrape.files
```

```python
['its always sunny in philadelphia 101.mkv']
```

You can also pass sequences of paths, which of course may include wildcards.

```python
scrape = scrappy.Scrape(['it's always sunny in philadelphia 101.mkv', '*.avi'])
print scrape.files
```

```python
['its always sunny in philadelphia 101.mkv', 'its always sunny in philadelphia 102.avi']
```

If you make a mistake, you can always revert changes made on the local filesystem.  The old filenames are stored in `scrape.old_`.  Note that `scrape.old_` only appears **after** the file names have been modified.

```python
scrape = scrappy.Scrape('its always sunny in philadelphia 101.mkv')
err = 3  # Max error (number of edits) to accept a hit
if scrape.getSeriesInfo(err):
    scrape.renameFiles()  # No test this time!

print scrape.files
scrape.revertFilenames()
print scrape.files
```

```python
It'S.Always.Sunny.In.Philadelphia.S01E01.The.Gang.Gets.Racist.mkv
['its always sunny in philadelphia 101.mkv']
```

###Application

Coming Soon