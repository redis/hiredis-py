#!/usr/bin/env python

try:
    from setuptools import setup, Extension
except ImportError:
    from distutils.core import setup, Extension
import importlib
import glob
import io
import sys


def version():
    loader = importlib.machinery.SourceFileLoader(
        "hiredis.version", "hiredis/version.py")
    module = loader.load_module()
    return module.__version__


if 'win' in sys.platform or 'darwin' in sys.platform:
    extra_link_args = []
else:
    extra_link_args = ["-Wl,-Bsymbolic"]

ext = Extension("hiredis.hiredis",
                sources=sorted(glob.glob("src/*.c") +
                               ["vendor/hiredis/%s.c" % src for src in ("alloc", "async", "hiredis", "net", "read", "sds")]),
                extra_compile_args=["-std=c99"],
                extra_link_args=extra_link_args,
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
    python_requires=">=3.7",
    project_urls={
        "Changes": "https://github.com/redis/hiredis-py/releases",
        "Issue tracker": "https://github.com/redis/hiredis-py/issues",
    },
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: MacOS',
        'Operating System :: POSIX',
        'Programming Language :: C',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: Implementation :: CPython',
        'Topic :: Software Development',
    ],
)
