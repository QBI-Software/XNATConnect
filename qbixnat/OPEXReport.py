# -*- coding: utf-8 -*-
"""
Utility script: OPEXReport

run from console/terminal with (example):
>python OPEXReport.py --filedir "data" --sheet "Sheetname_to_extract"

Created on Thu Mar 2 2017

@author: Liz Cooper-Williams, QBI
"""

from datetime import datetime
from os.path import expanduser
from os.path import join

import numpy as np
import pandas
import argparse
import multiprocessing
from collections import OrderedDict
from qbixnat.CantabParser import CantabParser


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
        self.exptintervals = self.__experiments()
        self.counts = None
        if subjects is not None:
            self.subjects = subjects
            self.subjectids = [s.label() for s in subjects]
            print "Subjects loaded from database"
        elif csvfile is not None:
            self.data = pandas.read_csv(csvfile)
            if 'Subject' in self.data:
                self.subjectids = self.data.Subject.unique()
                print "Subject IDs loaded from file"

    def __experiments(self):
        """Create list of experiments in set order"""
        fields= [('Health screening', 3),
             ('ACER', 3),
             ('CANTAB DMS', 1),
             ('CANTAB ERT', 1),
             ('CANTAB MOT', 1),
             ('CANTAB PAL', 1),
             ('CANTAB SWM', 1),
             ('MR Sessions', 6),
             ('MRI ASHS', 6),
             ('MRI FreeSurfer', 6),
             ('Virtual Water Maze', 3),
             ('PSQI', 3),
             ('DASS', 3),
             ('IPAQ', 3),
             ('Insomnia', 3),
             ('Godin', 3)]
        od = OrderedDict(fields)
        return od

    def _expt_types(self):
        """Create list of experiments in set order"""
        fields= [('Health screening','opex:health'),
             ('ACER','opex:acer'),
             ('CANTAB DMS','opex:cantabDMS'),
             ('CANTAB ERT','opex:cantabERT'),
             ('CANTAB MOT','opex:cantabMOT'),
             ('CANTAB PAL','opex:cantabPAL'),
             ('CANTAB SWM','opex:cantabSWM'),
             ('MR Sessions','xnat:mrSessionData'),
             ('MRI ASHS','opex:mriashs'),
             ('MRI FreeSurfer','opex:mrifs'),
             ('Virtual Water Maze','opex:amunet'),
             ('PSQI','opex:psqi'),
             ('DASS','opex:dass'),
             ('IPAQ','opex:ipaq'),
             ('Insomnia','opex:insomnia'),
             ('Godin','opex:godin')]
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
        else:
            groups = pandas.DataFrame([(s.attrs.get('group'), s.attrs.get('gender')) for s in self.subjects], columns=['group','gender'])
        #Set up frequency histogram
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
        dg = df['All']._construct_axes_dict() #workaround
        df['Group'] = dg['index']
        df.replace(to_replace=np.nan, value=0, inplace=True)
        return df

    def getExptCollection(self):
        """
        Generate Frequency histogram for expts collected
        :param csvfile:
        :return: sorted counts of each expt per participant
        """
        df = None
        if self.data is not None:
            #Area chart or Stacked Bar Chart or Histogram
            groups = self.data
            #replace NaN with 0
            groups.fillna(0, inplace=True)
            #exclude withdrawn
            df = groups[groups.Group != 'withdrawn']
            #sort by largest number expts (cantabDMS) - ascending
            df = df.sort_values('CANTAB DMS')
            #plot - exclude Subject, m/f,hand,yob
            cols = ['Group','Subject']
            cols = cols.append(self.exptintervals.keys())

            df = df[cols]
            #test plot
            #df.plot.area(x='Subject', y=cols[2:])

        return df

    def work(self,number):
        """
            Multiprocessing work

            Parameters
            ----------
            number : integer
                unit of work number
            """
        print "Unit of work number %d" % number  # simply print the worker's number

    def getCounts(self, xnat):
        """
        Experiment counts for all subjects - from database
        :param xnat: connection to database
        :return: dataframe as counts
        """
        headers = ['Subject'] + self.exptintervals.keys() + ['Stage']
        etypes = self._expt_types()
        if self.counts is None:
            self.counts = pandas.DataFrame([], columns=headers)
        if self.subjects is not None:
            for subj in subjects:
                print "Subject:", subj.label()
                result = [subj.label()]
                counts = xnat.getExptCounts(subj)
                for expt in self.exptintervals.keys():
                    etype = etypes[expt]
                    if (etype in counts):
                        result.append(counts[etype])
                    else:
                        result.append(0)

                result.append(self.getStage(counts['firstvisit']))
                self.counts.append(result)
                print result
        print self.counts

    def getStage(self,vdate):
        """
        Calculate stage in trial from first visit date
        :param vdate: datetime.datetime object
        :return: interval as 0,1,2 ...
        """
        months=0
        if vdate is not None:
            tdate = datetime.today()
            dt = tdate - vdate
            if dt.days > 0:
                months = int(dt.days // 30)
        return months

    def printMissingExpts(self):
        """
        Print expt counts with true/false if complete data set for current stage
        :param self:
        :return:
        """
        if self.data is not None or self.counts is not None:
            # find all experiments
            #sexpts = self.exptintervals
            headers = ['Subject'] + self.exptintervals.keys()
            if self.data is not None:
                fdata = self.data[headers]
            elif self.counts is not None:
                fdata = self.counts
            report = fdata.copy()
            report["Progress"]=""
            for s in sorted(self.subjectids):
                print "Subject:", s
                result = [s]
                sdata = fdata.query("Subject == '" + s + "'") #find data for this subject
                x = sdata.index.tolist()[0]
                if self.data is not None:
                    smonth = int(list(sdata['CANTAB DMS'])[0]) #determine how far through the trial
                elif self.counts is not None and sdata['Stage'] is not None:
                    smonth = sdata['Stage'][0]
                sprogress = (100 * smonth/self.maxmth)
                print "Progress:", smonth, "month", sprogress, "%"
                #for each expt - list number collected
                for e in self.exptintervals.keys():
                    v = False
                    sd = list(sdata[e])[0]
                    if (sd is None or np.isnan(sd)):
                        print e, "None"
                    elif(sd == len(range(self.minmth,smonth,self.exptintervals[e]))):
                        print e, "Complete"
                        v = True
                    else:
                        print e, "Partial"

                    result.append(v)
                result.append(sprogress)
                report.iloc[x] = result

            print report

            #Group
            # df_grouped = groups.groupby(by='Group')
            # df_grouped.plot.bar(x='Group',y=cols[2:])
            # df_AIT = df_grouped.get_group('AIT')
            # df_MIT = df_grouped.get_group('MIT')
            # df_LIT = df_grouped.get_group('LIT')


    def getMultivariate(self, expts):
        """
        List of expts from XNAT as collection
        :param expts:
        :return:
        """
        expts = pandas.DataFrame([e for e in expts])
        expts

    def formatDobNumber(self,orig):
        """
        Reformats DOB string from Excel data float to yyyy-mm-dd
        """
        dateoffset = 693594
        dt = datetime.fromordinal(dateoffset + int(orig))
        return dt.strftime("%Y-%m-%d")

########################################################################
def work(number):
    """
        Multiprocessing work

        Parameters
        ----------
        number : integer
            unit of work number
        """
    print "Unit of work number %d" % number  # simply print the worker's number

def counts(tasks):
    subject = tasks[0]
    xnat = tasks[1]
    counts = xnat.getExptCounts(subject)
    print counts

if __name__ == "__main__":
    from qbixnat.XnatConnector import XnatConnector #Only for testing

    parser = argparse.ArgumentParser(prog='OPEX Report',
                                     description='''\
            Script for reports of QBI OPEX XNAT db
             ''')
    parser.add_argument('database', action='store', help='select database config from xnat.cfg to connect to')
    parser.add_argument('projectcode', action='store', help='select project by code')
    parser.add_argument('--testfile', action='store', help='use a downloaded csv file - no connection')
    args = parser.parse_args()
    if (args.testfile is not None):
        try:
            op = OPEXReport(csvfile=args.testfile)
            # print "****Participant groups****"
            # df = op.getParticipants()
            # print df
            #Get Frequency histogram of expts collected
            #print "\n****Frequency histogram of expts****"
            #df = op.getExptCollection()
            print "\n****Missing data report****"
            df = op.printMissingExpts()

        except IOError as e:
            print "IOError: cannot access file: ", e.message
            exit(0)
    else:  #Connections
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
            proj = xnat.get_project(projectcode)
            subjects = xnat.get_subjects(projectcode)
            msg = "Loaded %d subjects from %s" % (len(subjects.fetchall()), proj.id())
            print msg
            op = OPEXReport(subjects=subjects)
            df = op.getParticipants()
            print df


            print("There are %d CPUs on this machine" % multiprocessing.cpu_count())
            number_processes = 2
            pool = multiprocessing.Pool(number_processes)
            total_tasks = len(subjects.fetchall())
            tasks = range(total_tasks)
            print tasks
            #results = pool.map_async(work, tasks)
            results = pool.map_async(xnat.getExptCounts, (subjects,))
            print results.get(timeout=1)
            # # Get counts from database
            # df_counts = op.getCounts(xnat)
            # print df_counts
            pool.close()
            pool.join()
        except ValueError as e:
            print "Error: Failed to connect", e
        finally:
            xnat.conn.disconnect()
            print("FINISHED")
