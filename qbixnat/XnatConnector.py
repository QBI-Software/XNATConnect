# -*- coding: utf-8 -*-
"""
XNAT connector class for scripts

@author: Liz Cooper-Williams, QBI
"""
import argparse
import csv
import glob
import logging
import os
import shutil
import warnings
from os import listdir
from os.path import expanduser
from os.path import join

import datetime
import dicom
import pyxnat
from configobj import ConfigObj

warnings.filterwarnings("ignore")
DEBUG = 1


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

    def list_subjects_all(self, projectcode):
        """
        Lists all subjects in a project to console
        """

        subj = self.get_subjects(projectcode)
        outfilename = projectcode + 'subjectlist.csv'
        with open(outfilename, 'wb') as csvfile:
            fieldnames = ['ID', 'subject_ID']
            mywriter = csv.DictWriter(csvfile, fieldnames=fieldnames)
            mywriter.writeheader()
            for s in subj:
                print("ID=", s.label(), ",SubjectID=", s.id())  # xnat subject id eg XNAT_S00006
                mywriter.writerow({'ID': s.label(), 'subject_ID': s.id()})
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

    def createSubject(self,projectcode,label, subjectkwargs):
        """
        Create a subject in this project with the label as ID and subject parameters as key value
        No checks made on args eg {'dob': '1949-11-06', 'gender': 'female'}
        """
        project = self.get_project(projectcode)
        subject = project.subject(label)
        subject.create()
        if subject.exists():
            #set attrs
            subject.attrs.mset(subjectkwargs)
            return subject
        else:
            logging.warning("Subject not created: %s", label)
            return None

    def createExperiment(self,subject,xsdtype,exptid,exptdata):
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
            expt = subject.experiment(exptid).create(experiments=xsdtype)
            if xsdtype + '/date' in exptdata:
                expt_creation = datetime.datetime.strptime(exptdata[xsdtype + '/date'],"%Y.%m.%d %H:%M:%S")
                del exptdata[xsdtype + '/date']
            else:
                expt_creation = datetime.datetime.now()
            expt_creation_date = expt_creation.strftime("%Y%m%d")
            expt_creation_time = expt_creation.strftime("%H:%M:%S")
            expt.attrs.set('xnat:experimentData/date', expt_creation_date)
            expt.attrs.set('xnat:experimentData/time', expt_creation_time)
            #Add attributes
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

    def upload_MRIscans(self, projectcode, scandir):
        """
        Upload MRI scans from scandir to project
        :param projectcode: XNAT ID for project eg QBICC
        :param scandir: full path name of dir containing subdirs with data
        eg /ibscratch/irc5scans/data
        data should be organized by DICOM series as: data/subject_label/scans/series_number/*.dcm (or *.IMA)
        :return: number of sessions loaded
        """
        project = self.get_project(projectcode)
        owners = project.owners()
        proj_pi = self.get_projectPI(projectcode)
        ctr = 0
        default_scantype = 'MR Image Storage'
        #load
        scanfiles = [f for f in listdir(scandir) if os.path.isdir(join(scandir, f))]
        if scanfiles:
            dirpath = os.path.dirname(scandir)
            donepath = join(dirpath, 'done')
            if not os.path.isdir(donepath):
                try:
                    os.mkdir(donepath)
                except:
                    raise OSError

        for slabel in scanfiles:
            sid = self.get_subjectid_bylabel(projectcode, slabel)
            if sid is None:
                logging.warning("Subject doesn't exist - skipping %s", slabel)
                continue
            s = project.subject(sid)

            if s.exists():
                ctr = ctr + 1
                # Set experiment
                elabel = 'MR_%s_%d' % (s.label(), ctr)
                elabel = self.checkUniqueLabel(s, elabel)  # eid = self.find_next_experimentID(projectcode, prefix,True)
                message = "Uploading scans for %s: %s with expt=%s" % (s.id(), s.label(), elabel)
                logging.info(message)
                print(message)
                expt = s.experiment(elabel)
                expt.create()  # experiments='xnat:mrSessionData')
                uploaddir = join(scandir, slabel, 'scans')
                scan_ctr = 0
                # (scan_date, scan_time) = (None, None)
                others = {}
                for subdr in listdir(uploaddir):
                    dcm_path = join(uploaddir, subdr)
                    scan_files = glob.glob(join(dcm_path, '*.*'))
                    if len(scan_files) == 0:  # check this isn't wrong dir
                        logging.warning("File directory doesn't contain dcm files:%s", uploaddir)
                        continue

                    scan_type = self.getScanType(default_scantype, scan_files[0])
                    scan_id = self.getSeriesNumber(subdr, scan_files[0])
                    scan_pi = self.getPI(scan_files[0])
                    print('Scan ID:', scan_id, 'Scan type=', scan_type, 'Scan info=',scan_pi)
                    # (scan_date, scan_time) = self.getSeriesDatestamp(scan_files[0])
                    scan_ctr += 1
                    scan = expt.scan(str(scan_id))
                    # Refer to scan types in DICOMSOP.csv
                    if scan_type == 'MR Image Storage' or '1.2.840.10008.5.1.4.1.1.4' in scan_type:
                        scan.create(scans='xnat:mrScanData')
                        logging.info("Scan created[%s]:  MR Image Storage [%s] - %s", scan_id, scan_type, scan_pi)
                    elif scan_type == 'Secondary Capture Image Storage' or '1.2.840.10008.5.1.4.1.1.7' in scan_type:
                        scan.create(scans='xnat:scScanData')
                        logging.info("Scan created[%s]:  Secondary Capture Image Storage [%s] - %s", scan_id, scan_type, scan_pi)
                    else:
                        modality = self.getModality(scan_files[0])
                        if modality is not None and modality == 'MR':
                            scan.create(scans='xnat:otherDicomScanData')
                            logging.info("Scan created[%s]:  Other DICOM [%s] - %s", scan_id, scan_type, scan_pi)

                    dicom_resource = scan.resource('DICOM')  # crucial for display DICOM headers
                    dicom_resource.put_dir(dcm_path, overwrite=True, extract=True)
                    # Update per scan doesn't work:
                    ## hdrs = '/REST/experiments/%s/scans/%s?pullDataFromHeaders=true' % (elabel, str(scan_id))
                    # xnat.conn.put(hdrs)

                # Update headers after files uploaded (mrScan only)
                if expt.scans():
                    # expt.trigger(fix_types=True, scan_headers=True, pipelines=True) - doesn't work properly as calls are in wrong order so list each function as below
                    try:
                        expt.pull_data_from_headers()
                    except:
                        message = "Unable to extract header data from this xsi type: %s" % scan_type
                        logging.warning(message)
                    expt.fix_scan_types()
                    expt.trigger_pipelines()
                    # mark or move folder if done
                    if donepath:
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

    def getScanType(self, dirlabel, dicomfile):
        type = dirlabel
        dcm = dicom.read_file(dicomfile)
        if dcm:
            type = dcm.SOPClassUID #see references at http://dicomlookup.com/dicom-sop.asp

        return type

    def getModality(self, dicomfile):
        type = None
        dcm = dicom.read_file(dicomfile)
        if dcm:
            type = dcm.Modality

        return type

    def getSeriesNumber(self, dirlabel, dicomfile):
        series = dirlabel
        dcm = dicom.read_file(dicomfile)
        if dcm:
            series = dcm.SeriesNumber

        return series

    def getSeriesDatestamp(self, dicomfile):
        sdate = None
        stime = None
        dcm = dicom.read_file(dicomfile)
        if dcm:
            sdate = dcm.SeriesDate
            stime = dcm.SeriesTime

        return (sdate, stime)

    def getPI(self, dicomfile):
        pi = None
        dcm = dicom.read_file(dicomfile)
        if dcm:
            pi = dcm.RequestedProcedureDescription  # check this field is set with Principal Investigator
        return pi

    def delete_subjects_all(self,projectcode):
        """
        Removes all subjects from a project
        """
        project = self.get_project(projectcode)
        subj = self.get_subjects(projectcode)
        for s in subj:
            sid = s.id()
            print "Deleting:", s.label()," ID=",sid
            project.subject(sid).delete()
            if project.subject(sid).exists():
                print "ERROR: Couldn't delete ID=", sid

