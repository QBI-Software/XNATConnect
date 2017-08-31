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

from qbixnat.CantabParser import CantabParser


class OPEXReport(object):

    def __init__(self, subjects=None, csvfile=None):
        """
        List of subjects from XNAT as collection
        :param subjects:
        """
        self.subjects = None
        self.subjectids = None
        self.data = None
        if subjects is not None:
            self.subjects = subjects
            print "Subjects loaded from database"
        elif csvfile is not None:
            self.data = pandas.read_csv(csvfile)
            if 'Subject' in self.data:
                self.subjectids = self.data.Subject.unique()
                print "Subject IDs loaded from file"



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
            cols = ['Group','Subject','Health screening','ACER',
                    'CANTAB DMS',	'CANTAB ERT',	'CANTAB MOT',	'CANTAB PAL',	'CANTAB SWM',
                    'MR Sessions','MRI ASHS',	'MRI FreeSurfer',
                    'Virtual Water Maze','PSQI','DASS','IPAQ',	'Insomnia','Godin']
            df = df[cols]
            #test plot
            df.plot.area(x='Subject', y=cols[2:])

        return df

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
            print "\n****Frequency histogram of expts****"
            df = op.getExptCollection()

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
        if (xnat.conn):
            print "...Connected"
            proj = xnat.get_project(projectcode)
            subjects = xnat.get_subjects(projectcode)
            msg = "Loaded %d subjects from %s" % (len(subjects.fetchall), proj.getID())
            print msg
            op = OPEXReport(subjects=subjects)
            df = op.getParticipants()
            print df


            # cantab = CantabParser("resources\\cantab_fields.csv", None)
            # for xsd in cantab.getxsd():
            #     expts = proj.experiments(xsd + "*")  # prefix of labels/ids
            #     teste = expts.fetchone()
            #     if (teste is not None):
            #         df_baseline = cantab.getDFExpts(expts, '0',xsd)
            #         print(df_baseline)
            #     else:
            #         print('No expts found for:', xsd)


            xnat.conn.disconnect()
            print("FINISHED")

        else:
            print "Failed to connect"
