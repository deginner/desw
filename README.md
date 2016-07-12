# Shared Wallet

A shared wallet server, for maintaining a centralized ledger of accounts. Accounts can transfer amounts to each other, deposit and withdraw. Currently supports [Bitcoin](http://bitcoin.org) and [Dash](http://dash.org).

# REST + Bitjws + Swagger

This server provides a REST API for operation as a service. The authentication is done using [bitjws](http://github.com/deginner/bitjws).

# Installation

### Pre-requisites

##### System Dependencies

The OpenSSL, Python and libffi development files are required,  which can be accomplished on Debian based systems with:

`apt-get install libssl-dev python-dev libffi-dev`

##### secp256k1

By default it's expected that [secp256k1](https://github.com/bitcoin/secp256k1) is available, so install it before proceeding; make sure to run `./configure --enable-module-recovery`. If you're using some other library that provides the functionality necessary for this, check the __Using a custom library__ section below.

bitjws can be installed by running `pip install bitjws`.

##### Building secp256k1

In case you need to install the `secp256k1` C library, the following sequence of commands is recommended. If you already have `secp256k1`, make sure it was compiled from the expected git commit or it might fail to work due to API incompatibilities.

```
git clone git://github.com/bitcoin/secp256k1.git libsecp256k1
cd libsecp256k1
git checkout d7eb1ae96dfe9d497a26b3e7ff8b6f58e61e400a
./autogen.sh
./configure --enable-module-recovery --enable-module-ecdh --enable-module-schnorr
make
make install
```

Additionally, you may need to set some environmental variables, pointing to the installation above.

```
INCLUDE_DIR=$(readlink -f ./libsecp256k1/include)
LIB_DIR=$(readlink -f ./libsecp256k1/.libs)
python setup.py -q install

LD_LIBRARY_PATH=$(readlink -f ./libsecp256k1/.libs)
```

# Configuration

`desw` and its related plugins share a common configuration file, the operator should set an environment variable like so:

`export DESW_CONFIG_FILE=/path/to/desw-cfg.ini`

`example_cfg.ini` is provided as a configuration template to be customised by the operator.
 
# Plugins

This package is practically useless without installing one or more wallet plugins. The only wallet backend that it comes with is a mockup. Currently supported plugins are: [desw-bitcoin](http://github.com/deginner/desw-bitcoin) and [desw-dash](http://github.com/deginner/desw-dash).

# Bitcoin Examples

For the sake of an example, we'll assume you're starting with the desw-bitcoin plugin, and that you're using Deginner's [bravado-bitjws](http://github.com/deginner/bravado-bitjws) Python client.

##### Register a new user

``` Python
luser = client.get_model('User')(username=username)
user = client.user.addUser(user=luser).result().user
```

##### Get an address

``` Python
addy = client.get_model('Address')(currency='BTC', network='Bitcoin')
address = client.address.createAddress(address=addy).result()
```

##### Get your balances

``` Python
balances = client.balance.getBalance().result()
```

##### Send coins

``` Python
addy = "1Go7y9ZQE3fzkHwWE89n4SbRo1GMEZonLN"
debit = client.debit.sendMoney(debit={'amount': int(0.01 * 1e8),
                              'address': addy,
                              'currency': 'BTC',
                              'network': 'Bitcoin',
                              'state': 'unconfirmed', #ignored
                              'reference': 'test send money BTC internal',
                              'ref_id': ''}).result()
```

# Running Tests

The unit tests require locally running an instance of the server: 

`python desw/server.py`

Unit tests are located at `test/test_account.py` and run with pytest:

`python setup.py pytest`

These tests are not dependent on any of the desw plugins.

Each plugin, e.g. [`desw-bitcoin`](https://github.com/GitGuild/desw-bitcoin), has its own unit tests located at `test/test_rpc.py`.