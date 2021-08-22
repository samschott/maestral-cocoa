# -*- coding: utf-8 -*-

from setuptools import setup, find_packages


install_requires = [
    "click",
    "importlib_metadata;python_version<'3.8'",
    "importlib_resources;python_version<'3.9'",
    "maestral>=1.4.8",
    "markdown2",
    "toga==0.3.0.dev28",
    "rubicon-objc>=0.4.0",
]

dev_requires = [
    "black",
    "bump2version",
    "flake8",
    "mypy",
    "pre-commit",
    "pytest",
    "pytest-cov",
    "types-pkg_resources",
    "types-requests",
]

setup(
    name="maestral-cocoa",
    author="Sam Schott",
    author_email="sam.schott@outlook.com",
    version="1.4.8",
    url="https://maestral.app",
    description="Open-source Dropbox client for macOS and Linux.",
    license="MIT",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    packages=find_packages("src"),
    package_dir={"": "src"},
    package_data={
        "maestral_cocoa": ["resources/*"],
    },
    python_requires=">=3.6",
    setup_requires=["wheel"],
    install_requires=install_requires,
    extras_require={"dev": dev_requires},
    zip_safe=False,
    entry_points={
        "console_scripts": ["maestral_cocoa=maestral_cocoa.__main__:main"],
        "maestral_gui": ["maestral_cocoa=maestral_cocoa.app:run"],
        "pyinstaller40": ["hook-dirs=maestral_cocoa.__pyinstaller:get_hook_dirs"],
    },
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Operating System :: MacOS",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3 :: Only",
    ],
)
