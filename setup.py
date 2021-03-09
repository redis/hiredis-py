#!/usr/bin/env python

try:
  from setuptools import setup, Extension
except ImportError:
  from distutils.core import setup, Extension
import sys, imp, os, glob, io

def version():
  module = imp.load_source("hiredis.version", "hiredis/version.py")
  return module.__version__

ext = Extension("hiredis.hiredis",
  sources=sorted(glob.glob("src/*.c") +
                 ["vendor/hiredis/%s.c" % src for src in ("alloc", "read", "sds")]),
  include_dirs=["vendor"])

setup(
  name="hiredis",
  version=version(),
  description="Python wrapper for hiredis",
  long_description=io.open('README.md', 'rt', encoding='utf-8').read(),
  long_description_content_type='text/markdown',
  url="https://github.com/redis/hiredis-py",
  author="Jan-Erik Rediger, Pieter Noordhuis",
  author_email="janerik@fnordig.de, pcnoordhuis@gmail.com",
  keywords=["Redis"],
  license="BSD",
  packages=["hiredis"],
  package_data={"hiredis": ["hiredis.pyi", "py.typed"]},
  ext_modules=[ext],
  python_requires=">=3.6",
  classifiers=[
    'Development Status :: 5 - Production/Stable',
    'Intended Audience :: Developers',
    'License :: OSI Approved :: BSD License',
    'Operating System :: MacOS',
    'Operating System :: POSIX',
    'Programming Language :: C',
    'Programming Language :: Python :: 3',
    'Programming Language :: Python :: 3.6',
    'Programming Language :: Python :: 3.7',
    'Programming Language :: Python :: 3.8',
    'Programming Language :: Python :: 3.9',
    'Programming Language :: Python :: Implementation :: CPython',
    'Topic :: Software Development',
  ],
)
