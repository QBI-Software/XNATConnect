# -*- coding: utf-8 -*-
"""
Utility script: AcerParser
Reads an excel or csv file with data and extracts per subject
run from console/terminal with (example):
>python AcerParser.py --filedir "data" --sheet "Sheetname_to_extract"

Created on Thu Mar 2 2017

@author: Liz Cooper-Williams, QBI
"""

import argparse
import glob
import re
import shutil
from datetime import datetime
from os import listdir, R_OK, path, mkdir, access
from os.path import isdir, join, basename, splitext


import pandas

class AcerParser:

    def __init__(self, datafile, sheet=1):
        self.datafile = datafile #full pathname to data file
        if (len(datafile)> 0):
            (bname, extn)= splitext(basename(datafile))
        self.type = extn #extension - xlsx or csv
        self.sheet = sheet
        self.loadData()

    def loadData(self):
        if self.type =='.xlsx':
            self.data = pandas.read_excel(self.datafile, self.sheet)
        elif self.type == '.csv':
            self.data = pandas.read_csv(self.datafile)
        else:
            self.data = None
        if self.data is not None:
            print('Data loaded')
        else:
            print('No data to load')

    def sortSubjects(self):
        '''Sort data into subjects by participant ID'''
        self.subjects = dict()
        if self.data is not None:
            ids = self.data['ID'].unique()
            for sid in ids:
                self.subjects[sid] = self.data[self.data['ID'] == sid]
                print('Subject:', sid, 'with datasets=', len(self.subjects[sid]))
            print('Subjects loaded=', len(self.subjects))

    def getXsd(self):
        return 'opex:acer'

    def mapData(self, row, i):
        """
        Maps required fields from input rows
        :param row:
        :return:
        """
        interval = 0 #NB There is no visit identifier
        xsd = self.getXsd()
        data = {
            xsd + '/interval': str(interval),
            xsd + '/attention': str(row['Attention and Orientation']),
            xsd + '/memory': str(row['Memory']),
            xsd + '/fluency': str(row['Fluency']),
            xsd + '/language': str(row['Language']),
            xsd + '/visuospatial': str(row['Visuospatial']),
            xsd + '/MMSE': str(row['MMSE Total']),
            xsd + '/total': str(row['ACE-R Total'])

        }
        return data


    def getSubjectData(self,sd):
        """
        Extract subject data from input data
        :param sd:
        :return:
        """
        skwargs = {}
        if self.subjects is not None:
            dob = self.formatDobNumber(self.subjects[sd]['DOB'].iloc[0])
            gender = str(self.subjects[sd]['Sex'].iloc[0]).lower()
            skwargs = {'dob': dob}
            if gender in ['F', 'M']:
                skwargs['gender'] = gender

        return skwargs

    def getSampleid(self,sd, row):
        """
        Generate a unique id for Amunet sample
        :param row:
        :return:
        """

        id = "AC_" + sd + "_1"
        return id

    def formatDobNumber(self,orig):
        """
        Reformats DOB string from Amunet data float to yyyy-mm-dd
        """
        dateoffset = 693594
        dt = datetime.fromordinal(dateoffset + int(orig))
        return dt.strftime("%Y-%m-%d")

########################################################################

if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog='ACE-R Files',
                                     description='''\
            Reads files in a directory and extracts data ready to load to XNAT database

             ''')
    parser.add_argument('--filedir', action='store', help='Directory containing files', default="..\\sampledata\\acer")
    parser.add_argument('--sheet', action='store', help='Sheet name to extract', default="1")
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
                cantab = AcerParser(f2,sheet)
                cantab.sortSubjects()
                print('Subject summary')
                for sd in cantab.subjects:
                    print('ID:', sd)
                    dob = cantab.subjects[sd]['DOB'][0]
                    for i, row in cantab.subjects[sd].iterrows():
                        print(i, 'ACE-R Total', row['ACE-R Total'] )


        except ValueError as e:
            print("Sheet not found: ", e)

        except:
            raise OSError

    else:
        print("Cannot access directory: ", inputdir)
