from distutils.core import setup

import setuptools
from pkg_resources import parse_requirements

setup(
    name='openconnect_okta',
    version='0.0.1',
    url='https://github.com/lvoloshyn/openconnect_with_okta',
    license='MIT License',
    author='lvoloshyn',
    description='GlobalProtect VPN through Okta',
    packages=setuptools.find_packages(exclude=['tests*']),
    install_requires=[str(item) for item in parse_requirements(open('requirements.txt'))],
    entry_points={
        'console_scripts': ['openconnect-okta=openconnect_okta.connect:main'],
    },
    package_data={'': ['hipreport.sh']},
    include_package_data=True,
)
