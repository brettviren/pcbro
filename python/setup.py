#!/usr/bin/env python
'''
'''

from setuptools import setup, find_packages
setup(
    name = 'wirecell.pcbro',
    version = '0.0',
    packages = find_packages(),
    install_requires = [
        'Click',
        'numpy',
        'matplotlib',
    ],
    entry_points = dict(
        console_scripts = [
            'wirecell-pcbro = wirecell.pcbro.__main__:main',
        ]
    )
)


