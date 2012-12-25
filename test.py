#!/usr/bin/env python
import scrappy.core as scrappy


series = scrappy.Series('its always sunny in philadelphia 101.mkv')
series.getSeriesName()

scrape = scrappy.Scrape()
scrape.getTVDBid(series.seriesname, 3)
scrape.getSeriesInfo()

series.mapSeriesInfo(scrape.seriesxml)
print series.filemap
#series.renameFiles()
