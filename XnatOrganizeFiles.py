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
import dicom


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
    pattern = '^([0-9A-Z_\.]+)(\d{4})\..*'
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
    else:
        datapath = join(datapath,path.basename(scandir), 'scans')

    if access(scandir, R_OK):

        for subdr in listdir(scandir):
            if subdr == 'scans':
                continue
            # get list of series
            for filename in listdir(join(scandir,subdr)):
                dcm = dicom.read_file(join(scandir,subdr,filename))
                if not dcm:
                    print "Not DICOM - skipping: ", filename
                    continue
                series_num = str(dcm.SeriesNumber)
                if series_num not in series:
                    parts = filename.split(".")
                    idx = parts.index(series_num.zfill(4))
                    series_prefix = '.'.join(parts[0:idx + 1])
                    series[series_num] = [join(datapath,str(int(series_num))), series_prefix]
            # Move files to new dirs grouped by series
            for snum, dpath in series.items():
                seriespattern = dpath[1] + '.*'
                try:
                    mkdir(dpath[0])
                    files = glob.glob(join(scandir,subdr, seriespattern))
                    for f2 in files:
                        shutil.copy(f2, dpath[0])
                except:
                    print "Error copying files"
                    raise OSError

            series={}
        print "Files sorted to dir: ", datapath
    else:
        print "Cannot access directory: ", scandir





