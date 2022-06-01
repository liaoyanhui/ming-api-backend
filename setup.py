'''
Description: 
Author: 尚夏
Date: 2021-11-04 13:44:27
LastEditTime: 2022-05-11 14:18:09
FilePath: /mining-api-backend/setup.py
'''
import os
import re

from setuptools import find_packages, setup


def read_version():
    regexp = re.compile(r"^__version__\W*=\W*'([\d.abrc]+)'")
    init_py = os.path.join(os.path.dirname(__file__),
                           'aiohttpdemo_polls', '__init__.py')
    with open(init_py) as f:
        for line in f:
            match = regexp.match(line)
            if match is not None:
                return match.group(1)
        else:
            msg = 'Cannot find version in aiohttpdemo_polls/__init__.py'
            raise RuntimeError(msg)


install_requires = ['aiohttp',
                    'aiopg',
                    'trafaret-config',
                    'webargs',
                    'cryptography',
                    'PyNaCl',
                    'PyJWT',
                    'pyotp',
                    'apscheduler',
                    'aiofiles']


setup(name='mining-api-backend',
      version=1.0,
      description='Mining API backend service',
      platforms=['POSIX'],
      packages=find_packages(),
      include_package_data=True,
      install_requires=install_requires,
      zip_safe=False)
