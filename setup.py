#!/usr/bin/env python

try:
    from setuptools import setup, Extension
except ImportError:
    from distutils.core import setup, Extension
import importlib
import glob
import io
import os
import sys


def version():
    loader = importlib.machinery.SourceFileLoader(
        "hiredis.version", "hiredis/version.py")
    module = loader.load_module()
    return module.__version__


def is_hiredis_bundled():
    hiredis_submodule = 'vendor/hiredis'
    if (os.path.exists(hiredis_submodule)
            and not os.path.isfile(hiredis_submodule)):
        return not os.listdir()
    return False


def get_hiredis_bundled_sources():
    hiredis_sources = ("alloc", "async", "hiredis", "net", "read",
                       "sds", "sockcompat")
    if is_hiredis_bundled():
        return ["vendor/hiredis/%s.c" % src for src in hiredis_sources]
    return []


if not is_hiredis_bundled():
    print('the bundled hiredis sources were not found;'
          ' system hiredis will be used\n'
          'to use the bundled hiredis sources instead,'
          ' run "git submodule update --init"')


def get_sources():
    return sorted(glob.glob("src/*.c") + get_hiredis_bundled_sources())


def get_linker_args():
    if 'win32' in sys.platform or 'darwin' in sys.platform:
        return []
    else:
        return ["-Wl,-Bsymbolic", ] + \
            ['-lhiredis'] if not is_hiredis_bundled() else []


def get_compiler_args():
    if 'win32' in sys.platform:
        return []
    else:
        return ["-std=c99"]


def get_libraries():
    if 'win32' in sys.platform:
        return ["ws2_32", ]
    else:
        return []


ext = Extension("hiredis.hiredis",
                sources=get_sources(),
                extra_compile_args=get_compiler_args(),
                extra_link_args=get_linker_args(),
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
    license="MIT",
    packages=["hiredis"],
    package_data={"hiredis": ["hiredis.pyi", "py.typed"]},
    ext_modules=[ext],
    python_requires=">=3.8",
    project_urls={
        "Changes": "https://github.com/redis/hiredis-py/releases",
        "Issue tracker": "https://github.com/redis/hiredis-py/issues",
    },
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: MacOS',
        'Operating System :: POSIX',
        'Programming Language :: C',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3 :: Only',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
        'Programming Language :: Python :: 3.13',
        'Programming Language :: Python :: Implementation :: CPython',
        'Topic :: Software Development',
    ],
)
