#!/usr/bin/env python
from setuptools import setup

setup(
    name='Scrappy',
    version="0.2.7 alpha",
    author='Louis Thibault',
    author_email='louist87@gmail.com',
    packages=['scrappy'],
    include_package_data=True,
    install_requires=['guessit', 'tvdb_api', 'hachoir-metadata', 'hachoir-core', 'hachoir-parser'],
    url='https://github.com/louist87/scrappy',
    license='GPL 3.0',
    description='Rename video files based on information scraped from thetvdb.com',
    keywords=["TVDB", "thetvdb", "rename", "broadcatching", "media"],
    long_description=open('README.rst').read()
)
