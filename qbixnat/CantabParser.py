# -*- coding: utf-8 -*-
"""
Utility script: CantabParser
Reads an excel or csv file with CANTAB data and extracts per subject
run from console/terminal with (example):
>python CantabParser.py --filedir "data" --output "output.xlsx" --sheet "Sheetname_to_extract"

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

class CantabParser:

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
            ids = self.data['Participant ID'].unique()
            for sid in ids:
                self.subjects[sid] = self.data[self.data['Participant ID'] == sid]
                print('Subject:', sid, 'with datasets=', len(self.subjects[sid]))
            print('Subjects loaded=', len(self.subjects))


########################################################################

if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog='Parse Excel Files',
                                     description='''\
            Reads a directory and extracts sheet into an output file

             ''')
    parser.add_argument('--filedir', action='store', help='Directory containing files', default="..\\sampledata\\cantab")
    parser.add_argument('--output', action='store', help='Output file name with full path', default="..\\output.xlsx")
    parser.add_argument('--sheet', action='store', help='Sheet name to extract',
                        default="RowBySession_HealthyBrains")
    args = parser.parse_args()

    inputdir = args.filedir
    outputfile = args.output
    sheet = args.sheet
    print("Input:", inputdir)
    if access(inputdir, R_OK):
        seriespattern = '*.xls*'
        #writer = pandas.ExcelWriter(outputfile, engine='xlsxwriter')
        try:
            files = glob.glob(join(inputdir, seriespattern))
            print("Files:", len(files))
            for f2 in files:
                print("Loading",f2)
                cantab = CantabParser(f2,sheet)
                cantab.sortSubjects()
                print('Subject summary')
                for sd in cantab.subjects:
                    print('ID:', sd)
                    for i, row in cantab.subjects[sd].iterrows():
                        print(i, 'Visit:', row['Visit Identifier'], 'MOTML', row['MOTML'],'MOTSDL',row['MOTSDL'] )


        except ValueError as e:
            print("Sheet not found: ", e)

        except:
            raise OSError
        #print("Files extracted to: ", outputfile)
        #writer.save()
        #writer.close()
    else:
        print("Cannot access directory: ", inputdir)
