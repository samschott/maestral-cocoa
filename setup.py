# -*- coding: utf-8 -*-

from setuptools import setup, find_packages
from maestral_cocoa import __author__, __version__


setup(
    name='maestral-cocoa',
    version=__version__,
    description='Open-source Dropbox client for macOS and Linux.',
    url='https://github.com/SamSchott/maestral',
    author=__author__,
    author_email='ss2151@cam.ac.uk',
    license='MIT',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    packages=find_packages(),
    package_data={
        'maestral_cocoa': ['resources/*'],
    },
    setup_requires=['wheel'],
    install_requires=[
        'bugsnag',
        'click',
        'maestral>=1.0.0',
        'markdown2',
        'toga==0.3.0.dev19',
    ],
    zip_safe=False,
    entry_points={
        'console_scripts': ['maestral_cocoa=maestral_cocoa.main:run_cli'],
    },
    python_requires='>=3.6',
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Operating System :: MacOS',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3 :: Only',
    ],
)
