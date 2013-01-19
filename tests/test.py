#!/usr/bin/env python
#encoding:utf-8

import os
import unittest
import random
import string

import scrappy.core as scrappy
# import scrappy.formatters as formatters


def random_unicode(length=10):
    ru = lambda: unichr(random.randint(0, 0x10ffff))
    return ''.join([ru() for _ in xrange(length)])


def random_ascii(length=10):
    ascii = string.printable + string.whitespace
    return ''.join([random.choice(ascii) for _ in xrange(length)])


def test_compare_strings():
    """Test normalized Levenshtein distance.
    """
    hamming = lambda s, ss: sum(ch1 != ch2 for ch1, ch2 in zip(s, ss))
    bigstrn = lambda slen, slen2: float(max(slen, slen2))
    for i in range(1000):
        s1 = random_unicode(random.randint(1, 50))
        s2 = random_unicode(random.randint(1, 50))

        ls1 = len(s1)
        ls2 = len(s2)

        diff = scrappy.compare_strings(s1, s2)
        assert diff >= 0 and diff <= 1
        assert diff >= (max(ls1, ls2) - min(ls1, ls2)) / bigstrn(ls1, ls2)
        if ls1 == ls2:
            assert diff == hamming(s1, s2) / bigstrn(ls1, ls2)
        if diff == 0:
            assert s1 == s2


def test_normalize():
    # ascii test
    for i in xrange(1000):
        scrappy.normalize(random_ascii(i))

    # unicode test
    for i in xrange(1000):
        scrappy.normalize(random_unicode(i))


class Test_Scrape(unittest.TestCase):
    def validate_output(self, scrp, id):
        self.assertTrue(scrp.map_episode_info())
        self.assertEqual(str(scrp.id), str(id))

    def test_basic(self):
        """Test simple scrape
        """
        s = scrappy.Scrape('its always sunny in philadelphia 1x2.mkv')
        self.validate_output(s, '75805')

    def test_glob(self):
        s = scrappy.Scrape('*phil*')
        self.validate_output(s, '75805')

    def test_list(self):
        s = scrappy.Scrape(['its always sunny i n philadelphia 101.mkv',
                            'its always sunny in philadelphia 1x2.mkv',
                            'its always sunny in phil s03e04.avi'])
        self.validate_output(s, '75805')

    def test_iter(self):
        s = scrappy.Scrape((f for f in os.listdir(os.getcwd()) if 'phil' in f))
        self.validate_output(s, '75805')

    def test_tvdbid(self):
        # typo should be ignored bc of tvdbid
        s = scrappy.Scrape('its always sunny i n philadelphia 101.mkv',
                           tvdbid=75805)
        self.validate_output(s, '75805')

    def test_abstract(self):
        s = scrappy.Scrape(['its always sunny i n philadelphia 101.mkv',
                            'its always sunny in philadelphia 1x2.mkv',
                            'its always sunny in phil s03e04.avi'],
                            interface=scrappy.AbstractMediaInterface)
        self.validate_output(s, '75805')


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
