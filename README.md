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
if scrape.getSeriesInfo(err):
    scrape.renameFiles(test=True)  # commit changes
```

###Advanced API Use

To DO

###Application

Coming Soon