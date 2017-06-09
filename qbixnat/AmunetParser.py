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
