from setuptools import setup, find_packages
from os import path

this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='rsbackup',
    version='1.0',
    packages=find_packages(),
    long_description=long_description,
    long_description_content_type='text/markdown',
    install_requires=[
        'pyyaml==5.1',
        'jsonschema==3.0.1'
    ],
    entry_points={
        'console_scripts':
            ['rsbu = rsbackup.rsbackup:main']
    }
)
