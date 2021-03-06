
.. include:: global.rst

The AccessLayer
============================

You can ``import`` from ``./`` or with :mod:`bfly` installed_.

.. code-block:: python

    from bfly import AccessLayer

Or, in scripts in some directories:

.. code-block:: python

    # if './bfly/' in sys.path
    from CoreLayer import AccessLayer
    # if './bfly/CoreLayer/' in sys.path 
    import AccessLayer

You can ``from AccessLayer import`` :ref:`all QueryLayer`.

.. code-block:: python

    # if './bfly/CoreLayer' in sys.path
    from AccessLayer import QueryLayer, ImageLayer, UtilityLayer

AccessLayer
------------------
.. module:: bfly.CoreLayer.AccessLayer
.. automodule:: AccessLayer

You can import ``AccessLayer`` from :mod:`bfly` and :mod:`CoreLayer`.


AccessLayer classes
************************* 
.. autoclass:: Websocket
    :members:
.. autoclass:: NDStore
    :members:
.. autoclass:: API
    :members:
.. autoclass:: Precomputed
    :members:
.. autoclass:: StaticHandler
    :members:

Request Handler base class
****************************

.. autoclass:: RequestHandler
    :members:

    .. automethod :: get_query_argument

.. _installed: https://github.com/Rhoana/butterfly#butterfly-installation
