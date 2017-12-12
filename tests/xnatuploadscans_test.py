import unittest
from XnatUploadScans import XnatConnector


class TestXnatUploadScans(unittest.TestCase):
    def setUp(self):
        configfile='xnat.cfg'
        server = 'irc5xnat-dev'

        self.xnat = XnatConnector(configfile, server)
        self.xnat.connect()
        if not self.xnat.conn:
            self.skipTest("Database not connecting")

    def tearDown(self):
        self.xnat.conn.disconnect()


    def test_get_project(self):
        projectcode = 'QBICC'
        proj = self.xnat.get_project(projectcode)
        self.assertIsNotNone(proj, "Project not found")
        self.assertEqual(projectcode,proj.id(),"Project code is not equal")

    def test_get_subjectbylabel(self):
        projectcode = 'QBICC'
        subjectlabel = '1450001'
        subjectid = 'IRC5XNAT_S00001'
        sid = self.xnat.get_subjectid_bylabel(projectcode,subjectlabel)
        self.assertIsNotNone(sid, "Subject ID not found")
        self.assertEqual(sid, subjectid, "Subject id is not equal")


if __name__ == '__main__':
    unittest.main()
