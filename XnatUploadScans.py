# -*- coding: utf-8 -*-
"""
XNAT Utility script: Upload scans via subject
where scans are loaded from structure as follows:
/project_id/subject_label/scans/group/session_type/
eg. /QBICC/1450001/scans/1/DICOM/*.dcm

http://xnat.qbi.uq.edu.au:8080/qbixnat/data/experiments/QBIXNAT_E00010/scans/4/resources/DICOM/files?format=zip&subjectIncludedInPath=true&structure=simplified


Created on Thu Feb 23 10:58:21 2017

@author: uqecoop2
"""
import os
import sys
import time
import datetime
from os import listdir
from os.path import isfile, isdir, join
from os.path import expanduser
from subprocess import Popen, call
import multiprocessing as mp
import pyxnat
import ConfigParser
import argparse
import csv
import glob
from collections import OrderedDict
import warnings

warnings.filterwarnings("ignore")


class XnatConnector:
    def __init__(self, configfile, sitename):
        config = ConfigParser.RawConfigParser()
        config.read(configfile)
        self.url = config.get(sitename, "URL")
        self.user = config.get(sitename, "USER")
        self.passwd = config.get(sitename, "PASS")
        # print "Config:", self.url , ", ", self.user, ", ", self.passwd

    def connect(self):
        """
        Connect to xnat server via config
        """
        self.conn = pyxnat.Interface(server=self.url, user=self.user, verify=False,
                                     password=self.passwd, cachedir='/tmp')  # connection object

    def get_project(self, projectcode):
        if not self.conn:
            self.connect()
        qry_project = '/projects/%s' % projectcode
        return self.conn.select(qry_project)

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
        Lists all subjects in a project
        """

        subj = self.get_subjects(projectcode)
        outfilename = projectcode + 'subjectlist.csv'
        with open(outfilename, 'wb') as csvfile:
            fieldnames = ['ID', 'subject_ID']
            mywriter = csv.DictWriter(csvfile, fieldnames=fieldnames)
            mywriter.writeheader()
            for s in subj:
                print "ID=", s.label(), ",SubjectID=", s.id()  # xnat subject id eg XNAT_S00006
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
            print "Found subject=", s.label()
            return s.id()
        else:
            print "Subject not found"

    def checkUniqueLabel(self, subject, label):
        # columns = ['xnat:experimentData/LABEL']
        # criteria = [('xnat:experimentData/LABEL', '=', label)]
        # expts = self.conn.select('xnat:experimentData', columns).where(criteria)
        print "checking label is unique: ", label
        experiments = self.conn.select('//subjects/' + subject.id() + '/experiments')
        expts = [e for e in experiments if e.datatype() == 'xnat:mrSessionData']

        # expts = subject.experiments() #self.conn.select('//experiments')
        prefix = label.rsplit('_', 1)[0]
        labels = [e.label() for e in expts if e.id() is not None and e.label().startswith(prefix)]
        if label in labels:
            labels.sort(reverse=True)  # in-place sort
            ctr = labels[0].rsplit('_', 1)[1]
            c = int(ctr) + 1
            label = prefix + "_" + str(c)
            print "updating label number:", label
        return label

    def find_next_experimentID(self, projectcode, prefix='XNAT', exptid=True):
        """
        Find the max experiment ID or label from the database given a prefix
        exptid = True (find ID)
        exptid = False (find label)
        """
        # import re
        # p = re.compile(prefix)
        # project = self.get_project(projectcode)
        # eargs = [('xnat:subjectData/PROJECT', '=', projectcode)]
        expts = self.conn.select('//experiments')  # .where(eargs)
        eids = OrderedDict()
        for e in expts:
            #    print "expt=", e.label(), ' ', e.datatype(), ' ', e.id()

            if (exptid and e.id() is not None and e.id().startswith(prefix)):
                eids[e.id()] = e.label()
            elif (not exptid and e.id() is not None and e.label().startswith(prefix)):
                eids[e.label()] = e.id()
        if len(eids.keys()) > 0:
            maxid = eids.keys()[-1]
            maxlabel = eids[maxid]
        else:
            maxid = 0
            maxlabel = 0

        return [maxid, maxlabel]

    # def upload_folder(resource_obj, fpath):
    #     """
    #     Method to upload a folder to a resource
    #     :param resource_obj: resource object to upload snapshots to
    #     :param fpath: path to the folder to upload
    #     :return: None
    #     """
    #     # check all the files if one exist at least:
    #     if check_folder_resources(resource_obj, fpath):
    #         LOGGER.info('     - WARNING: files in resource already found on XNAT. Use --force to upload this file.')
    #     else:
    #         if not resource_obj.exists(): resource_obj.create()
    #         filename_zip = resource_obj.label() + '.zip'
    #         init_dir = os.getcwd()
    #         # Zip all the files in the directory
    #         os.chdir(fpath)
    #         os.system('zip -r %s * > /dev/null' % (filename_zip))
    #         # upload
    #         LOGGER.info('     - Folder %s: uploading folder...' % (fpath))
    #         resource_obj.put_zip(os.path.join(fpath, filename_zip), overwrite=True, extract=OPTIONS.extract)
    #         # remove the tmp zip file:
    #         if os.path.exists(os.path.join(fpath, filename_zip)):
    #             os.remove(os.path.join(fpath, filename_zip))
    #         # return to the initial directory:
    #         os.chdir(init_dir)

    def upload_MRIscans(self, projectcode, scandir):
        """
        Upload MRI scans from scandir to project where foldername is subject label
        https://xnat-devel.qbi.uq.edu.au:8443/irc5xnat/data/projects/QBICC/subjects/IRC5XNAT_S00001/experiments/MR_1450001_1/scans/sks45b.dcm?xsiType=xnat:mrScanData&inbody=false
        """
        project = self.get_project(projectcode)
        prefix = 'IRC5XNAT'  # get this by lookup
        ctr = 0
        scanfiles = [f for f in listdir(scandir) if os.path.isdir(join(scandir, f))]
        for slabel in scanfiles:
            sid = self.get_subjectid_bylabel(projectcode, slabel)
            if sid is None:
                print "Subject doesn't exist - skipping %s" % slabel
                continue
            s = project.subject(sid)
            uid = time.time()  # unique timestamp for each subject

            if s.exists():
                ctr = ctr + 1
                print "Uploading scans to ", s.id(), ": ", s.label()
                # eid = self.find_next_experimentID(projectcode, prefix,True)
                elabel = 'MR_%s_%d' % (s.label(), ctr)  # self.find_next_experimentID(projectcode, prefix,True)
                elabel = self.checkUniqueLabel(s, elabel)
                expt = s.experiment(elabel)
                #print "Before create: ", expt.exists()
                expt.create(experiments='xnat:mrSessionData')
                #print "After create: ", expt.exists()
                uploaddir = join(scandir, slabel, 'scans')
                scantype = 'DICOM'
                fileext = '*.*'
                scan_ctr = 0
                for subdr in listdir(uploaddir):
                    scan_ctr += 1
                    dcm_path = join(scandir, slabel, 'scans', subdr)
                    scan = expt.scan(subdr) # The scan ID you chose when creating the scan in XNAT matches the Series instance number in the dicom.
                    scan.create(scans='xnat:mrScanData')
                    dicom_resource = scan.resource('DCM')
                    dicom_resource.put_dir(dcm_path,overwrite=True, extract=True)
                    dicom_files = dicom_resource.files()
                    print "Files=", dicom_files
                    #expt.pull_data_from_headers()

                    ######Update from scan - IMPORTANT #########:
                    # The scan ID you chose when creating the scan in XNAT matches the Series instance number in the dicom.
                    # The scan modality you created matches what XNAT would have created for the kind of data you are pushing up.
                    # I think if you’ve done that, it should work fine.  After uploading all of your DICOM to the scan, issue this PUT command.
                    # /REST/experiments/ID/scans/ID?pullDataFromHeaders=true
                    # That command should review the files and populate the scan metadata accordingly.
                    # You can also perform this operation at the session level (/REST/projects/ID/subjects/ID/experiments/ID?pullDataFromHeaders=true).  But, that will regenerate the metadata for all of the scans and session level.  If you are only adding a subset of scans, you are probably best of doing it scan by scan.

                    #dcm_dir = glob.glob(join(dcm_path, fileext))
                    # for dcm in dcm_dir:
                    #     #scan_name = dcm.split('-')[-1]  # extract short version of filename
                    #     scan_name = os.path.basename(dcm) #filename only
                    #     scan = expt.scan(str(scan_ctr))
                    #     #scan = expt.scan(subdr)
                    #     # scan.create(scans='xnat:mrScanData')
                    #     # scan.attrs.mset({
                    #     #     'xnat:mrScanData/series_description': subdr,
                    #     #     'xnat:mrScanData/quality': 'good'
                    #     # })
                    #
                    #     scan.resource(scantype).file(scan_name).insert(dcm, overwrite='true', inbody='false',
                    #                                                 format=scantype, content='RAW')
                    #     print("Loading scan: ", scan_name)
                    #         #scan.attrs.mget(['xnat:mrScanData/ID', 'xnat:mrScanData/image_session_ID', 'xnat:mrScanData/type']))


                # Update headers after files uploaded
                if expt.scans():
                    expt.trigger(fix_types=True, scan_headers=True, pipelines=True)
                    #expt.pull_data_from_headers()
                    #expt.fix_scan_types()  # will replace if matching dictionary set up under Project->Actions->Scantypes
                    # Get folder creation
                    expt_creation = datetime.datetime.fromtimestamp(os.stat(scandir).st_mtime)
                    expt_creation_date = expt_creation.strftime("%Y%m%d")
                    expt_creation_time = expt_creation.strftime("%H:%M:%S")
                    expt.attrs.set('xnat:experimentData/date', expt_creation_date)
                    expt.attrs.set('xnat:experimentData/time', expt_creation_time)
                    # This should create thumbnails
                    #expt.trigger_pipelines()
                    # Check valid data??
            else:
                print "Subject doesn't exist in this project: %s %s" % (projectcode, sid)

        return ctr


