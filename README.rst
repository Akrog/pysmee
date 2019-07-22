Smee.io CLI
===========

.. image:: https://img.shields.io/pypi/v/pysmee.svg
   :target: https://pypi.python.org/pypi/pysmee

.. image:: https://img.shields.io/pypi/pyversions/pysmee.svg
   :target: https://pypi.python.org/pypi/pysmee

.. image:: https://img.shields.io/:license-apache-blue.svg
   :target: http://www.apache.org/licenses/LICENSE-2.0


Command line client for Smee's webhook payload delivery service

This CLI tool allows you to connect to https://smee.io and see the messages that are coming through it, forward them to an URL, save them, and then replay them from a saved file into https://smee.io or directly into an URL of your choosing.


Features
--------

- Showing messages
- Forwarding messages
- Replaying messages
- Long live support: Unlike the npm smee client that stops working after 4 hours


Examples
--------

- Forwarding messages to a local server:

  ``pysmee forward https://smee.io/xIgtwP3rRcQWPs5e http://localhost:8010/change_hook/github``

- Showing messages and saving them for later:

  ``pysmee show https://smee.io/xIgtwP3rRcQWPs5e --save output.txt``

- Sending saved messages back to smee.io:

  ``pysmee send https://smee.io/xIgtwP3rRcQWPs5e saved.txt``

- Sending saved messages to a local server:

  ``pysmee send http://localhost:8010/change_hook/github saved.txt``
