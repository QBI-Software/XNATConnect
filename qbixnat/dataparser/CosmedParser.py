# -*- coding: utf-8 -*-
"""
Utility script: CosmedParser
COSMED data requires further calculation and filtering before compiling for upload
1. Individual data files are stored in directory with filename as: subjectid_xMonth[A|B|C|D]_30sec_yyyymmdd.xlsx
 - ignore files 0MonthA
 - group files 0MonthB, 3MonthC, 6MonthD
 - date of expt (full date and time in spreadsheet)
2. Load Fields listed in cosmed_fields.xlsx
    - cosmed tab: read SubjectID, date and time as per row/column from "Data" tab
    - cosmed_xnat: map XnatField to Parameter
    - cosmed_fields: shows how data is collected - not read directly
    - cosmed_data: header fields for parsing data
3. Load data file with skip=0 sheetname='Data'
    - SubjectID = cell(1,1)
    - date = cell(0,4) - format d/m/yyyy
    - time = cell(1,4) - format hh:mm:ss AM/PM
    - subset with 'cosmed_data'[0] as columns -> phasedata
        + Find phase=EXERCISE - last time point - extract data fields as per cosmed_fields
        + subset EXERCISE data at 3min intervals
        + subset RECOVERY data at 1min interval
4. Load data file with skip=0 sheetname='Results'
    - extract line 5 for headers
    - read params and Max for xnat
5. Generate phase data from subsets
    - write to new tab with Results data 'ScriptResults'
6. Load another data file: VO2data_VEVCO2_20171009.xlsx (?date variable)
    - read 'Efficiency' params - line by line per subject (post-update)

run from console/terminal with (example):
>python CosmedParser.py --filedir "data" --sheet "Sheetname_to_extract"

Created on Thu Mar 2 2017

@author: Liz Cooper-Williams, QBI
"""

import argparse
import glob
from datetime import datetime
from os import R_OK, access
from os.path import join, basename
import numpy as np

import pandas as pd
from qbixnat.dataparser.DataParser import stripspaces

VERBOSE = 1