# =============================================================================

if __name__ == "__main__":
    # get current user's login details (linux) or local file (windows)

    home = expanduser("~")
    configfile = join(home, '.xnat.txt')
    parser = argparse.ArgumentParser(prog='XnatUploadScans',
                                     description='''\
        Script for uploading scans to QBI XNAT db
         ''')
    parser.add_argument('database', action='store', help='select database to connect to [qbixnat|irc5xnat]')
    parser.add_argument('projectcode', action='store', help='select project by code eg QBICC')
    parser.add_argument('--p', action='store_true', help='list projects')
    parser.add_argument('--s', action='store_true', help='list subjects')
    parser.add_argument('--g', action='store', help='get XNAT ID for subject ID')
    parser.add_argument('--f', action='store', help='find next experiment ID with this prefix (default XNAT)')
    parser.add_argument('--u', action='store',
                        help='Upload MRI scans from directory as data/subject_label/scans/session_label/DICOM')

    # TEST args
    server = 'irc5xnat-dev' #'irc5xnat'
    projectcode ='QBICC' #'TEST_PJ01'
    # tests = {'All projects': [server, projectcode, '--p'],
    #          'All subjects': [server, projectcode, '--s'],
    #          'Subject 1450001': [server, projectcode, '--g', '1450001'],
    #          'XNATID for 1450001': [server, projectcode, '--g', '1450001'],
    #          'Last expt ID': [server, projectcode, '--f', 'IRC5XNAT'],
    #          }
    tests = {'Upload scans by Label': [server, projectcode, '--u', 'D:\\Projects\\XNAT\\data'], }

    print "Server:%s Project:%s" % (server, projectcode)
    for key, arglist in tests.items():
        print(key)
        args = parser.parse_args(arglist)

        xnat = XnatConnector(configfile, args.database)
        # print "Connecting to URL=", xnat.url
        xnat.connect()
        if (xnat.conn):
            # print "...Connected"

            projectcode = args.projectcode  # "QBICC"
            if (args.s is not None and args.s):
                xnat.list_subjects_all(projectcode)
            if (args.p is not None and args.p):
                xnat.list_projects()
            if (args.g is not None and args.g):
                subjectid = args.g
                sid = xnat.get_subjectid_bylabel(projectcode, subjectid)
                print "XNAT ID=%s for subject ID=%s" % (sid, subjectid)
            if (args.f is not None and args.f):
                idprefix = args.f  # 'IRC5XNAT'
                fid = xnat.find_next_experimentID(projectcode, idprefix, True)
                print "Last EXPT ID=", fid
            if (args.u is not None and args.u):
                uploaddir = args.u  # Top level DIR FOR SCANS
                # Directory structure data/subject_label/scans/session_label/DICOM
                if isdir(uploaddir):
                    fid = xnat.upload_MRIscans(projectcode, uploaddir)
                    print "Subject sessions uploaded: ", fid
                else:
                    print "Directory path cannot be found"

            xnat.conn.disconnect()

        else:
            print "Failed to connect"
