#!/usr/bin/env python
from setuptools import setup

setup(
    name='Scrappy',
    version='0.1.0 alpha',
    author='Louis Thibault',
    author_email='',
    packages=['scrappy'],
    include_package_data=True,
    install_requires=['guessit', 'requests', 'beautifulsoup'],
    url='https://github.com/louist87/scrappy',
    license='GPL 3.0',
    description='TVDB lookup and intelligent file renaming',
    keywords=["XBMC", "TVDB", "thetvdb", "plugin", "rename"],
    long_description=open('README.md').read()
)
