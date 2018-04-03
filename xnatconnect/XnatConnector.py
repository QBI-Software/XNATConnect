from __future__ import print_function
# -*- coding: utf-8 -*-
"""
XNAT connector class for scripts

@author: Liz Cooper-Williams, QBI
"""
import argparse
import csv

# import resource
import datetime
import logging
import os
import re
import shutil
import warnings
from os import listdir
from os.path import expanduser
from os.path import join

import pandas as pd
import pyxnat
from configobj import ConfigObj

from XnatUploadScans import ScanUploader

warnings.filterwarnings("ignore")

class XnatConnector:
    def __init__(self, configfile, sitename):
        config = ConfigObj(configfile)
        self.url = config[sitename]['URL']
        self.user = config[sitename]['USER']
        self.passwd = config[sitename]['PASS']
        # print "Config:", self.url , ", ", self.user, ", ", self.passwd

    def connect(self):
        """
        Connect to xnat server via config
        """
        self.conn = pyxnat.Interface(server=self.url, user=self.user, verify=True,
                                     password=self.passwd, cachedir='/tmp')  # connection object

    def testconnection(self):
        """
        Test connection actually exists by returning some data
        :return: true or false
        """
        if self.conn is None:
            return False
        testconn = self.conn.inspect.datatypes('xnat:subjectData')
        return (len(testconn) > 0)

    def get_project(self, projectcode):
        if not self.conn:
            self.connect()
        qry_project = '/projects/%s' % projectcode
        return self.conn.select(qry_project)

    def get_projectPI(self, projectcode):
        """
        Finds the Principal Investigator for the project and returns their surname
        :param projectcode:
        :return:
        """
        if not self.conn:
            self.connect()
        qry_project = '/projects/%s' % projectcode
        proj = self.conn.select(qry_project)
        return proj.attrs.get('xnat:projectData/PI/lastname')

    def get_subjects(self, projectcode):
        if not self.conn:
            self.connect()
        qry = '/projects/%s/subjects' % projectcode
        return self.conn.select(qry)

    def list_projects(self):
        if not self.conn:
            self.connect()
        qry_project = '/projects'
        return self.conn.select(qry_project)

    def list_subjects_all(self, projectcode, fieldnames=None):
        """
        Lists all subjects in a project to console
        """

        subj = self.get_subjects(projectcode)
        outfilename = projectcode + '_subjectlist.csv'
        with open(outfilename, 'wb') as csvfile:
            if fieldnames is None:
                fieldnames = ['ID', 'group', 'label', 'dob', 'gender', 'handedness', 'education']
            mywriter = csv.DictWriter(csvfile, fieldnames=fieldnames)
            mywriter.writeheader()
            for s in subj:
                print("ID=", s.label(), ", SubjectID=", s.id())  # xnat subject id eg XNAT_S00006
                # ID	group	label	dob	gender	handedness	education
                mywriter.writerow({'ID': s.label(),
                                   'group': s.attrs.get('group'),
                                   'dob': s.attrs.get('dob'),
                                   'gender': s.attrs.get('gender'),
                                   'handedness': s.attrs.get('handedness'),
                                   'education': s.attrs.get('education')
                                   })
        print("Subjects written to file:", outfilename)
        return outfilename

    def get_subjectid_bylabel(self, projectcode, label):
        """
        Find the XNAT ID for a subject by label

        EXAMPLE
        sid = ixnat.get_subjectid_bylabel('QBICC', '1554603')

        """
        # constraints = [('xnat:subjectData/LABEL', '=', label)]
        project = self.get_project(projectcode)
        s = project.subject(label)
        if s.exists():
            return s.id()
        else:
            logging.warning("Subject not found: %s", label)
            return None

    def createSubject(self, projectcode, label, subjectkwargs):
        """
        Create a subject in this project with the label as ID and subject parameters as key value
        No checks made on args eg {'dob': '1949-11-06', 'gender': 'female'}
        """
        project = self.get_project(projectcode)
        subject = project.subject(label)
        subject.create()
        if subject.exists():
            # set attrs
            subject.attrs.mset(subjectkwargs)
            return subject
        else:
            logging.warning("Subject not created: %s", label)
            return None

    def createExperiment(self, subject, xsdtype, exptid, mandata, exptdata):
        """
        Creates an experiment of type xsdtype for subject with exptid and exptdata as dict
        No checks made for correct data fields - must represent the XSD as set in the database
        :param subject: Subject object
        :param xsdtype: schema datatype
        :param exptid: ID for expt
        :param exptdata: data for expt as dict
        :return: expt or None
        """
        expt = None
        if subject is not None:
            mandata['experiments'] = xsdtype
            mandata['ID'] = exptid
            logging.debug(mandata)
            if xsdtype + '/date' in mandata:
                vdate = mandata[xsdtype + '/date']
                if "-" in vdate:
                    expt_creation = datetime.datetime.strptime(mandata[xsdtype + '/date'], "%Y-%m-%d")
                else:
                    expt_creation = datetime.datetime.strptime(mandata[xsdtype + '/date'], "%Y.%m.%d %H:%M:%S")
                del mandata[xsdtype + '/date']
            else:
                expt_creation = datetime.datetime.now()
            expt_creation_date = expt_creation.strftime("%Y%m%d")
            expt_creation_time = expt_creation.strftime("%H:%M:%S")
            # create with mandatory data
            expt = subject.experiment(exptid).create(**mandata)
            if not expt.exists():
                msg = 'Cannot create expt: %s' % exptid
                raise ValueError(msg)
            # Add attributes as other fields
            expt.attrs.set('xnat:experimentData/date', expt_creation_date)
            expt.attrs.set('xnat:experimentData/time', expt_creation_time)
            expt.attrs.mset(exptdata)

        return expt

    def checkUniqueLabel(self, subject, label):
        prefix = label.rsplit('_', 1)[0]
        experiments = [e.label() for e in subject.experiments() if
                       e.datatype() == 'xnat:mrSessionData' and e.label().startswith(prefix)]
        if label in experiments:
            experiments.sort(reverse=True)
            ctr = experiments[0].rsplit('_', 1)[1]
            # prefix = experiments[0].rsplit('_', 1)[0]
            c = int(ctr) + 1
            label = prefix + "_" + str(c)
        return label

    def updateExptDate(self, subject, exptid, exptdate, dsitype):
        """
        Update existing experiment date if not equal
        :param subject: Subject obj
        :param exptid:
        :param exptdate:
        :param dsitype:
        :return:
        """
        # project = self.get_project(projectcode)
        expt = subject.experiment(exptid)
        if expt.exists():
            # format date
            if not isinstance(exptdate, datetime.datetime):
                exptdate = datetime.datetime.strptime(exptdate, "%Y-%m-%d %H:%M:%S")
            edate = expt.attrs.get('xnat:experimentData/date')
            if edate != exptdate.strftime("%Y-%m-%d"):
                expt.attrs.set('xnat:experimentData/date', exptdate.strftime("%Y%m%d"))
                expt.attrs.set('xnat:experimentData/time', exptdate.strftime("%H:%M:%S"))
                print("Updated experiment date: ", expt.id())
                return expt
            else:
                return None
        else:
            return None

    def changeExptLabel(self, projectcode, oldlabel, newlabel):
        """
        Change label for an experiment - currently OPEX
        NOTE: Need to Load mandatory fields and subject ID
        Alternatively works on spreadsheet upload with these fields selected
        :param projectcode:
        :param oldlabel:
        :param newlabel:
        :return:
        """
        project = self.get_project(projectcode)
        expt = project.experiment(oldlabel)
        if expt.exists():
            xsd = expt.datatype()
            mandata = {
                xsd + '/label': newlabel,
                xsd + '/interval': expt.attrs.get(xsd + '/interval'),
                xsd + '/sample_quality': expt.attrs.get(xsd + '/sample_quality'),
                xsd + '/data_valid': expt.attrs.get(xsd + '/data_valid'),
                'subject_ID': expt.attrs.get('subject_ID')
            }
            print("Old:", expt.label())
            expt.attrs.mset(mandata)
            print("New:", expt.label())
        else:
            print("No expts found with label=", oldlabel)

    def getSubjectsDataframe(self, projectcode, dsitype=None, columns=None, criteria=None):
        """
        Gets subject label, id as dataframe
        :param projectcode:
        :return:
        """
        if columns is None:
            columns = ['xnat:subjectData/SUBJECT_LABEL', 'xnat:subjectData/SUBJECT_ID', 'xnat:subjectData/SUB_GROUP',
                       'xnat:subjectData/GENDER_TEXT', 'xnat:subjectData/DOB']
        if criteria is None:
            criteria = [('xnat:subjectData/SUBJECT_ID', 'LIKE', '*'), 'AND']
        if dsitype is None:
            dsitype = 'xnat:subjectData'
        subj = self.conn.select(dsitype, columns).where(criteria)
        # Convert to dataframe
        if len(subj) > 0:
            df_subjects = pd.DataFrame(list(subj))
            if 'xnat_subjectdata_subject_id' in df_subjects.columns:
                df_subjects.rename(columns={'xnat_subjectdata_subject_id': 'subject_id'}, inplace=True)
                # print(df_subjects.head())
        else:
            df_subjects = None
        return df_subjects

    def upload_MRIscans(self, projectcode, scandir, opexid=False, proj_pi=None):
        """
        Upload MRI scans from scandir to project
        :param projectcode: XNAT ID for project eg QBICC
        :param scandir: full path name of dir containing subdirs with data
        eg /ibscratch/irc5scans/data
        data should be organized by DICOM series as: data/subject_label/scans/series_number/*.dcm (or *.IMA)
        :return: number of sessions loaded
        """

        project = self.get_project(projectcode)
        suploader = ScanUploader(proj_pi)
        ctr = 0
        scanfiles = [f for f in listdir(scandir) if os.path.isdir(join(scandir, f))]
        if len(scanfiles) > 0:
            dirpath = os.path.dirname(scandir)
            # opex
            visitid = scandir.rsplit('_', 1)
            if len(visitid) > 1:
                m = re.match('(\d){1,2}[mM]?$', visitid[1])
                visitid = int(m.group(1))
            else:
                visitid = 1
            donepath = join(dirpath, 'done')
            if not os.path.isdir(donepath):
                try:
                    os.mkdir(donepath)
                except:
                    raise OSError
        else:
            message = "No scans found: %s" % scandir
            logging.error(message)

        # Loop through each directory where directory name is subject id
        for slabel in scanfiles:
            if opexid and len(slabel) > 6:
                # try to extract slabel eg 1006JJ06
                sid = self.get_subjectid_bylabel(projectcode, slabel[0:6])
            else:
                sid = self.get_subjectid_bylabel(projectcode, slabel)
            if sid is None:
                logging.warning("Subject doesn't exist - skipping %s", slabel)
                continue

            s = project.subject(sid)
            uploaddir = join(scandir, slabel, 'scans')
            if s.exists():
                elabel = 'MR_%s_%d' % (s.label(), ctr)
                elabel = self.checkUniqueLabel(s, elabel)
                message = "Uploading scans for %s: %s with expt=%s" % (s.id(), s.label(), elabel)
                logging.info(message)
                print(message)
                ctr = ctr + suploader.subject_uploadscans(s, uploaddir, elabel, visitid)
                # mark or move folder if done
                if ctr > 0 and donepath:
                    try:
                        shutil.move(join(scandir, slabel), donepath)
                        message = "Uploaded scans moved to %s" % donepath
                        logging.info(message)
                        print(message)
                    except IOError:
                        message = "Error in moving uploaded scans to %s" % donepath
                        logging.warning(message)
                        print(message)
            else:
                logging.warning("Subject doesn't exist in this project: %s %s", projectcode, sid)
        return ctr

    def delete_subjects_all(self, projectcode):
        """
        Removes all subjects from a project
        """
        project = self.get_project(projectcode)
        subj = self.get_subjects(projectcode)
        for s in subj:
            sid = s.id()
            print("Deleting:", s.label(), " ID=", sid)
            project.subject(sid).delete()
            if project.subject(sid).exists():
                print("ERROR: Couldn't delete ID=", sid)

    def delete_experiments(self, projectcode, datatype, fields):
        """
        Removes experiments with corresponding field-values
        """
        # expts = self.conn.inspect.experiment_values(datatype, projectcode)
        project = self.get_project(projectcode)
        row = datatype
        for field in fields:
            fieldref = datatype + '/' + field
            columns = [datatype + '/SUBJECT_ID', datatype + '/ID', fieldref]
            criteria = [(fieldref, 'LIKE', fields[field]),
                        'AND'
                        ]
            self.conn.manage.search.save('deleting', row, columns, criteria)  # save search
            elist = self.conn.manage.search.get('deleting')  # run search
            print(datatype, " Expts to delete:", len(elist))
            for e in elist:
                print(e)
                expt = project.experiment(e['expt_id'])
                expt.delete()
                if (project.experiment(e['expt_id']).exists()):
                    print("ERROR: Couldn't delete Expt ID=", e['expt_id'])
                else:
                    print("DELETED:", e['expt_id'])
            xnat.conn.manage.search.delete('deleting')  # remove saved search


