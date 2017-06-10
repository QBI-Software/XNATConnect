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
from datetime import datetime
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
                self.subjects[sid.upper()] = self.data[self.data['Participant ID'] == sid]
                print('Subject:', sid, 'with datasets=', len(self.subjects[sid]))
            print('Subjects loaded=', len(self.subjects))

    def formatDateString(self,orig):
        '''Reformats datetime string from yyyy.mm.dd hh:mm:ss to yyyy-mm-dd'''
        dt = datetime.strptime(orig, "%Y.%m.%d %H:%M:%S")
        return dt.strftime("%Y-%m-%d")

    def getStringDateUTC(self, orig):
        '''Returns datetime string as a unique id'''
        dt = datetime.strptime(orig, "%Y.%m.%d %H:%M:%S UTC")
        return dt.strftime("%Y%m%d%H%M%S")

    def genders(self):
        return {0: 'male', 1: 'female'}

    def formatDob(self,orig):
        """
        Reformats DOB string from yyyy-mm-dd 00:00:00 as returned by series obj to yyyy-mm-dd
        """
        # dt = datetime.strptime(orig,"%d-%b-%y") #if was 20-Oct-50
        # dt = datetime.strptime(orig, "%d/%m/%Y")
        dt = datetime.strptime(orig, "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%Y-%m-%d")

    def getInterval(self,orig):
        """Parses string M-00 to 0 or M-01 to 1 etc"""
        interval = int(orig[2:])
        return interval

    def getSampleid(self, sd, row):
        """
        Generate Unique sample ID - append prefix for subtypes
        :param sd: Subject ID
        :param row: row data with unique number
        :return: id
        """
        cantabid = sd + '_' + self.getStringDateUTC(row['Visit Start (GMT)'])
        return cantabid

    def getMOTxsd(self):
        return 'opex:cantabMOT'

    def mapMOTdata(self,row,i):
        """
        Map MOT data to row input data
        :param row: pandas series row data
        :return: data kwargs structure to load to xnat expt
        """
        motxsd = self.getMOTxsd()
        visit_date = self.formatDateString(row['Visit Start (Local)'])
        interval = self.getInterval(row['Visit Identifier'])
        comments = str(row['MOT Voice Comment'])
        motdata = {
            motxsd + '/interval': str(interval),
            motxsd + '/date': row['Visit Start (Local)'],
            motxsd + '/date_analysed': visit_date,
            motxsd + '/sample_id': str(i),  # row number in this data file for reference
            motxsd + '/sample_num': '0',  # ie repeat runs - may need to fix later
            motxsd + '/sample_quality': 'Unknown',  # default - check later if an error
            motxsd + '/status': str(row['MOT Voice Status']),
            motxsd + '/comments': comments,
            motxsd + '/MOTML': str(row['MOTML']),
            motxsd + '/MOTSDL': str(row['MOTSDL'])}
        return motdata

    def getPALxsd(self):
        return 'opex:cantabPAL'

    def mapPALdata(self, row, i):
        """
        Map PAL data to row input data
        :param row: pandas series row data
        :return: data kwargs structure to load to xnat expt
        """
        xsd = self.getPALxsd()
        visit_date = self.formatDateString(row['Visit Start (Local)'])
        interval = self.getInterval(row['Visit Identifier'])
        comments = str(row['PAL Recommended Standard Comment'])
        motdata = {
            xsd + '/interval': str(interval),
            xsd + '/date': row['Visit Start (Local)'],  # PARSED in experiment load
            xsd + '/date_analysed': visit_date,
            xsd + '/sample_id': str(i),  # row number in this data file for reference
            xsd + '/sample_num': '0',  # ie repeat runs - may need to fix later
            xsd + '/sample_quality': 'Unknown',  # default - check later if an error
            xsd + '/status': str(row['PAL Recommended Standard Status']),
            xsd + '/comments': comments,
            xsd + '/PALFAMS': str(row['PALFAMS']),
            xsd + '/PALMETS': str(row['PALMETS']),
            xsd + '/PALTA': str(row['PALTA']),
            xsd + '/PALTE': str(row['PALTE']),
            xsd + '/PALTEA': str(row['PALTEA']),
            xsd + '/PALTEA6': str(row['PALTEA6']),
            xsd + '/PALTEA8': str(row['PALTEA8'])
        }
        return motdata

    def getDMSxsd(self):
        return 'opex:cantabDMS'

    def mapDMSdata(self, row,i):
        """
        Map DMS data to row input data
        :param row: pandas series row data
        :return: data kwargs structure to load to xnat expt
        """
        xsd = self.getDMSxsd()
        visit_date = self.formatDateString(row['Visit Start (Local)'])
        interval = self.getInterval(row['Visit Identifier'])
        comments = str(row['DMS Recommended Standard Comment'])
        motdata = {
            xsd + '/interval': str(interval),
            xsd + '/date': row['Visit Start (Local)'],  # PARSED in experiment load
            xsd + '/date_analysed': visit_date,
            xsd + '/sample_id': str(i),  # row number in this data file for reference
            xsd + '/sample_num': '0',  # ie repeat runs - may need to fix later
            xsd + '/sample_quality': 'Unknown',  # default - check later if an error
            xsd + '/status': str(row['DMS Recommended Standard Status']),
            xsd + '/comments': comments,
            xsd + '/DMSCC': str(row['DMSCC']),
            xsd + '/DMSML': str(row['DMSML']),
            xsd + '/DMSML0': str(row['DMSML0']),
            xsd + '/DMSML12': str(row['DMSML12']),
            xsd + '/DMSMLAD': str(row['DMSMLAD']),
            xsd + '/DMSPC': str(row['DMSPC']),
            xsd + '/DMSPC0': str(row['DMSPC0']),
            xsd + '/DMSPC12': str(row['DMSPC12']),
            xsd + '/DMSPCAD': str(row['DMSPCAD']),
            xsd + '/DMSTC0': str(row['DMSTC0']),
            xsd + '/DMSTC12': str(row['DMSTC12']),
            xsd + '/DMSTCAD': str(row['DMSTCAD']),
            xsd + '/DMSTCS': str(row['DMSTCS']),
            xsd + '/DMSTE': str(row['DMSTE']),
            xsd + '/DMSTEAD': str(row['DMSTEAD'])
        }
        return motdata

    def getSWMxsd(self):
        return 'opex:cantabSWM'

    def mapSWMdata(self, row,i):
        """
        Map SWM data to row input data
        :param row: pandas series row data
        :return: data kwargs structure to load to xnat expt
        """
        xsd = self.getSWMxsd()
        visit_date = self.formatDateString(row['Visit Start (Local)'])
        interval = self.getInterval(row['Visit Identifier'])
        comments = str(row['SWM Recommended standard Comment'])
        motdata = {
            xsd + '/interval': str(interval),
            xsd + '/date': row['Visit Start (Local)'],  # PARSED in experiment load
            xsd + '/date_analysed': visit_date,
            xsd + '/sample_id': str(i),  # row number in this data file for reference
            xsd + '/sample_num': '0',  # ie repeat runs - may need to fix later
            xsd + '/sample_quality': 'Unknown',  # default - check later if an error
            xsd + '/status': str(row['SWM Recommended Standard Status']),
            xsd + '/comments': comments,
            xsd + '/SWMBE': str(row['SWMBE']),
            xsd + '/SWMBE6': str(row['SWMBE6']),
            xsd + '/SWMBE8': str(row['SWMBE8']),
            xsd + '/SWMDE8': str(row['SWMDE8']),
            xsd + '/SWMTE': str(row['SWMTE']),
            xsd + '/SWMTE6': str(row['SWMTE6']),
            xsd + '/SWMTE8': str(row['SWMTE8']),
            xsd + '/SWMWE': str(row['SWMWE'])
        }
        return motdata

    def getSubjectData(self,sd):
        """
        Load subject data from input data
        :param sd:
        :return:
        """
        skwargs = {}
        if self.subjects is not None:
            dob = self.formatDob(str(self.subjects[sd]['Date of Birth'].iloc[0]))
            gender = self.genders()[self.subjects[sd]['Gender'].iloc[0]]
            group = str(self.subjects[sd]['Group'].iloc[0])
            skwargs = {'dob': dob, 'gender': gender, 'group': group}
        return skwargs

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
                    dob = cantab.subjects[sd]['Date of Birth'][0]
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
