#!/usr/bin/env python

from unittest import TextTestRunner
import test
import sys

result = TextTestRunner().run(test.tests())
if not result.wasSuccessful():
  sys.exit(1)