#Not using DataParser as too complex
class CosmedParser():
    def __init__(self, inputdir,inputsubdir,datafile,fieldsfile):
        #Load fields
        self.subjectdataloc = pd.read_excel(fieldsfile, header=0, sheetname='cosmed')
        self.fields = pd.read_excel(fieldsfile, header=0, sheetname='cosmed_xnat')
        self.datafields = pd.read_excel(fieldsfile, header=0, sheetname='cosmed_data')

        #Get list of subjects - parse individual files
        self.files = glob.glob(join(inputdir, inputsubdir, "*.xlsx"))
        print('Files: %d' % len(self.files))

        #Load efficiency data from single file
        self.effdata = pd.read_excel(join(inputdir, datafile), sheetname=0, header=1)
        self.effdata.drop(self.effdata.index[0], inplace=True)
        self.effdata['SubjectID'] = self.effdata.apply(lambda x: stripspaces(x, 'ID'), axis=1)
        self.effdata_cols = {'0':[5,8], '3':[9,12],'6':[13,16], '9':[17,20], '12':[21,24]}
        cols = ['SubjectID','interval','date', 'filename','time']
        self.df = pd.DataFrame(columns=cols+self.fields['Parameter'].tolist())
        self.loaded = self.__loadData()

    def __loadData(self):
        rtn = False
        try:
            for f in self.files:
                filename = basename(f)
                if "MonthA" in filename:
                    continue
                fdata = self.parseFilename(filename)
                df_file_data = pd.read_excel(f, header=0, sheetname='Data')
                df_data_ex = df_file_data[df_file_data['Phase']=='EXERCISE']
                df_data_rec = df_file_data[df_file_data['Phase'] == 'RECOVERY']
                df_file_results = pd.read_excel(f, header=0, sheetname='Results', skiprows=4)
                if (df_file_data.iloc[0,3] == 'Test Time'):
                    ftime = df_file_data.iloc[0,4] #format with date
                else:
                    ftime = ''
                fdata.append(ftime)
                protocoldata = self.parseProtocol(df_file_results,df_data_ex,self.fields['Parameter'].tolist()[0:4])
                metabolicdata = self.parseMetabolic(df_file_results,self.fields['Parameter'].tolist()[4:8])
                cardiodata = self.parseCardio(df_data_ex,self.fields['Parameter'].tolist()[8:14])
                effdata = self.parseEfficiency(self.effdata,fdata[0], self.effdata_cols[fdata[1]])
                recoverydata = self.calcRecovery(df_data_ex,df_data_rec)
                row=fdata+protocoldata+metabolicdata+cardiodata+effdata+recoverydata
                s_x = pd.Series(row, index=self.df.columns.tolist())
                self.df = self.df.append(s_x, ignore_index=True)

            print(self.df)
            if not self.df.empty:
                rtn = True

        finally:
            return rtn

    def parseFilename(self,filename):
        fparts = filename.split("_")
        # split to ID, interval, date
        id = fparts[0]
        interval = fparts[1][0]
        fdate = fparts[3][0:8]
        msg = 'Filedata: %s, %s, %s' % (id,interval,fdate)
        print(msg)
        return [id,interval,fdate,filename]

    def parseProtocol(self, df_results,df_data_ex, fieldnames):
        data =[]
        for field in fieldnames[0:3]:
            max = df_results[df_results['Parameter'] == field]['Max'].values[0]
            if max is None:
                max=''
            data.append(max)
        # One field is in data tab not results
        datafield = fieldnames[3]
        data.append(df_data_ex[datafield].iloc[-1])
        if VERBOSE:
            print("Proto:",data)
        return data

    def parseMetabolic(self, df_data,fieldnames):
        data =[]
        for field in fieldnames:
            max = df_data[df_data['Parameter'] == field]['Max'].values[0]
            if max is None:
                max=''
            data.append(max)
        if VERBOSE:
            print("Metab:",data)
        return data

    def parseCardio(self, df_data, fieldnames):
        data =[]
        for field in fieldnames:
            max = df_data[field].iloc[-1]
            if max is None:
                max=''
            data.append(max)
        if VERBOSE:
            print("Cardio:",data)
        return data

    def calcRecovery(self, df_ex,df_data):
        """
        Get Recovery data fields
        :param df_ex: Exercise data subset
        :param df_data: Recover data subset
        :return: [HRR1,HRR2,HRR3]
        """
        data =[]
        t0 = df_data['t'].iloc[0]
        t1 = df_data['t'].iloc[1]
        dt = (t1.minute *60 + t1.second) - (t0.minute *60 + t0.second)
        print('time diff=', dt, 's')

        d0 = df_ex['HR'].iloc[-1]
        for i in [1,5,9]:
            d1 = df_data['HR'].iloc[i]
            d = d0-d1
            data.append(d)
        if VERBOSE:
            print("HRR:",data)
        return data

    def parseEfficiency(self, df_data, sid, intervals):
        """
        Get Efficiency data fields
        :param df_data: Separate file VO2data
        :param sid: subject id
        :param intervals: [col_start, col_end]
        :return:
        """
        row = df_data[df_data['SubjectID']==sid]
        data = row.iloc[:,intervals[0]:intervals[1]].values.tolist()[0]

        if len(data)==0:
            data=['','','']
        if VERBOSE:
            print("Eff:",data)
        return data

    def sortSubjects(self):
        '''Sort data into subjects by participant ID'''
        self.subjects = dict()
        if self.df is not None:
            sids = self.df[0]['SubjectID'].unique()
            ids = [i for i in sids if len(i) == 6]
            for sid in ids:
                self.subjects[sid] = dict()
                # for i, intval in self.intervals.items():
                #     data = self.df[i]
                #     self.subjects[sid][i]= data[data['SubjectID'] == sid]
                if VERBOSE:
                    print('Subject:', sid, 'with datasets=', len(self.subjects[sid]))
            print('Subjects loaded=', len(self.subjects))


    def getSampleid(self, sd, interval):
        """
        Generate Unique sample ID - append prefix for subtypes
        :param sd: Subject ID
        :param row: row data with unique number
        :return: id
        """
        id = 'DXA_' + sd + '_' + str(interval)
        return id

    def getxsd(self):
        xsd = 'opex:cosmed'
        return xsd

    def mapData(self, row, i, xsd):
        """
        Map SWM data to row input data
        :param row: pandas series row data
        :return: data kwargs structure to load to xnat expt
        """

        mandata = {
            xsd + '/interval': str(i),
            xsd + '/sample_id': str(row.index.values[0]),  # row number in this data file for reference
            xsd + '/sample_quality': 'Good',  # default - check later if an error
            xsd + '/data_valid': 'Checked',
            xsd + '/comments': ''
        }
        motdata = {}
        for i in range(len(self.fields)):
            field = self.fields['Field'][i]
            xnatfield = self.fields['XnatField'][i]
            if field in row and not np.isnan(row[field].iloc[0]):
                motdata[xsd + '/' + xnatfield] = str(row[field].iloc[0])
        return (mandata, motdata)



########################################################################

if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog='Parse MRI Analysis',
                                     description='''\
            Reads files in a directory and extracts data for upload to XNAT

             ''')
    parser.add_argument('--filedir', action='store', help='Directory containing files', default="..\\..\\sampledata\\cosmed")
    parser.add_argument('--subdir', action='store', help='Subdirectory with individual files',
                        default="VO2data_crosschecked")
    parser.add_argument('--datafile', action='store', help='VEVCO2 file', default='VO2data_VEVCO2_20171009.xlsx')
    parser.add_argument('--fields', action='store', help='Fields to extract',
                        default="..\\..\\resources\\cosmed_fields.xlsx")
    args = parser.parse_args()

    inputdir = args.filedir
    inputsubdir = args.subdir
    datafile = args.datafile
    fieldsfile = args.fields
    print("Input:", inputdir)
    if access(inputdir, R_OK):
        dp = CosmedParser(inputdir,inputsubdir,datafile,fieldsfile)
        print(dp.df)
        # xsd = dp.getxsd()
        # dp.sortSubjects()
        #
        # for sd in dp.subjects:
        #     print '\n***********SubjectID:', sd
        #     for i, row in dp.subjects[sd].items():
        #         #print 'Interval:', dp.intervals[i]
        #         sampleid = dp.getSampleid(sd, i)
        #         print 'Sampleid:', sampleid
        #         (mandata, data) = dp.mapData(row, i, xsdtypes)
        #         print mandata
        #         print data
                # for field in dp.fields['Field']:
                #     if field in row and not np.isnan(row[field].iloc[0]):
                #         print field, "=", row[field].iloc[0]

    else:
        print("Cannot access directory: ", inputdir)
