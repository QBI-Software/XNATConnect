import unittest2 as unittest
from os.path import join, expanduser
from xnatconnect.XnatConnector import XnatConnector


class TestConnector(unittest.TestCase):
    '''
    Tests require a test XNAT instance to connect to with:
    1. Login details in a file in the user home directory (.xnat.cfg)
    2. Configuration name of the server to use for login
    3. A project ID with subject as sampledata to test access
    '''
    def setUp(self):
        configfile=join(expanduser('~'),'.xnat.cfg')
        server = 'xnat-dev'
        self.projectcode='TEST'
        self.xnat = XnatConnector(configfile, server)
        self.xnat.connect()
        if not self.xnat.conn:
            self.skipTest("Database not connecting")

    def tearDown(self):
        self.xnat.conn.disconnect()

    def test_get_project(self):
        projectcode = self.projectcode
        proj = self.xnat.get_project(projectcode)
        self.assertIsNotNone(proj, "Project not found")
        self.assertEqual(projectcode,proj.id(),"Project code is not equal")

    def test_get_projectPI(self):
        projectcode = self.projectcode
        proj = self.xnat.get_projectPI(projectcode)
        lastname='Einstein'
        self.assertIsNotNone(proj, "Project PI not found")
        self.assertEqual(lastname, proj, "Project code is not equal")

    def test_get_subjectbylabel(self):
        projectcode = self.projectcode
        subjectlabel = 'S0001'
        subjectid = 'IRC5XNAT_S00001'
        sid = self.xnat.get_subjectid_bylabel(projectcode,subjectlabel)
        self.assertIsNotNone(sid, "Subject ID not found")
        self.assertEqual(sid, subjectid, "Subject id is not equal")


if __name__ == '__main__':
    unittest.main()
