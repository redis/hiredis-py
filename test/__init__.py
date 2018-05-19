import glob
import sys
from unittest import TestSuite, makeSuite

version = sys.version.split(" ")[0]
majorminor = version[0:3]

# Add path to hiredis.so load path
path = glob.glob("build/lib*-%s/hiredis" % majorminor)[0]
sys.path.insert(0, path)

from . import reader


def tests():
    suite = TestSuite()
    suite.addTest(makeSuite(reader.ReaderTest))
    return suite
