from RequestHandler import RequestHandler
from QueryLayer import InfoQuery
from QueryLayer import DataQuery
from urllib2 import URLError
import numpy as np

class NDStore(RequestHandler):
    """ Responds to :data:`bfly.Webserver._webapp` /nd endpoint

    Attributes
    -----------
    inherits: :class:`RequestHandler`


    :h:`Methods`

    """
    SD = [
        'token',
        'action'
    ]

    SLICE_XY = [
        'token',
        'channel',
        'plane',
        'resolution',
        'xmin,xmax',
        'ymin,ymax',
        'zslice',
        'tslice',
    ]

    def parse(self, request):
        """ Extract details from any of the methods
        Overrides :meth:`Database.parse`

        Arguments
        ----------
        request: str
            The full request

        Returns
        ---------
        :class:`QueryLayer.Query`
            contains standard details for each request
        """
        TARGETS = ['sd']

        super(NDStore, self).parse(request)
        # Store the request
        args = request.split('/')
        target = args.pop(0)
        # Get the method
        target = self._match_list('target', target, TARGETS)

        # XY Slice API supported
        # http://docs.neurodata.io/ndstore/api/slice_api.html
        if target == 'sd':
            # Interpret first arguments
            info_keys = dict(zip(self.SD, args)) 
            # Handle the info action
            if info_keys['action'] == 'info':
                return self.get_info(info_keys)

            # Handle keywords for SD XY target
            keywords = dict(zip(self.SLICE_XY, args))
            return self.get_data(keywords)

        return 'Unsupported Request Category'

    #####
    #Lists values from config for group methods
    #####

    def get_name(self, g):
        """ get the name of a group

        Arguments
        ----------
        g: dict
            The group from :data:`BFLY_CONFIG`

        Returns
        --------
        str
            the name of `g`
        """
        return g.get(self.INPUT.GROUP.NAME,'')

    def _find_all_groups(self):
        """ Pairs all groups needed for the ``_method``

        Returns
        --------
        list
            list of pairs of group query terms and values
        """
        group_methods = self.INPUT.METHODS.GROUP_LIST
        group_queries = self.INPUT.GROUP.LIST

        return zip(group_methods, group_queries)

    def _get_group_dict(self, _keywords, _channel=False):
        """ get the config dictionary for the requested method

        Arguments
        ----------
        _keywords: dict
            All URL parameters
        _channel: bool
            Get Specific Channel information if true

        Returns
        --------
        dict
            The requested sub-dictionary from :data:`BFLY_CONFIG`
        """
        configured = self.BFLY_CONFIG
        group_keys = list(self.INPUT.METHODS.GROUP_LIST)

        # Get all the input token groups
        tokens = _keywords.get('token','').split(',')
        tokens.append(_keywords.get('channel',''))

        # Ignore channel information
        if not _channel:
            group_keys.pop(-1)

        # Make dictionary of all input token groups
        token_groups = dict(zip(group_keys, tokens))
  
        # validate each group in token
        for g_key in group_keys:
            # Get all valid group names
            valid_groups = configured.get(g_key, [])
            valid_names = map(self.get_name, valid_groups)
            # Check group against all valid group names
            group_name = token_groups.get(g_key, '')
            self._match_list(g_key, group_name, valid_names)
            # Check next group name in the token
            group_index = valid_names.index(group_name)   
            configured = valid_groups[group_index]

        # Return info for full token
        return configured

    #####
    #Loads info from tiles for image methods
    #####
    def get_info(self, _keywords):
        """ Loads :class:`InfoQuery` for ``INPUT.METHODS.META``

        Returns
        --------
        :class:`InfoQuery`
            made with info from :meth:`_get_group_dict`
        """
        # Parse all the group terms
        meta_dict = self._get_group_dict(_keywords)

        # Get keys for interface
        channels_key = self.OUTPUT.INFO.CHANNELS.NAME
        dataset_key = self.OUTPUT.INFO.DATASET.NAME
        format_key = self.INPUT.INFO.FORMAT.NAME
        method_key = self.INPUT.METHODS.NAME

        print 'a', meta_dict
        return InfoQuery(**{
            dataset_key: self.get_name(meta_dict),
            channels_key: meta_dict.get(channels_key, []),
            method_key: 'project_info',
            format_key: 'json',
        })

    #####
    #Loads data from tiles for image methods
    #####

    def get_data(self, _keywords):
        """ Make :class:`DataQuery` for an image at request path

        Arguments
        ----------
        _keywords: dict
            All URL parameters

        Returns
        --------
        :class:`DataQuery`
            Created with the :meth:`sub_data` for the full request
        """
        # Get the input terms
        xmin, xmax = self._get_ints(_keywords, 'xmin,xmax', '0,512') 
        ymin, ymax = self._get_ints(_keywords, 'ymin,ymax', '0,512') 
        resolution = self._get_int(_keywords, 'resolution', '0')
        zslice = self._get_int(_keywords, 'zslice', '0') 
        # Compute standard bounds
        bounds = [
            zslice,
            ymin,
            xmin,
            1,
            ymax - ymin,
            xmax - xmin,
        ]
 
        # Create the data query for the full bounds
        return self.sub_data(_keywords, bounds, resolution)

    def sub_data(self, _keywords, bounds, resolution):
        """ Make :class:`DataQuery` for any subregion or request

        Arguments
        ----------
        _keywords: dict
            All URL parameters
        bounds: numpy.ndarray
            The 6x1 array of z,y,x,depth,width,height values for \
the bounds requested for a data query
        resolution: int
            the number of halvings along the X and Y axes

        Returns
        --------
        :class:`DataQuery`
        """
        # Parse all the group terms
        meta_dict = self._get_group_dict(_keywords, _channel=True)

        # Get keys for interface
        resolution_key = self.INPUT.RESOLUTION.XY.NAME
        format_key = self.INPUT.IMAGE.FORMAT.NAME
        view_key = self.INPUT.IMAGE.VIEW.NAME
        path_key = self.OUTPUT.INFO.PATH.NAME
        method_key = self.INPUT.METHODS.NAME

        # Begin building needed keywords
        terms = {
            path_key: meta_dict[path_key],
            resolution_key: resolution,
            view_key: 'grayscale',
            method_key: 'data',
            format_key: 'tif',
        }

        # get integers from bounds
        for order in range(6):
            key = self.INPUT.POSITION.LIST[order]
            terms[key] = bounds[order]

        return DataQuery(**terms)

    ####
    # Handles Logs and Exceptions
    ####

    def _try_int(self, name, result):
        """ Try to convert a query result to an integer

        Arguments
        -----------
        name: str
            The name of the ``result`` property
        result: anything
            The value to try to convert to ``int``

        Returns
        ---------
        numpy.uint32
            If the ``result`` can convert to an integer
        """
        try:
            return int(result)
        except (TypeError, ValueError):
            msg = "The {0} {1} is not an integer."
            msg = msg.format(name, result)
            raise URLError([msg, 400])

    def _match_list(self, name, result, whitelist):
        """ Check if the query result is in a whitelist

        Arguments
        -----------
        name: str
            The name of the ``result`` property
        result: anything
            The value to check for in the ``whitelist``
        whitelist: list
            The list of all accepted ``result``

        Returns
        ---------
        anything
            If the ``result`` is in the ``whitelist``
        """
        # Check if the result is in the list
        if result in whitelist:
            return result

        # Create the error message
        msg = "The {0} {1} is not in {2}."
        msg = msg.format(name, result, whitelist)
        raise URLError([msg, 400])

    def _get_list(self, keywords, name, whitelist, value=''):
        """ Call :meth:`_match_list` on the keywords

        Arguments
        ----------
        keywords: dict
            All URL parameters
        name: str
            the name of the property
        whitelist: list
            the valid property values
        value: anything
            the default property value

        Returns
        ---------
        anything
            If the ``result`` is in the ``whitelist``
        """
        result = keywords.get(name, value)
        return self._match_list(name, result, whitelist)

    def _get_int(self, keywords, name, value=''):
        """ Call :meth:`_try_int` on the keywords

        Arguments
        ----------
        keywords: dict
            All URL parameters
        name: str
            the name of the property
        value: anything
            the default property value

        Returns
        ---------
        int
            If the ``result`` can be converted to an integer
        """
        result = keywords.get(name, value)
        return self._try_int(name, result)

    def _get_ints(self, keywords, name, value=''):
        """ Call :meth:`_try_ints` on the keywords

        Arguments
        ----------
        keywords: dict
            All URL parameters
        name: str
            the name of the property
        value: anything
            the default property value

        Returns
        ---------
        [int]
            If the ``result`` can be converted to an integer list
        """
        result = keywords.get(name, value)
        def try_int(i):
            return self._try_int(name, i)
        # Try int on all results
        return map(try_int, result.split(','))
