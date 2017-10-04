# -*- coding: utf-8 -*-
"""
Utility script: BloodParser
Reads an excel or csv file with data and extracts per subject
run from console/terminal with (example):
>python BloodParser.py --filedir "data" --sheet "Sheetname_to_extract"

Created on Thu Mar 2 2017

@author: Liz Cooper-Williams, QBI
"""

import argparse
import glob
from os import R_OK, access
from os.path import join
from datetime import datetime

from qbixnat.dataparser.DataParser import DataParser


class BloodParser(DataParser):

    def __init__(self, *args, **kwargs):
        DataParser.__init__(self, *args)
        self.type=''
        if 'type' in kwargs:
            self.type = kwargs.get('type')

    def sortSubjects(self):
        '''Sort data into subjects by participant ID'''
        self.subjects = dict()
        if self.data is not None:
            self.data['Participant ID'] = self.data['Participant ID'].str.replace(" ","")
            ids = self.data['Participant ID'].unique()
            for sid in ids:
                self.subjects[sid] = self.data[self.data['Participant ID'] == sid]
                print 'Subject:', sid, 'with datasets=', len(self.subjects[sid])
            print 'TOTAL Subjects loaded=', len(self.subjects)

    def getxsd(self):
        return {"COBAS":'opex:bloodCobasData',
                "MULTIPLEX": 'opex:bloodMultiplexData',
                "ELISAS": 'opex:bloodElisasData'}

    def getPrepostOptions(self,i):
        options = ['fasted', 'pre', 'post']
        return options[i]

    def parseSampleID(self,sampleid):
        """
        Splits sample id
        :param sampleid: 0-0-S-a gives interval-prepost-S-a
        :return: interval, prepost string
        """
        parts = sampleid.split("-")
        if len(parts) == 4:
            interval = int(parts[0])
            prepost = self.getPrepostOptions(int(parts[1]))
        else:
            interval = -1
            prepost = ""
        return (interval, prepost)

    def getSampleid(self, sd, row):
        """
        Generate a unique id for data sample
        :param row:
        :return:
        """
        if 'Sample ID' in row:
            parts = row['Sample ID'].split("-")
            id = "%s_%s_%d_%d" % (self.type, sd, int(parts[0]), int(parts[1]))
        else:
            id = sd
        return id

    def formatADate(self, orig):
        """
        Formats date from input as dd/mm/yyyy hh:mm
        :param orig:
        :return:
        """
        if "/" in orig:
            dt = datetime.strptime(orig, "%d/%m/%Y %H:%M:%S")
        elif "-" in orig:
            dt = datetime.strptime(orig, "%Y-%m-%d %H:%M:%S")
        else:
            dt = orig
        return dt.strftime("%Y-%m-%d")

    def mapData(self, row, i, type):
        """
        Maps required fields from input rows
        :param row:
        :return:
        """
        (interval,prepost) = self.parseSampleID(row['Sample ID'])
        xsd = self.getxsd()[type]
        mandata = {
            xsd + '/interval': str(interval),
            xsd + '/sample_id': row['Sample ID'],  # row number in this data file for reference
            xsd + '/sample_quality': 'Unknown',  # default - check later if an error
            xsd + '/data_valid': 'Initial',
            xsd + '/date' : row['A_Date'],
            xsd + '/prepost': prepost,
            xsd + '/HGH': str(row['HGH']),
            xsd + '/Prolactin': str(row['Prolactin']),
            xsd + '/Cortisol': str(row['Cortisol']),
            xsd + '/Insulin': str(row['Insulin'])
        }

        data = {}
        return (mandata,data)




########################################################################

if __name__ == "__main__":
    import sys
    parser = argparse.ArgumentParser(prog=sys.argv[0],
                                     description='''\
            Reads files in a directory and extracts data ready to load to XNAT database

             ''')

    parser.add_argument('--filedir', action='store', help='Directory containing files', default="sampledata\\blood\\COBAS")
    parser.add_argument('--sheet', action='store', help='Sheet name to extract', default="1")
    args = parser.parse_args()

    inputdir = args.filedir
    sheet = int(args.sheet)
    skip = 1
    type = "COBAS"
    print("Input:", inputdir)
    if access(inputdir, R_OK):
        seriespattern = '*.xlsx'

        try:
            files = glob.glob(join(inputdir, seriespattern))
            print("Files:", len(files))
            for f2 in files:
                print "\n****Loading",f2
                cantab = BloodParser(f2,sheet,skip, type=type)
                cantab.sortSubjects()

                for sd in cantab.subjects:
                    print 'ID:', sd
                    for i, row in cantab.subjects[sd].iterrows():
                        dob = cantab.formatADate(str(cantab.subjects[sd]['A_Date'][i]))
                        uid = cantab.getSampleid(sd,row)
                        print i, 'Visit:', uid, 'DOB', dob
                        (d1,d2) = cantab.mapData(row,i,type)
                        print d1



        except ValueError as e:
            print(e)

    else:
        print("Cannot access directory: ", inputdir)
