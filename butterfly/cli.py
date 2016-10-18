import logging
import re
import os
import cv2
import argparse


def main():
    '''
    Butterfly
    EM Data server
    Eagon Meng and Daniel Haehn
    Lichtman Lab, 2015
    '''

    help = {
        'bfly': 'Host a butterfly server!',
        'home': '/parent/path/of/all/sources',
        'port': 'port >1024 for hosting this server'
    }
    user = os.path.expanduser('~')

    parser = argparse.ArgumentParser(description=help['bfly'])
    parser.add_argument('port', type=int, default = 2001, nargs='?', help=help['port'])
    parser.add_argument('-f','--folder', metavar='home', default= user, help= help['home'])
    [home,port] = [parser.parse_args().folder, parser.parse_args().port]
    base = os.path.join(home,'rh_config.yaml')

    if os.path.isfile(base):
        os.environ['RH_CONFIG_FILENAME'] = base
    from rh_logger import logger
    from butterfly import settings,core,webserver

    logger.start_process("bfly", "Starting butterfly server on port {}".format(port), [port])
    logger.report_event("Datasources: " + ", ".join(settings.DATASOURCES),log_level=logging.DEBUG)
    logger.report_event("Allowed paths: " + ", ".join(settings.ALLOWED_PATHS),log_level=logging.DEBUG)
    c = core.Core()

    if home is not user and not os.environ.get('RH_CONFIG_FILENAME'):
        visible = [os.path.join(home,f) for f in os.listdir(home) if not f.startswith('.')]
        folds = [v for v in visible if os.path.isdir(v) or v.endswith('.json')]
        sample = {'name':os.path.basename(home),'datasets':[]}
        for fold in folds:
            try:
                c.create_datasource(fold)
                source = c.get_datasource(fold)
                dataset = source.get_dataset(fold)
                sample['datasets'].append(dataset)
            except:
                logger.report_event('No datasource at '+ fold,log_level=logging.WARN)
                continue
        settings.bfly_config['experiments'] = [{'name':'BFLY','samples':[sample]}]

    ws = webserver.WebServer(c, port)
    ws.start()


# Custom parsing of the args file


def convert_arg_line_to_args(arg_line):
    for arg in re.split(''' (?=(?:[^'"]|'[^']*'|"[^"]*")*$)''', arg_line):
        if not arg.strip():
            continue
        yield arg.strip('\'\"')


def parseNumRange(num_arg):
    match = re.match(r'(\d+)(?:-(\d+))?$', num_arg)
    if not match:
        raise argparse.ArgumentTypeError(
            "'" + num_arg + "' must be a number or range (ex. '5' or '0-10').")
    start = match.group(1)
    end = match.group(2) or match.group(1)
    step = 1
    if end < start:
        step = -1
    return list(range(int(start), int(end) + step, step))


def query():
    from butterfly import core
    from rh_logger import logger, ExitCode
    logger.start_process("bquery", "Starting butterfly query")
    c = core.Core()

    # Parser for command-line arguments - to be incorporated separately in a
    # client-side tool
    parser = argparse.ArgumentParser(
        description='Returns cutout of requested volume from a given EM stack',
        fromfile_prefix_chars='@',
        add_help=False)
    parser.convert_arg_line_to_args = convert_arg_line_to_args

    # Argument group for input/output paths
    paths = parser.add_argument_group('Paths')
    paths.add_argument('-h', '--help', action='help', help=argparse.SUPPRESS)
    paths.add_argument('datapath', help='Path to EM stack')
    paths.add_argument(
        '--output',
        metavar='filename',
        help='Output file name (with extension), '
             'use sprintf format for multiple slices',
        required=True)

    # Argument group for information about requested volume
    v_inf = parser.add_argument_group('Requested volume')
    v_inf.add_argument(
        '--start',
        nargs=3,
        type=int,
        metavar=(
            'X',
            'Y',
            'Z'),
        help='Starting coordinates of the requested volume',
        required=True)
    v_inf.add_argument(
        '--size',
        nargs=3,
        type=int,
        metavar=(
            'X',
            'Y',
            'Z'),
        help='Size of the requested volume',
        required=True)
    v_inf.add_argument(
        '--zoom',
        nargs='?',
        type=int,
        default=0,
        metavar='level',
        help='MIP map level, 0 is default')

    # Hidden argument group for parameters - temporary for now! Will not be on
    # client, and will be optional on server
    d_inf = parser.add_argument_group()
    # EM stack filenames in sprintf format
    d_inf.add_argument('--filename', help=argparse.SUPPRESS, required=True)
    # Folder names for each vertical slice in sprintf format
    d_inf.add_argument('--folderpaths', help=argparse.SUPPRESS, required=True)
    d_inf.add_argument(
        '--x_ind',
        nargs='+',
        type=parseNumRange,
        help=argparse.SUPPRESS,
        required=True)  # Row indices of the filenames
    d_inf.add_argument(
        '--y_ind',
        nargs='+',
        type=parseNumRange,
        help=argparse.SUPPRESS,
        required=True)  # Column indices of the filenames
    d_inf.add_argument(
        '--z_ind',
        nargs='+',
        type=parseNumRange,
        help=argparse.SUPPRESS,
        required=True)  # Slice indices of the filenames
    d_inf.add_argument(
        '--blocksize',
        nargs=2,
        type=int,
        help=argparse.SUPPRESS,
        required=True)  # Tile size of each image (X, Y)

    args = parser.parse_args()
    # Paths and filenames for the current image set
    datapath = args.datapath
    # datapath = '/Volumes/DATA1/P3/'
    # datapath = '/home/e/Documents/Data/P3/'

    filename = args.filename
    folderpaths = args.folderpaths

    # Tile and slice index ranges - the list comprehensions can be understood
    # as nested for loops to flatten list
    z_ind = [number for sublist in args.z_ind for number in sublist]
    y_ind = [number for sublist in args.y_ind for number in sublist]
    x_ind = [number for sublist in args.x_ind for number in sublist]
    indices = (x_ind, y_ind, z_ind)

    # Requested volume (coordinates are for the entire current image set)
    start_coord = args.start
    vol_size = args.size
    zoom_level = args.zoom

    # In the case of regular image stacks we manually input paths
    c.create_datasource(datapath)
    ris = c._datasources[datapath]
    ris.load_paths(folderpaths, filename, indices)

    # Temporary input of blocksize, should be able to grab from index in the
    # future
    ris.blocksize = args.blocksize

    # Grab the sample volume
    volume = c.get(datapath, start_coord, vol_size, zoom_level)

    if vol_size[2] == 1:
        # Is there a better way to catch errors?
        try:
            cv2.imwrite(args.output, volume[:, :, 0].astype('uint8'))
        except cv2.error:
            logger.report_exception()
            logger.end_process('Could not write image',
                               ExitCode.io_error)
            exit(-1)
    else:
        for i in range(vol_size[2]):
            try:
                cv2.imwrite(args.output % i, volume[:, :, i].astype('uint8'))
            except cv2.error:
                logger.report_exception()
                logger.end_process('Could not write image',
                                   ExitCode.io_error)
                exit(-1)

    logger.end_process("Wrote cutout with volume = %s" % str(volume.shape),
                       ExitCode.success)
