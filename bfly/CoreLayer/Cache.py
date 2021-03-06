from AccessLayer import UtilityLayer
import logging as log
import collections
import sys

class Cache(object):
    """ Cache tiles and preloaded keywords

    Arguments
    -----------
    _runtime: :class:`RUNTIME`
        Needed to make attributes for each instance

    Attributes
    -----------
    _max_memory: int
        ``MAX`` from :data:`RUNTIME.CACHE`, and \
the max bytes of memory to be used.
    _cach_meta: str
        ``MAX`` from :data:`RUNTIME.CACHE`, and \
the key for the size of cached keywords
    _cache: Collections.OrderedDict
        A Least recently used ordered dictionary
    _now_memory: int
        The current bytes of memory used

    """
    def __init__(self, _runtime):
        self._max_memory = _runtime.CACHE.MAX.VALUE
        self._cache_meta = _runtime.CACHE.META.NAME
        self._cache = collections.OrderedDict()
        self._now_memory = 0

    def get(self, key):
        """ Get a value from the cache by key

        Arguments
        ----------
        key: str
            The key from a :class:`Query` to access the cache

        Returns
        ---------
        anything
            The value stored in the cache, or an empty list
        """
        try:
            # Get the value from the cache. Add to top.
            value = self._cache.pop(key)
            self._cache[key] = value
            return value
        except KeyError:
            return []

    def set(self, key, value):
        """ Set a key in the cache to a value

        Arguments
        ----------
        key: str
            The key from a :class:`Query` to access the cache
        value: anything
            The keywords or tile value to store in the cache

        Returns
        ---------
        int
            0 if successful and -1 if value is too large
        """

        value_memory = self.value_size(value)
        # Do not cache if value more than total memory
        if value_memory > self._max_memory:
            # Log Value over Max Cache
            msg = "Cannot cache {0}. {1} bytes is over max."
            log.warning(msg.format(key, value_memory))
            return -1
        # Add new item to cache memory count
        self._now_memory += value_memory
        try:
            self._cache.pop(key)
        except KeyError:
            while self._now_memory >= self._max_memory:
                # Remove old item from cache and memory count
                old_value = self._cache.popitem(last=False)[1]
                self._now_memory -= self.value_size(old_value)
        # Add new item to the cache
        self._cache[key] = value
        # Log successful add
        msg = "Add {0} to cache. Cache now {1} bytes."
        log.info(msg.format(key, self._now_memory))
        return 0

    def value_size(self, value):
        """ Get actual memory size of a value

        Arguments
        ----------
        value: anything
            expected to be a dict or a numpy.ndarray

        Returns
        --------
        int:
            the number of bytes used by the value
        """
        if isinstance(value,dict):
            return int(value[self._cache_meta])
        return sys.getsizeof(value)
