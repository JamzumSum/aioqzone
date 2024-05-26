===============
QQQR
===============

.. automodule:: qqqr

.. _QQQR Concepts:

-------------------------
Basic Concepts
-------------------------

.. hint::

  Before referencing the detailed implements directly, a brief description is useful for you
  to understand the overall constructing logic of :mod:`QQQR` package.

- Login logics are packaged into classes named ``xxLogin``, which must inherit from
  :class:`~qqqr.base.LoginBase`.

- :class:`LoginBase` s are reusable. In another word, login data are seperated from login logic.
  The data collecting classes are named ``xxSession``, which must inherit from
  :class:`~qqqr.base.LoginSession`.


--------------------------
Table of Contents
--------------------------

.. toctree::
    :maxdepth: 2
    :glob:

    base
    qr/index
    up/index


^^^^^^^^^^^^^^^^^^^^^^
Miscellaneous
^^^^^^^^^^^^^^^^^^^^^^
.. toctree::
    :maxdepth: 1

    jsjson
    exception
