#!/usr/bin/env python
from setuptools import setup
from scrappy.core import __version__

setup(
    name='Scrappy',
    version=__version__,
    author='Louis Thibault',
    author_email='louist87@gmail.com',
    packages=['scrappy'],
    include_package_data=True,
    setup_requires=['guessit', 'tvdb_api', 'ez_setup', 'titlecase', 'hachoir-metadata', 'hachoir-core'],
    install_requires=['guessit', 'tvdb_api', 'ez_setup', 'titlecase', 'hachoir-metadata', 'hachoir-core'],
    url='https://github.com/louist87/scrappy',
    license='GPL 3.0',
    description='Rename video files based on information scraped from thetvdb.com',
    keywords=["TVDB", "thetvdb", "rename", "broadcatching", "media"],
    long_description=open('README.rst').read()
)
