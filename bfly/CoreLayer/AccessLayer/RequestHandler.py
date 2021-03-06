import os
import logging as log
from tornado import web, gen
from urllib2 import URLError
from mimetypes import types_map
from QueryLayer import UtilityLayer
from pkg_resources import resource_string
from concurrent.futures import ThreadPoolExecutor

class RequestHandler(web.RequestHandler):
    """ Responds to requests from :data:`bfly.Webserver._webapp`

    Attributes
    ------------
    INPUT: :class:`INPUT`
        Static input keywords for all in :mod:`AccessLayer`
    RUNTIME: :class:`RUNTIME`
        Static runtime keywords for all in :mod:`AccessLayer`
    OUTPUT: :class:`OUTPUT`
        Static output keywords for all in :mod:`AccessLayer`
    BFLY_CONFIG: dict
        All data from rh-config

    _ex: ``concurrent.futures.ThreadPoolExecutor``
        Allows handling of parallel requests
    _core: :class:`CoreLayer.Core`
        Converts a request into a response
    _db: :class:`DatabaseLayer.Database`
        Loads data for :class:`INPUT` ``.METHODS.FEATURE``

    :h:`Methods`

    """
    _basic_mime = 'text/plain'
    INPUT = UtilityLayer.INPUT()
    OUTPUT = UtilityLayer.OUTPUT()
    RUNTIME = UtilityLayer.RUNTIME()

    def initialize(self, _core, _db, _config, _root=''):
        """ Bind Core, database, and configuration

        Arguments
        ----------
        _core: :class:`CoreLayer.Core`
            set to :data:`_core`
        _db: :class:`CoreLayer.Database`
            set to :data:`_db`
        _config: dict
            set to :data:`BFLY_CONFIG`
        """
        self._ex = ThreadPoolExecutor(max_workers=10)
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header('Access-Control-Allow-Methods', 'GET')
        self._core = _core
        self._root = _root
        self._db = _db
        # Set the config dict
        self.BFLY_CONFIG = _config

    def parse(self, request):
        """ Extract details from any of the methods

        Must be overridden by derived classes

        Arguments
        ----------
        request: str
            The single method requested in the URL

        Returns
        ---------
        :class:`QueryLayer.Query`
            contains standard details for each request
        """
        pass

    @gen.coroutine
    def get(self, *args):
        """ Asynchronously uses :data:`_ex` to call :meth:`handle`

        The query is returned from :meth:`parse` and passed \
asynchronously to :meth:`handle`.

        Arguments
        ----------
        args: list
            args[0] (str) method requested in the URL

        """
        try:
            query = self.parse(*args)
            if isinstance(query, str):
                yield self._ex.submit(self.handle_static, query)
            else:
                yield self._ex.submit(self.handle, query)
        except URLError, u_error:
            # Get error information
            msg, status = u_error.args[0]
            self.set_status(int(status))
            self.set_header('Content-Type', 'text/plain')
            # Log and write the error message
            log.warning(msg)
            self.write(msg)

    def handle_static(self, filepath):
        """ Serves a path in the `./bfly/static` directory

        Arguments
        ----------
        path: str
            the actual path to a file on the server
        """
        extension = os.path.splitext(filepath)[1]
        # Get the mimetype from the requested extension
        mime_type = types_map.get(extension, self._basic_mime)
        self.set_header("Content-Type", mime_type)

        data = resource_string(self._root, filepath)
        self.write(data)


    def handle(self, _query):
        """ Sends response of :data:`_core` to ``_query``

        Calls :meth:`Core.get_data` or :meth:`Core.get_info` \
based on the type of the query from :meth:`Query.is_data`

        Arguments
        ----------
        _query: :class:`Query`
            The details formatted by :meth:`parse`
        """

        self.set_header('Content-Type',_query.mime_type)
        if _query.is_data:
            # get an image formatted as a string
            content = self._core.get_data(_query)
        elif _query.is_group:
            # get a list of groups formatted as a string
            content = self._core.get_groups(_query)
        elif _query.is_dataset:
            # Get all the info for the dataset
            content = self._core.get_dataset(_query)
        else:
            # get a list or dict of information as a string
            content = self._core.get_info(_query)
        # Return content
        self.write(content)
