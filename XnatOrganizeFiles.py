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
from dicom.filereader import InvalidDicomError, read_file


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
    parser.add_argument('inputdir', action='store', help='Top level file directory eg SUBJECTID')
    parser.add_argument('--scandir', action='store', help='Copy scans to this directory for upload to XNAT')

    args = parser.parse_args()
    series ={}
    #pattern = '^([0-9A-Z_\.]+)(\d{4})\..*'
    #p = re.compile(pattern)
    #Read files from input directory
    inputdir = args.inputdir
    if not access(inputdir, R_OK):
        raise OSError("Cannot access input directory")

    #Create output directory if not already existing
    if args.scandir is not None:
        datapath = args.scandir
    else:
        dirpath = path.dirname(inputdir)
        datapath = join(dirpath, 'sortedscans')
    origdatapath = datapath
    #Check only subject dirs processed
    pattern = re.compile('^\d{4}[A-Za-z0-9]+$')

    #Create MRI sessions for each subject directory
    for subject in listdir(inputdir):
        print "Subject: ", subject
        if not pattern.match(subject):
            print "Not a subject - next"
            continue
        try:
            mkdir(join(datapath, subject))
            mkdir(join(datapath,subject,'scans'))
            datapath = join(datapath,subject,'scans')
        except OSError:
            print 'Directory exists: ', join(datapath, subject)
            datapath = origdatapath
            continue
        for group in listdir(join(inputdir,subject)):
            grouppath = join(inputdir,subject,group)
            if not isdir(grouppath) or group == 'scans':
                continue
            # get list of series
            for filename in listdir(grouppath):
                try:
                    dcm = dicom.read_file(join(grouppath,filename))
                except InvalidDicomError:
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
                    files = glob.glob(join(grouppath, seriespattern))
                    for f2 in files:
                        shutil.copy(f2, dpath[0])
                except:
                    print "Error copying files"
                    raise OSError

            series={}

        print "Files sorted to dir: ", datapath
        datapath = origdatapath






