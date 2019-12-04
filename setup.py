#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup

with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()

requirements = [
    'sseclient==0.0.24',
    'requests',  # no pinning, it's included with seeclient
    'six',  # no pinning, it's included with seeclient
]

test_requirements = [
    # TODO: put package test requirements once we have tests
]

setup(
    name='pysmee',
    version='0.1.1',
    description=("Command line client for smee.io's webhook payload delivery "
                 "service"),
    long_description=readme + '\n\n' + history,
    author="Gorka Eguileor",
    author_email='gorka@eguileor.com',
    url='https://github.com/akrog/pysmee',
    packages=[
        'pysmee',
    ],
    package_dir={'pysmee':
                 'pysmee'},
    include_package_data=True,
    install_requires=requirements,
    license="Apache Software License 2.0",
    zip_safe=False,
    keywords='pysmee',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Natural Language :: English',
        "Programming Language :: Python :: 2",
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],
    test_suite='tests',
    tests_require=test_requirements,
    entry_points={
        'console_scripts': [
            'pysmee=pysmee.pysmee:Main',
        ]
    },
)
