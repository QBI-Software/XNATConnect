# -*- coding: utf-8 -*-
"""
Utility script: AmunetParser
Reads an excel or csv file with data and extracts per subject
run from console/terminal with (example):
>python AmunetParser.py --filedir "data" --sheet "Sheetname_to_extract"

Created on Thu Mar 2 2017

@author: Liz Cooper-Williams, QBI
"""

import argparse
import fnmatch
import glob
import re
import sys
import csv
from datetime import datetime, date
from os import listdir, R_OK, access
from os.path import join, isfile

from qbixnat.DataParser import DataParser


class AmunetParser(DataParser):

    def __init__(self, *args):
        #super(AmunetParser, self).__init__(*args) - PYTHON V3
        DataParser.__init__(self, *args)
        self.dates = dict()
        self.subjects = dict()

    def sortSubjects(self):
        '''Sort data into subjects by participant ID'''
        if self.data is not None:
            ids = self.data['S_Full name'].unique()
            for sid in ids:
                self.subjects[sid] = self.data[self.data['S_Full name'] == sid]
                print('Subject:', sid, 'with datasets=', len(self.subjects[sid]))
            print('Subjects loaded=', len(self.subjects))

    def getxsd(self):
        return 'opex:amunet'

    def mapAEVdata(self, row,i):
        """
        Maps required fields from input rows
        :param row:
        :return:
        """
        visit = re.search('Visit\s(\d{1,2})', str(row['S_Visit']))
        interval = int(visit.group(1)) - 1
        xsd = self.getxsd()
        mandata = {
            xsd + '/interval': str(interval),
            xsd + '/sample_id': str(i),  # row number in this data file for reference
            xsd + '/sample_quality': 'Unknown',  # default - check later if an error
            xsd + '/data_valid': 'Initial'
        }
        data = {
            xsd + '/AEVcomments': str(row['AEV_Lexical rating']),
            xsd + '/AEV': str(row['AEV_Average total error']),
            xsd + '/EV': str(row['EV_Average total error']),
            xsd + '/AV': str(row['AV_Average total error']),
            xsd + '/DV': str(row['DV_Average total error'])

        }
        return (mandata,data)

    def mapSCSdata(self,row,i):
        """
        Maps required fields from input row
        :param self:
        :param row:
        :return:
        """
        visit = re.search('Visit\s(\d{1,2})', str(row['S_Visit']))
        interval = int(visit.group(1)) - 1
        xsd = self.getxsd()
        mandata = {
            xsd + '/interval': str(interval),
            xsd + '/sample_id': str(i),  # row number in this data file for reference
            xsd + '/sample_quality': 'Unknown',  # default - check later if an error
            xsd + '/data_valid': 'Initial'
        }
        data = {
            xsd + '/SCScomments': str(row['SCS_Lexical rating']),
            xsd + '/SCS': str(row['SCS_Average total error']),
            xsd + '/SCD': str(row['SCD_Average total error']),
            xsd + '/SAS': str(row['SAS_Average total error']),
            xsd + '/SAD': str(row['SAD_Average total error']),
            xsd + '/SES': str(row['SES_Average total error']),
            xsd + '/SED': str(row['SED_Average total error'])
        }
        return (mandata, data)

    def getSubjectData(self,sd):
        """
        Extract subject data from input data
        :param sd:
        :return:
        """
        skwargs = {}
        if self.subjects is not None:
            dob = self.formatDobNumber(self.subjects[sd]['S_Date of birth'].iloc[0])
            gender = str(self.subjects[sd]['S_Sex'].iloc[0]).lower()
            hand = str(self.subjects[sd]['S_Hand'].iloc[0])
            skwargs = {'dob': dob}
            if gender in ['female', 'male']:
                skwargs['gender'] = gender
            if hand in ['Right', 'Left', 'Ambidextrous']:
                skwargs['handedness'] = hand

        return skwargs

    def getSampleid(self,sd, row):
        """
        Generate a unique id for Amunet sample
        :param row:
        :return:
        """
        visit = re.search('Visit\s(\d{1,2})', str(row['S_Visit']))
        id = "AM_" + sd + "_" + visit.group(1)
        return id

    def formatDobNumber(self,orig):
        """
        Reformats DOB string from Amunet data float to yyyy-mm-dd
        """
        dateoffset = 693594
        dt = datetime.fromordinal(dateoffset + int(orig))
        return dt.strftime("%Y-%m-%d")

    def extractDateInfo(self, dirpath):
        seriespattern = '*.zip'
        zipfiles = [f for f in listdir(dirpath) if (isfile(join(dirpath, f)) and fnmatch.fnmatch(f, seriespattern))]
        print(zipfiles)
        rid = re.compile('^(\d{4}.{2})')
        rdate = re.compile('(\d{8})\.zip$')
        for f in zipfiles:
            fid = rid.search(f).group(0)
            fdate = rdate.search(f).groups()[0]
            #some dates are in reverse
            try:
                if (fdate[4:6]) == '20':
                    fdateobj = date(int(fdate[4:9]), int(fdate[2:4]), int(fdate[0:2]))
                else:
                    fdateobj = date(int(fdate[0:4]), int(fdate[4:6]), int(fdate[6:9]))
            except ValueError:
                print "cannot create date from: ", fdate
                continue


            if self.dates.get(fid) is not None:
                self.dates[fid].append(fdateobj)
            else:
                self.dates[fid] = [fdateobj]
        print(self.dates)
        #Output to a csvfile
        csvfile = join(dirpath,'amunet_participantdates.csv')
        writer = csv.writer(csvfile, delimiter=',')
        for d,v in self.dates:
            v.sort()
            for datevals in v:
                writer.writerow([d, datevals])



########################################################################

if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog='Parse Water Maze (Amunet) Files',
                                     description='''\
            Reads files in a directory and extracts data ready to load to XNAT database

             ''')
    parser.add_argument('--filedir', action='store', help='Directory containing files', default="..\\sampledata\\amunet")
    parser.add_argument('--sheet', action='store', help='Sheet name to extract', default="1")
    parser.add_argument('--datelist', action='store', help='Generate list of dates from dir', default="1")
    args = parser.parse_args()

    inputdir = args.filedir
    sheet = args.sheet
    print("Input:", inputdir)
    if access(inputdir, R_OK):
        seriespattern = '*.*'

        try:
            files = glob.glob(join(inputdir, seriespattern))
            print("Files:", len(files))
            for f2 in files:
                print("Loading",f2)
                cantab = AmunetParser(f2,sheet)
                if args.datelist is not None:
                    cantab.extractDateInfo(args.datelist)
                cantab.sortSubjects()
                print('Subject summary')
                for sd in cantab.subjects:
                    print('ID:', sd)
                    dob = cantab.subjects[sd]['S_Date of birth']
                    for i, row in cantab.subjects[sd].iterrows():
                        print(i, 'Visit:', row['S_Visit'], 'AEV_Average total error', row['AEV_Average total error'], 'DOB', cantab.formatDobNumber(row['S_Date of birth']) )


        except ValueError as e:
            print("Sheet not found: ", e)

        except:
            e = sys.exc_info()[0]
            print(e)

    else:
        print("Cannot access directory: ", inputdir)
