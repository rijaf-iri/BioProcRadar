import os
from setuptools import setup, find_packages

def read(fname):
    try:
        with open(os.path.join(os.path.dirname(__file__), fname)) as fh:
            return fh.read()
    except IOError:
        return ''

requirements = read('requirements.txt').splitlines()
long_description = read('README.md')

setup(
    name='BioProcRadar',
    version='1.0',

    author='Rija Faniriantsoa',
    author_email='rijaf@iri.columbia.edu',
    description='Data processing for BioAPIRadar',
    url='https://github.com/rijaf-iri/BioProcRadar',
    long_description=long_description,
    long_description_content_type='text/markdown',
    packages=find_packages(),

    classifiers=[
        'Programming Language :: Python :: 3',
        'Intended Audience :: National Meteorological and Hydrological Service',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.12',
    install_requires=requirements,
)
