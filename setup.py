import os
from setuptools import setup


# Utility function to read the README file.
# Used for the long_description.  It's nice, because now 1) we have a top level
# README file and 2) it's easier to type in the README file than to put a raw
# string in below ...
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(
    name='django-csv-exporter',
    version='1.2',
    author='Joseph Solomon',
    author_email='josephs@isl.co',
    description=('A django package to export data in a csv with File export.'),
    license='MIT',
    keywords='django csv file image zip',
    url='https://github.com/istrategylabs/django-csv-exporter',
    packages=['csv_exporter', ],
    long_description=read('README.md'),
    classifiers=[
        'Topic :: Utilities',
        'License :: OSI Approved :: MIT License',
    ],
)