############################################################################################
if __name__ == "__main__":
    # get current user's login details (linux) or local file (windows)
    home = expanduser("~")
    configfile = join(home, '.xnat.cfg')
    parser = argparse.ArgumentParser(prog='XnatConnector',
                                     description='''\
        XnatConnector: Script for managing data in QBI XNAT db
         ''')
    parser.add_argument('database', help='select database to connect to [qbixnat|irc5xnat]')
    parser.add_argument('projectcode', help='select project by code eg QBICC')
    parser.add_argument('--p', action='store_true', help='list projects')
    parser.add_argument('--s', action='store_true', help='list subjects')
    parser.add_argument('--x', action='store_true', help='delete subjects')
    parser.add_argument('--m', action='store_true', help='delete experiments (opex,aborted)')
    parser.add_argument('--c1', action='store', help='change expt label from')
    parser.add_argument('--c2', action='store', help='change expt label to')
    parser.add_argument('--counts', action='store_true', help='Get experiment counts for subjects')
    parser.add_argument('--config', action='store', help='database configuration file (overrides ~/.xnat.cfg)')
    # Tests
    # args = parser.parse_args(['xnat-dev', 'TEST_PJ00', '--p']) #Preset
    args = parser.parse_args()
    print(args)
    xnat = XnatConnector(configfile, args.database)
    print("Connecting to URL=", xnat.url)
    xnat.connect()
    if (xnat.conn):
        print("...Connected")
        try:
            projectcode = args.projectcode  # "QBICC"
            if (args.x is not None and args.x):
                xnat.delete_subjects_all(projectcode)

            if (args.s is not None and args.s):
                xnat.list_subjects_all(projectcode)

            if (args.p is not None and args.p):
                projlist = xnat.list_projects()
                for p in projlist:
                    print("Project: ", p.id())

            if (args.c1 is not None and args.c2 is not None):
                xnat.changeExptLabel(projectcode, args.c1, args.c2)

            if (args.m is not None and args.m):
                etypes = sorted(xnat.conn.inspect.datatypes())
                print(etypes)
                for dtype in ['opex:bloodCobasData']:
                    xnat.delete_experiments(projectcode, dtype,
                                            {'sample_quality': 'UNKNOWN'})  # 'status': 'SYSTEM_ERROR'
                    # for dtype in ['opex:cantabDMS','opex:cantabERT','opex:cantabMOT','opex:cantabPAL','opex:cantabSWM']:
                    #     xnat.delete_experiments(projectcode,dtype,{'status': 'COMPLETED'}) # 'status': 'SYSTEM_ERROR'
        except ValueError as e:
            print("Error:", e)

        finally:
            xnat.conn.disconnect()
            print("FINISHED")

    else:
        print("Failed to connect")
