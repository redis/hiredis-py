#!/bin/bash

set -e

SUFFIX=$1
if [ -z ${SUFFIX} ]; then
    echo "Supply valid python package extension such as whl or tar.gz. Exiting."
    exit 3
fi

script=`pwd`/${BASH_SOURCE[0]}
HERE=`dirname ${script}`
ROOT=`realpath ${HERE}/../..`

cd ${ROOT}
DESTENV=${ROOT}/.venvforinstall
if [ -d ${DESTENV} ]; then
    rm -rf ${DESTENV}
fi
python -m venv ${DESTENV}
source ${DESTENV}/bin/activate
pip install --upgrade --quiet pip
pip install --quiet -r dev_requirements.txt
python setup.py sdist bdist_wheel

PKG=`ls ${ROOT}/dist/*.${SUFFIX}`
ls -l ${PKG}

# install, run tests
pip install ${PKG}