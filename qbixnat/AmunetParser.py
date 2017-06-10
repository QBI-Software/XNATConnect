# -*- coding: utf-8 -*-
"""
Utility script: AmunetParser
Reads an excel or csv file with CANTAB data and extracts per subject
run from console/terminal with (example):
>python AmunetParser.py --filedir "data" --output "output.xlsx" --sheet "Sheetname_to_extract"

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

class AmunetParser:

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
            ids = self.data['S_Full name'].unique()
            for sid in ids:
                self.subjects[sid.upper()] = self.data[self.data['S_Full name'] == sid]
                print('Subject:', sid, 'with datasets=', len(self.subjects[sid]))
            print('Subjects loaded=', len(self.subjects))

    def getXsd(self):
        return 'opex:amunet'

    def mapAEVdata(self, row):
        """
        Maps required fields from input rows
        :param row:
        :return:
        """
        visit = re.search('Visit\s(\d{1,2})', str(row['S_Visit']))
        interval = int(visit.group(1)) - 1
        xsd = self.getXsd()
        data = {
            xsd + '/interval': str(interval),
            xsd + '/AEVcomments': str(row['AEV_Lexical rating']),
            xsd + '/AEV': str(row['AEV_Average total error']),
            xsd + '/EV': str(row['EV_Average total error']),
            xsd + '/AV': str(row['AV_Average total error']),
            xsd + '/DV': str(row['DV_Average total error'])

        }
        return data

    def mapSCSdata(self,row):
        """
        Maps required fields from input row
        :param self:
        :param row:
        :return:
        """
        visit = re.search('Visit\s(\d{1,2})', str(row['S_Visit']))
        interval = int(visit.group(1)) - 1
        xsd = self.getXsd()
        data = {
            xsd + '/interval': str(interval),
            xsd + '/SCScomments': str(row['SCS_Lexical rating']),
            xsd + '/SCS': str(row['SCS_Average total error']),
            xsd + '/SCD': str(row['SCD_Average total error']),
            xsd + '/SAS': str(row['SAS_Average total error']),
            xsd + '/SAD': str(row['SAD_Average total error']),
            xsd + '/SES': str(row['SES_Average total error']),
            xsd + '/SED': str(row['SED_Average total error'])
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

########################################################################

if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog='Parse Excel Files',
                                     description='''\
            Reads a directory and extracts data ready to load to XNAT database

             ''')
    parser.add_argument('--filedir', action='store', help='Directory containing files', default="..\\sampledata\\cantab")
    parser.add_argument('--report', action='store', help='Report to text file', default="..\\report.txt")
    parser.add_argument('--sheet', action='store', help='Sheet name to extract', default="1")
    args = parser.parse_args()

    inputdir = args.filedir
    outputfile = args.report
    sheet = args.sheet
    print("Input:", inputdir)
    if access(inputdir, R_OK):
        seriespattern = '*.*'
        #writer = pandas.ExcelWriter(outputfile, engine='xlsxwriter')
        try:
            files = glob.glob(join(inputdir, seriespattern))
            print("Files:", len(files))
            for f2 in files:
                print("Loading",f2)
                cantab = AmunetParser(f2,sheet)
                cantab.sortSubjects()
                print('Subject summary')
                for sd in cantab.subjects:
                    print('ID:', sd)
                    dob = cantab.subjects[sd]['S_Date of birth'][0]
                    for i, row in cantab.subjects[sd].iterrows():
                        print(i, 'Visit:', row['S_Visit'], 'AEV_Average total error', row['AEV_Average total error'] )


        except ValueError as e:
            print("Sheet not found: ", e)

        except:
            raise OSError
        #print("Files extracted to: ", outputfile)
        #writer.save()
        #writer.close()
    else:
        print("Cannot access directory: ", inputdir)
