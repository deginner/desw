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
    version='0.0.3',
    packages=['desw'],
    url='https://github.com/WalletGuild/desw',
    license='MIT',
    classifiers=classifiers,
    author='WalletGuild',
    author_email='support@gitguild.com',
    description='A centralized ledger suitable for use like a cryptocurrency hot wallet.',
    setup_requires=setup_requires,
    package_data={'desw': ['static/swagger.json']},
    install_requires=[
        'sqlalchemy>=1.0.9',
        'sqlalchemy-models>=0.0.6',
        "flask>=0.10.0",
        "flask-login",
        "flask-cors",
        "alchemyjsonschema"
    ],
    tests_require=['pytest', 'pytest-cov'],
    extras_require={"build": ["flask-swagger"]}
)
