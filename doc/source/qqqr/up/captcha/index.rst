=============================
Solving Captcha
=============================

--------------------
Basic Concepts
--------------------

Captcha solving follows the concepts we've introduced in :ref:`Basic Concepts <QQQR Concepts>`.
The captcha verifying logic also keeps code and data seperated by design.

- :class:`~qqqr.up.captcha.Captcha` holds the captcha solving and verifying procedure.

- Each captcha has its own ``xxCaptchaSession`` inherited from
  :class:`~qqqr.up.captcha.capsess.BaseTcaptchaSession` which saves data received from the server.

- All "solving" are hidden behind :external+tylisten:mod:`tylisten` hook framework. These
  hooks serve as placeholders in the verify processes. Downstreams are free to register their
  implementations to these hooks.
  We unify machine and human solutions by defining the hook interfaces
  while not have to maintain any builtin solutuion, thus ensure the maintainability.

----------------------
Supported Captcha
----------------------

Currently we support two kinds of captcha:

1. Slide captcha

.. seealso::

   Since slide captcha rarely present since 2023, to keep maintainability of this package while
   reducing the necessary dependencies, we moved the slide-captcha machine solution into an
   independent package `slide-tc`_. This package is an extra dependency of QQQR (aioqzone).

2. Select captcha


------------------------------
Table of Contents
------------------------------

.. toctree::
    :maxdepth: 1
    :glob:

    *


------------------
Links
------------------

The :mod:`captcha` package relys on aioqzone dependency toolchains:

- `pychaosvm`_: a chaosvm executor in Python.

.. seealso::

    Formerly we use ``NodeJS`` to encode password and execute chaosvm. Now these are
    replaced by :class:`~qqqr.up.encrypt.TeaEncoder` and `pychaosvm`_.

- :external:mod:`tylisten`: a hook framework with async support.



.. _slide-tc: https://github.com/aioqzone/slide-tc
.. _pychaosvm: https://github.com/aioqzone/pychaosvm
