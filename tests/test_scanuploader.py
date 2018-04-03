import unittest2 as unittest
from os.path import join, expanduser, isdir, basename
from os import listdir
from datetime import datetime
from xnatconnect.XnatConnector import XnatConnector
from xnatconnect.XnatUploadScans import ScanUploader


class TestScanUploader(unittest.TestCase):
    '''
    Tests require a test XNAT instance to connect to with:
    1. Login details in a file in the user home directory (.xnat.cfg)
    2. Configuration name of the server to use for login
    3. A project ID with subject as sampledata to test access
    '''
    def setUp(self):
        """
        Requires MRI scans to upload to test XNAT instance
        :return:
        """
        scandir="D:\\Projects\\XNAT\\data\\S1\\scans\\3"
        self.seriesnum = basename(scandir)
        scanfiles = [f for f in listdir(scandir) if not isdir(join(scandir, f))]
        if len(scanfiles) > 0:
            self.dicomfile=join(scandir,scanfiles[0])
        else:
            self.skipTest('No DICOM test files found')



    def tearDown(self):
        print('Done')

    def test_getScanType(self):
        scanuploader = ScanUploader()
        type = scanuploader.getScanType(scanuploader.default_scantype, self.dicomfile)
        self.assertEqual(type, scanuploader.default_scantype, "Scan type not default")

    def test_getModality(self):
        scanuploader = ScanUploader()
        type = scanuploader.getModality(self.dicomfile)
        self.assertIsNotNone(type, 'Modality is none')

    def test_getSeriesNumber(self):
        scanuploader = ScanUploader()
        type = scanuploader.getSeriesNumber(self.seriesnum,self.dicomfile)
        self.assertIsNotNone(type, 'SeriesNumber is none')
        self.assertEqual(int(type), int(self.seriesnum), 'Series number not matching')

    def test_getSeriesDatestamp(self):
        scanuploader = ScanUploader()
        do = scanuploader.getSeriesDatestamp(self.dicomfile)
        self.assertIsNotNone(do, 'Date is none')
        self.assertIsInstance(do, datetime, 'Date is not datetime instance')

    def testUpload(self):
        '''
        Will upload scan series - so don't run this often
        :return:
        '''
        configfile = join(expanduser('~'), '.xnat.cfg')
        server = 'xnat-dev'
        self.xnat = XnatConnector(configfile, server)
        self.xnat.connect()
        if not self.xnat.conn:
            self.skipTest("Database not connecting")



if __name__ == '__main__':
    unittest.main()
