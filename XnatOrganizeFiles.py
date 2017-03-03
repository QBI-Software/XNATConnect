# -*- coding: utf-8 -*-
"""
XNAT Utility script: XnatOrganizeFiles
Reads directories and creates directory structure
suitable for XNAT upload

Created on Thu Mar 2 2017

@author: Liz Cooper-Williams, QBI
"""

from os import listdir, R_OK, path, mkdir, access
from os.path import isdir, join
import argparse
import re
import glob
import shutil


if __name__ == "__main__":
    # Read dirlist until get to *.dcm or *.IMA
    parser = argparse.ArgumentParser(prog='XnatOrganizeFiles',
                                     description='''\
            Reads directories and creates directory structure suitable for XNAT upload
            - expects this input dir format: SUBJECTID/Group/*.IMA (mixed series)
            - note this will not work if directory structure is different.
            - outputs format: sortedscans/SUBJECTID/scans/series/*.IMA
            - run XnatUploadScans with "--u sortedscans"

             ''')
    parser.add_argument('filedir', action='store', help='Top level file directory eg SUBJECTID')

    args = parser.parse_args()
    series ={}
    pattern = '^([A-Z_\.]+)(\d{4})\..*'
    p = re.compile(pattern)
    scandir = args.filedir
    dirpath = path.dirname(scandir)
    datapath = join(dirpath, 'sortedscans')
    if not path.isdir(datapath):
        try:
            mkdir(datapath)
            mkdir(join(datapath, path.basename(scandir)))
            mkdir(join(datapath, path.basename(scandir), 'scans'))
            datapath = join(datapath, path.basename(scandir), 'scans')
        except:
            raise OSError

    if access(scandir, R_OK):

        for subdr in listdir(scandir):
            if subdr == 'scans':
                continue
            # get list of series
            for filename in listdir(join(scandir,subdr)):
                m = p.match(filename)
                series_prefix = m.group(1)
                series_num =str(m.group(2))
                series[series_num] = join(datapath,str(int(series_num)))
            # Move files to new dirs grouped by series
            for snum,dpath in series.items():
                seriespattern = series_prefix + snum + '.*'
                try:
                    mkdir(dpath)
                    files = glob.glob(join(scandir,subdr, seriespattern))
                    for f2 in files:
                        shutil.copy(f2, dpath)
                except:
                    raise OSError

            series={}
        print "Files sorted to dir: ", datapath
    else:
        print "Cannot access directory: ", scandir





