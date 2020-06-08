# -*- coding: utf-8 -*-
from setuptools import setup

packages = [
    "basis",
    "basis.cli",
    "basis.core",
    "basis.core.conversion",
    "basis.core.extraction",
    "basis.core.metadata",
    "basis.core.sql",
    "basis.db",
    "basis.indexing",
    "basis.utils",
]

package_data = {"": ["*"], "basis.core.sql": ["templates/*"]}

install_requires = [
    "click>=7.1.1,<8.0.0",
    "colorful>=0.5.4,<0.6.0",
    "halo>=0.0.29,<0.0.30",
    "jinja2>=2.11.1,<3.0.0",
    "networkx>=2.4,<3.0",
    "pandas>=1.0.1,<2.0.0",
    "psycopg2-binary==2.8.4",
    "ratelimit>=2.2.1,<3.0.0",
    "requests>=2.23.0,<3.0.0",
    "sqlalchemy>=1.3.13,<2.0.0",
    "strictyaml>=1.0.6,<2.0.0",
]

entry_points = {"console_scripts": ["dream = basis.cli:app"]}

setup_kwargs = {
    "name": "basis",
    "version": "0.1.0",
    "description": "Functional typed data pipelines",
    "long_description": None,
    "author": "Ken Van Haren",
    "author_email": "kenvanharen@gmail.com",
    "maintainer": None,
    "maintainer_email": None,
    "url": None,
    "packages": packages,
    "package_data": package_data,
    "install_requires": install_requires,
    "entry_points": entry_points,
    "python_requires": ">=3.7,<4.0",
}


setup(**setup_kwargs)

# This setup.py was autogenerated using poetry.