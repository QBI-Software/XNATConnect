# -*- coding: utf-8 -*-
"""
Utility script: OPEXReport

run from console/terminal with (example):
>python OPEXReport.py --filedir "data" --sheet "Sheetname_to_extract"

Created on Thu Mar 2 2017

@author: Liz Cooper-Williams, QBI
"""

import argparse
from collections import OrderedDict
from datetime import datetime
from os.path import expanduser
from os.path import join

import numpy as np
import pandas


class OPEXReport(object):
    def __init__(self, subjects=None, csvfile=None):
        """
        List of subjects from XNAT as collection
        :param subjects:
        :param csvfile: spreadsheet export from OPEX subjects tab (with counts)
        """
        self.subjects = None
        self.subjectids = None
        self.data = None
        self.minmth = 0
        self.maxmth = 12
        self.cache = csvfile
        self.xnat = None
        self.exptintervals = self.__experiments()
        if csvfile is not None:
            self.data = pandas.read_csv(csvfile)
        if subjects is not None:
            self.subjects = subjects
            if isinstance(subjects, pandas.DataFrame):
                self.subjectids = subjects['subject_label']
            else:
                self.subjectids = [s.label() for s in subjects]
            print "Subjects loaded from database"
        elif self.data is not None and 'Subject' in self.data:
            self.subjectids = self.data.Subject.unique()
            print "Subject IDs loaded from file"

    def __experiments(self):
        """Create list of experiments in set order"""
        fields = [('Health', 3),
                  ('ACER', 6),
                  ('CANTAB DMS', 1),
                  ('CANTAB ERT', 1),
                  ('CANTAB MOT', 1),
                  ('CANTAB PAL', 1),
                  ('CANTAB SWM', 1),
                  ('VWM', 3),
                  ('PSQI', 3),
                  ('DASS', 3),
                  ('IPAQ', 3),
                  ('Insomnia', 3),
                  ('Godin', 3),
                  ('COBAS', 1),
                  ('ELISAS', 1),
                  ('MULTIPLEX', 1),
                  ('MR Sessions', 6),
                  ('MRI ASHS', 6),
                  ('MRI FS', 6),
                  ('DEXA',3),
                  ('COSMED',3)]
        od = OrderedDict(fields)
        return od

    def _expt_types(self):
        """Create list of experiments in set order"""
        fields = [('Health', 'opex:health'),
                  ('ACER', 'opex:acer'),
                  ('CANTAB DMS', 'opex:cantabDMS'),
                  ('CANTAB ERT', 'opex:cantabERT'),
                  ('CANTAB MOT', 'opex:cantabMOT'),
                  ('CANTAB PAL', 'opex:cantabPAL'),
                  ('CANTAB SWM', 'opex:cantabSWM'),
                  ('COBAS', 'opex:bloodCobasData'),
                  ('ELISAS', 'opex:bloodElisasData'),
                  ('MULTIPLEX', 'opex:bloodMultiplexData'),
                  ('MR Sessions', 'xnat:mrSessionData'),
                  ('MRI ASHS', 'opex:mriashs'),
                  ('MRI FS', 'opex:mrifs'),
                  ('DEXA','opex:dexa'),
                  ('COSMED', 'opex:cosmed'),
                  ('VWM', 'opex:amunet'),
                  ('PSQI', 'opex:psqi'),
                  ('DASS', 'opex:dass'),
                  ('IPAQ', 'opex:ipaq'),
                  ('Insomnia', 'opex:insomnia'),
                  ('Godin', 'opex:godin')
                  ]
        od = OrderedDict(fields)
        return od

    def getParticipants(self):
        """
        Get Number of participants grouped by Group and Gender
        :return:
        """
        if self.data is not None:
            groups = self.data[['Group', 'M/F']]
            groups.columns = ['group', 'gender']
        elif isinstance(self.subjects, pandas.DataFrame):
            groups = self.subjects[['sub_group', 'gender_text']]
            groups.rename(columns={'sub_group': 'group', 'gender_text': 'gender'}, inplace=True)
        else:
            groups = pandas.DataFrame([(s.attrs.get('group'), s.attrs.get('gender')) for s in self.subjects],
                                      columns=['group', 'gender'])
        # Set up frequency histogram
        df = groups.groupby('group').count()
        if 'male' in groups.gender.unique():
            df_male = groups.groupby(['gender']).get_group('male')
            df_female = groups.groupby(['gender']).get_group('female')
        else:
            df_male = groups.groupby(['gender']).get_group('M')
            df_female = groups.groupby(['gender']).get_group('F')
        df['Male'] = df_male.groupby('group').count()
        df['Female'] = df_female.groupby('group').count()
        df = df.rename(columns={'gender': 'All'})
        dg = df['All']._construct_axes_dict()  # workaround
        df['Group'] = dg['index']
        df.replace(to_replace=np.nan, value=0, inplace=True)
        return df

    def getExptCollection(self, projectcode):
        """
        Generate Frequency histogram for expts collected
        :param csvfile:
        :return: sorted counts of each expt per participant
        """
        df = None
        if self.data is None:
            self.data = self.getExptCounts(projectcode)
        # Area chart or Stacked Bar Chart or Histogram
        groups = self.data
        # replace NaN with 0
        groups.fillna(0, inplace=True)
        # exclude withdrawn
        df = groups[groups.Group != 'withdrawn']
        # sort by largest number expts
        if 'MONTH' in df:
            df = df.sort_values('MONTH', ascending=True)
        else:
            df = df.sort_values('CANTAB DMS', ascending=True)
        # plot - exclude Subject, m/f,hand,yob
        cols = ['Group', 'Subject'] + self.exptintervals.keys()
        cols_present = [h for h in cols if h in df.columns]
        df = df[cols_present]

        return df

    def processCounts(self, subj, q):
        """
        Process counts via multiprocessing
        :param subj:
        :return:
        """
        result = []
        if subj is not None:
            etypes = self._expt_types()
            result = [subj.attrs.get('group'), subj.label(), subj.attrs.get('gender')]
            counts = self.xnat.getExptCounts(subj)
            for expt in self.exptintervals.keys():
                etype = etypes[expt]
                if (etype in counts):
                    result.append(counts[etype])
                else:
                    result.append(0)

            result.append(self.getMONTH(counts['firstvisit']))
            q[subj.label()] = result
            # print result
        # print "Counts:", len(self.counts)
        return result

    def getExptCounts(self, projectcode):
        dfsubjects = None
        if self.xnat is not None:
            df_counts = self.getOPEXExpts(projectcode)
            # Get first visit as starting point in study
            v0 = df_counts.filter(regex="_visit", axis=1)
            v = v0.replace(['',np.nan], 'ZZZZZZZ')
            df_counts['first_visit'] = v.min(axis=1, skipna=True)
            df_counts.replace([np.inf, -np.inf, np.nan], 0, inplace=True)
            dfsubjects = self.formatCounts(df_counts)
            self.data = dfsubjects
        else:
            print("Load counts from file")  # TODO

        return dfsubjects

    def getOPEXExpts(self,projectcode,headers=None):
        """
        Get Expt data to parse
        :return:
        """
        etypes = sorted(self.xnat.conn.inspect.datatypes())
        df_subjects = self.xnat.getSubjectsDataframe(projectcode)
        # Cannot load all at once nor can get count directly so loop through each datatype and compile counts
        for etype in etypes:
            print "Expt type:", etype
            if etype.startswith('opex'):
                #fields = self.conn.inspect.datatypes(etype)
                columns = [etype + '/ID',etype + '/SUBJECT_ID',etype + '/DATE',etype + '/INTERVAL',etype + '/DATA_VALID',etype + '/SAMPLE_QUALITY']
                criteria = [(etype + '/SUBJECT_ID', 'LIKE', '*'), 'AND']
                df_dates = self.xnat.getSubjectsDataframe(projectcode, etype, columns, criteria)
                if df_dates is not None:
                    aggreg = {'subject_id': {etype:'count'}, 'date': {etype+'_date': 'min'}}
                    df_counts = df_dates.groupby('subject_id').agg(aggreg).reset_index()
                    df_counts.columns = df_counts.index.droplevel(level=0)
                    df_counts.columns = ['subject_id', etype + '_visit', etype]
                    df_subjects = df_subjects.merge(df_counts, how='left', on='subject_id')
                    print len(df_subjects)

        print(df_subjects.head())

        return df_subjects

    def downloadOPEXExpts(self,projectcode, outputdir):
        '''
        CSV downloads for each expt type
        :param projectcode:
        :return:
        '''
        etypes = sorted(self.xnat.conn.inspect.datatypes())
        columns = ['xnat:subjectData/SUBJECT_LABEL', 'xnat:subjectData/SUB_GROUP',
                   'xnat:subjectData/GENDER_TEXT', 'xnat:subjectData/DOB']
        for etype in etypes:
            print "Expt type:", etype
            if etype.startswith('opex'):
                fields = self.xnat.conn.inspect.datatypes(etype)
                fields = columns + fields
                #print(fields)
                criteria = [(etype + '/SUBJECT_ID', 'LIKE', '*'), 'AND']
                df_expts = self.xnat.getSubjectsDataframe(projectcode, etype, fields, criteria)
                if df_expts is not None:
                    print('Expts:', len(df_expts))
                    outputname = etype.replace(":", "_") + ".csv"
                    df_expts.to_csv(join(outputdir,outputname), index=False)
                else:
                    print('No data')


    def formatCounts(self, df_counts):
        """
        Format counts dataframe with headers in order
        :param df-counts: produced by Xnatconnector.getOPEXExpts
        :return:
        """
        if not df_counts.empty:
            # print(df_counts.columns)
            df_counts['MONTH'] = df_counts['first_visit'].apply(lambda d: self.getMONTH(d))
            etypes = self._expt_types()
            # rename columns
            df_counts.rename(columns={'sub_group': 'Group', 'subject_label': 'Subject', 'gender_text': 'M/F'},
                             inplace=True)
            for etype in etypes:
                df_counts.rename(columns={etypes[etype]: etype}, inplace=True)
            # reorder columns
            headers = ['MONTH', 'Subject', 'Group', 'M/F'] + self.exptintervals.keys()
            headers_present = [h for h in headers if h in df_counts.columns]
            df_counts = df_counts[headers_present]
            # save to file as cache if db down
            df_counts.to_csv(self.cache, index=False)
            # print df_counts.head()

        return df_counts

    def getMONTH(self, vdate, formatstring='%Y-%m-%d'):
        """
        Calculate MONTH in trial from first visit date
        :param vdate: datetime.datetime object
        :return: interval as 0,1,2 ...
        """
        months = 0
        if isinstance(vdate, str) and len(vdate) > 0:  # and not isinstance(vdate, datetime):
            vdate = datetime.strptime(vdate, formatstring)
        else:
            return months
        tdate = datetime.today()
        dt = tdate - vdate
        if dt.days > 0:
            months = int(dt.days // 30)
        return months

    def maxValue(self, row):
        """
        Function per row - assumes first two are MONTH, Subject
        :param row:
        :return: max of values in row
        """
        val = row[2:].max()
        # print "Val=",val
        # int(max(row.iloc[0, 1:].values)
        return int(val)

    def calculateMissing(self, row):
        """
        Function per row - replace counts with missing
        :param row:
        :return:
        """
        for hdr in self.exptintervals.keys():
            # print row
            if hdr in row:
                # print "1.",hdr, "=", row[hdr]
                row[hdr] = len(range(self.minmth, row['MONTH'], self.exptintervals[hdr])) - row[hdr]
                # print "2.",hdr, "=", row[hdr]
        return row

    def printMissingExpts(self, projectcode=None):
        """
        Print expt counts with true/false if complete data set for current MONTH
        :param self:
        :return:
        """
        data = self.getExptCounts(projectcode)
        if data is None or data.empty:  # use cached data
            data = self.data
        # Filter groups
        if 'Group' in data.columns:
            data = data[data.Group != 'withdrawn']
        headers = ['MONTH', 'Subject'] + self.exptintervals.keys()
        headers_present = [h for h in headers if h in data.columns]
        report = data[headers_present]
        if 'MONTH' not in report:
            report['MONTH'] = report.apply(self.maxValue, axis=1)
        report = report.apply(self.calculateMissing, axis=1)
        #Only one CANTAB
        report = report.drop(['CANTAB ERT','CANTAB MOT','CANTAB PAL', 'CANTAB SWM'], axis=1)
        # print report
        return report

    def getMultivariate(self, expts):
        """
        List of expts from XNAT as collection
        :param expts:
        :return:
        """
        expts = pandas.DataFrame([e for e in expts])
        expts

        # Group
        # df_grouped = groups.groupby(by='Group')
        # df_grouped.plot.bar(x='Group',y=cols[2:])
        # df_AIT = df_grouped.get_group('AIT')
        # df_MIT = df_grouped.get_group('MIT')
        # df_LIT = df_grouped.get_group('LIT')

    def formatDobNumber(self, orig):
        """
        Reformats DOB string from Excel data float to yyyy-mm-dd
        """
        dateoffset = 693594
        dt = datetime.fromordinal(dateoffset + int(orig))
        return dt.strftime("%Y-%m-%d")


########################################################################

if __name__ == "__main__":
    from qbixnat.XnatConnector import XnatConnector  # Only for testing

    parser = argparse.ArgumentParser(prog='OPEX Report',
                                     description='''\
            Script for reports of QBI OPEX XNAT db
             ''')
    parser.add_argument('database', action='store', help='select database config from xnat.cfg to connect to')
    parser.add_argument('projectcode', action='store', help='select project by code')
    parser.add_argument('--cache', action='store', help='use a downloaded csv file - no connection')
    parser.add_argument('--output', action='store', help='output directory for csv files')
    args = parser.parse_args()
    if (args.cache is not None):
        try:
            op = OPEXReport(csvfile=args.cache)
            # print "****Participant groups****"
            # df = op.getParticipants()
            # print df
            # Get Frequency histogram of expts collected
            # print "\n****Frequency histogram of expts****"
            # df = op.getExptCollection()
            print "\n****Missing data report****"
            df = op.printMissingExpts()

        except IOError as e:
            print "IOError: cannot access file: ", e.message
            exit(0)
    else:  # Connections
        print "Connecting to database"
        home = expanduser("~")
        configfile = join(home, '.xnat.cfg')
        database = args.database
        projectcode = args.projectcode
        xnat = XnatConnector(configfile, database)
        print "Connecting to URL=", xnat.url
        xnat.connect()
        try:
            print "...Connected"
            # proj = xnat.get_project(projectcode)
            subjects = xnat.getSubjectsDataframe(projectcode)
            msg = "Loaded %d subjects from %s : %s" % (len(subjects), database, projectcode)
            print msg
            op = OPEXReport(subjects=subjects)
            op.xnat = xnat
            df = op.getParticipants()
            print df
            #Download CSV files: DO NOT CHANGE - Hooked up from GUI
            if args.output is not None and args.output:
                outputdir = args.output
                op.downloadOPEXExpts(projectcode=projectcode, outputdir=outputdir)
            #Dash report test - can change
            else:
                op.printMissingExpts(projectcode)

            # MULTIPROCESSING REQUIRED
            #
            # print("There are %d CPUs on this machine" % multiprocessing.cpu_count())
            # active_subjects = [s for s in subjects if s.attrs.get('group') != 'withdrawn']
            # subjects = list(active_subjects)
            # start = time.time()
            # total_tasks = len(subjects)
            # tasks = []
            # mm = multiprocessing.Manager()
            # q = mm.dict()
            # for i in range(total_tasks):
            #     p = multiprocessing.Process(target=op.processCounts, args=(subjects[i],q))
            #     tasks.append(p)
            #     p.start()
            #
            # for p in tasks:
            #     p.join()
            #
            # print "Finished:", time.time() - start, 'secs'


            # print "*****All Counts:******"
            # headers = ['Group','Subject', 'M/F'] + op.exptintervals.keys() + ['MONTH']
            # print q.values()
            # op.counts = pandas.DataFrame(q.values(), columns=headers)
            # print op.counts


        except ValueError as e:
            print "Error: ", e
        finally:
            xnat.conn.disconnect()
            print("FINISHED")
