#!/usr/bin/env python
#encoding:utf-8

import os
import unittest
import random

import scrappy.core as scrappy
import scrappy.formatters as formatters


# def test_compare_strings():
#     for _ in range(100):
#         randuni = lambda: unichr(random.randint(0, 0x10ffff))
#         s1_size = random.randint(1, 100)
#         s2_size = random.randint(1, 100)

#         s1 = ''.join([randuni() for _ in xrange(s1_size)])
#         s2 = ''.join([randuni() for _ in xrange(s2_size)])

#         diff = scrappy.compare_strings(s1, s2)

#         assert diff >= 0 and diff <= 1


class Test_Scrape(unittest.TestCase):
    def test_basic(self):
        """Test simple scrape
        """
        s = scrappy.Scrape('its always sunny in philadelphia 1x2.mkv')
        self.assertTrue(s.map_episode_info())

    def test_glob(self):
        s = scrappy.Scrape('*phil*')
        self.assertTrue(s.map_episode_info())

    def test_list(self):
        s = scrappy.Scrape(['its always sunny i n philadelphia 101.mkv',
                            'its always sunny in philadelphia 1x2.mkv',
                            'its always sunny in phil s03e04.avi'])
        self.assertTrue(s.map_episode_info())

    def test_iter(self):
        s = scrappy.Scrape((f for f in os.listdir(os.getcwd()) if 'phil' in f))
        self.assertTrue(s.map_episode_info())

    def test_tvdbid(self):
        s = scrappy.Scrape([f for f in os.listdir(os.getcwd()) if 'phil' in f],
                           tvdbid=75805)
        self.assertTrue(s.map_episode_info())


# class Test_Rename(unittest.TestCase):
#     def test_rename(self):
#         s = scrappy.Scrape([f for f in os.listdir(os.getcwd()) if 'phil' in f])
#         files = s.files
#         self.assertTrue(s.map_episode_info())
#         s.rename_files()
#         self.assertEqual(files, s.files)

#     def test_formatters(self):
#         forms = (
#                  formatters.formatter_default,
#                  formatters.formatter_X0X,
#                  formatters.formatter_longname
#                 )

#         for form in forms:
#             s = scrappy.Scrape([f for f in os.listdir(os.getcwd()) if 'phil' in f],
#                                formatter=form)
#             self.assertTrue(s.map_episode_info())