############################################################################################
if __name__ == "__main__":
    # get current user's login details (linux) or local file (windows)
    home = expanduser("~")
    configfile = join(home, '.xnat.cfg')
    parser = argparse.ArgumentParser(prog='qbixnat_manager',
        description='''\
        XnatConnector: Script for managing data in QBI XNAT db
         ''')
    parser.add_argument('database', help='select database to connect to [qbixnat|irc5xnat]')
    parser.add_argument('projectcode', help='select project by code eg QBICC')
    parser.add_argument('--p', action='store_true', help='list projects')
    parser.add_argument('--s', action='store_true', help='list subjects')
    parser.add_argument('--x', action='store_true', help='delete subjects')
    #Tests
    args = parser.parse_args(['xnat-dev', 'TEST_PJ00', '--p']) #Preset

    print args
    xnat = XnatConnector(configfile, args.database)
    print "Connecting to URL=", xnat.url
    xnat.connect()
    if (xnat.conn):
        print "...Connected"
        # EXAMPLE -
        projectcode = args.projectcode  # "QBICC"
        if (args.x is not None and args.x):
            xnat.delete_subjects_all(projectcode)

        if (args.s is not None and args.s):
            xnat.list_subjects_all(projectcode)

        if (args.p is not None and args.p):
            projlist = xnat.list_projects()
            for p in projlist:
                print "Project: ", p.id()


        xnat.conn.disconnect()
        print("FINISHED")

    else:
        print "Failed to connect"