import sys
from setuptools import setup

setup_requires = []
if set(['pytest', 'test', 'ptr']).intersection(sys.argv):
    setup_requires.append('pytest-runner')

classifiers = [
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 2",
    "Topic :: Software Development :: Libraries",
]

setup(
    name='DeSW',
    version='0.0.2',
    packages=['desw'],
    url='https://bitbucket.org/deginner/desw',
    license='MIT',
    classifiers=classifiers,
    author='deginner',
    author_email='support@deginner.com',
    description='A centralized ledger suitable for use like a cryptocurrency hot wallet.',
    setup_requires=setup_requires,
    package_data={'desw': ['static/swagger.json']},
    install_requires=[
        'sqlalchemy>=1.0.9',
        'secp256k1==0.11',
        "bitjws==0.6.3.1",
        "flask>=0.10.0",
        "flask-login",
        "flask-cors",
        "flask-bitjws>=0.1.1.4",
        "alchemyjsonschema"
    ],
    tests_require=['pytest', 'pytest-cov'],
    extras_require={"build": ["flask-swagger"]}
)
