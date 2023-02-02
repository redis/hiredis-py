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


def get_sources():
    hiredis_sources = ("alloc", "async", "hiredis", "net", "read", "sds", "sockcompat")
    return sorted(glob.glob("src/*.c") + ["vendor/hiredis/%s.c" % src for src in hiredis_sources])


def get_compiler_args():
    if 'win32' in sys.platform:
        return []
    else:
        return ["-std=c99", "-static-libstdc++", "-O2"]


def get_libraries():
    if 'win32' in sys.platform:
        return ["ws2_32",]
    else:
        return []


ext = Extension("hiredis.hiredis",
                sources=get_sources(),
                extra_compile_args=get_compiler_args(),
                libraries=get_libraries(),
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
