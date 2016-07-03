============
znc-relay-in
============
``znc-relay-in`` is a Python ZNC module for passing mosquitto messages to IRC.

Intended for use with `obs <https://github.com/nerdfarm/obs>`_, a service for `mosquitto <http://mosquitto.org>`_ messages to Google Hangouts

Dependencies
============
- ZNC built with ``--enable-python``
- ``modpython``
- Python dependencies (``pip install``): 
  - ``paho-mqtt``

Installation
============
1. Install the dependencies listed above
2. Copy ``relay_in.py`` to your ZNC profile
3. Load the ZNC module::

    /msg *status loadmod relay_in

Configuration
=============
Currently, configuration is done by editing mosquitto client connection parameters in ``relay_in.py``

License
=======
MIT
