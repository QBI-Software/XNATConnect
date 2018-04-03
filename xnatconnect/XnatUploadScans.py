# -*- coding: utf-8 -*-
"""
XNAT scan upload:
Upload scans via subject label (or XNAT id)
where scans are loaded from structure as follows:
/project_id/subject_label/scans/group/session_type/

DICOM FILE FORMATS: dcm or Siemens IMA

@author: Liz Cooper-Williams, QBI
"""
import glob
import logging
import warnings
from os import listdir
from os.path import join
from datetime import datetime

import pydicom as dicom

warnings.filterwarnings("ignore")


class ScanUploader:
    def __init__(self, project_investigator=None):
        self.default_scantype = 'MR Image Storage'
        self.proj_pi = project_investigator

    def subject_uploadscans(self, xnatsubject, uploaddir, exptlabel, visitid=None):
        """
        Main method for uploading scans for a subject. This ensures image is of correct type and metadata is inserted
        :param xnatsubject: Subject object from pyxnat
        :param uploaddir: scans directory containing DICOMS
        :param exptlabel: experiment ID for MR session
        :param visitid: (optional) Further information on which visit (longitudinal studies)
        :return: number of scans loaded or 0 if failed
        """
        expt = xnatsubject.experiment(exptlabel)
        expt.create()  # experiments='xnat:mrSessionData')
        if visitid is not None:
            expt.attrs.set('xnat:mrSessionData/visit_id', str(visitid))

        scan_ctr = 0
        # (scan_date, scan_time) = (None, None)
        others = {}
        for subdr in listdir(uploaddir):
            dcm_path = join(uploaddir, subdr)
            scan_files = glob.glob(join(dcm_path, '*.*'))
            if len(scan_files) == 0:  # check this isn't wrong dir
                logging.warning("File directory doesn't contain dcm files:%s", uploaddir)
                continue

            scan_type = self.getScanType(self.default_scantype, scan_files[0])
            scan_id = self.getSeriesNumber(subdr, scan_files[0])
            print('Scan ID: %s  Scan type=%s' % (scan_id, scan_type))

            scan_pi = self.getPI(scan_files[0])
            if self.proj_pi is not None:
                if self.proj_pi in scan_pi:
                    message = "Owner verified:  scan=%s project=%s" % (scan_pi, self.proj_pi)
                    logging.info(message)
                else:
                    message = "Owner does not match - skipping upload: scan=%s project=" % (scan_pi, self.proj_pi)
                    logging.warning(message)
                    continue
            # (scan_date, scan_time) = self.getSeriesDatestamp(scan_files[0])

            scan = expt.scan(str(scan_id))
            # scan.insert() #Should detect type BUT IT DOESN'T
            if scan_type == 'MR Image Storage' or '1.2.840.10008.5.1.4.1.1.4' in scan_type:
                scan.create(scans='xnat:mrScanData')
                scan_ctr += 1
                logging.info("Scan created[%s]:  MR Image Storage [%s] - %s", scan_id, scan_type, scan_pi)
            elif scan_type == 'Secondary Capture Image Storage' or '1.2.840.10008.5.1.4.1.1.7' in scan_type:
                scan.create(scans='xnat:scScanData')
                scan_ctr += 1
                logging.info("Scan created[%s]:  Secondary Capture Image Storage [%s] - %s", scan_id, scan_type,
                             scan_pi)
            else:
                modality = self.getModality(scan_files[0])
                if modality is not None and modality == 'MR':
                    scan.create(scans='xnat:otherDicomScanData')
                    scan_ctr += 1
                    logging.info("Scan created[%s]:  Other DICOM [%s] - %s", scan_id, scan_type, scan_pi)

            dicom_resource = scan.resource('DICOM')  # crucial for display DICOM headers
            dicom_resource.put_dir(dcm_path, overwrite=True, extract=True)

        # Update headers after files uploaded (mrScan only)
        if expt.scans():
            # expt.trigger(fix_types=True, scan_headers=True, pipelines=True) - doesn't work properly as calls are in wrong order so list each function as below
            try:
                expt.pull_data_from_headers()
                expt.fix_scan_types()
                expt.trigger_pipelines()

            except:
                message = "Unable to extract header data from this xsi type: %s" % scan_type
                logging.warning(message)

        return scan_ctr

    def getScanType(self, dirlabel, dicomfile):
        type = dirlabel
        dcm = dicom.read_file(dicomfile)
        if dcm:
            type = dcm.SOPClassUID

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
        """
        Get date and time from dicom
        :param dicomfile:
        :return: datetime object
        """
        do = None
        dcm = dicom.read_file(dicomfile)
        if dcm:
            sdate = dcm.SeriesDate
            stime = dcm.SeriesTime
            do = datetime.strptime(sdate + ' ' + stime.split('.')[0], '%Y%m%d %H%M%S')
        return do

    def getPI(self, dicomfile):
        pi = None
        dcm = dicom.read_file(dicomfile)
        if dcm:
            pi = dcm.RequestedProcedureDescription  # check this field is set with Principal Investigator
        return pi

# =============================================================================
