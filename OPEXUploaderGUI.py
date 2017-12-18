import sys
import logging
import os
import wx

import subprocess
from os.path import isdir, join, expanduser
from os import access, R_OK, walk, mkdir
from qbixnat.gui.noname import UploaderGUI, dlgScans,dlgConfig
from OPEXUploader import OPEXUploader
from configobj import ConfigObj
from requests.exceptions import ConnectionError
import argparse

class ConfigDialog(dlgConfig):
    def __init__(self, parent):
        super(ConfigDialog, self).__init__(parent)
        self.config= None

    def load(self, configfile):
        if access(configfile,R_OK):
            self.config = ConfigObj(configfile)
            self.chConfig.Clear()
            self.chConfig.AppendItems(self.config.keys())
            self.txtURL.Clear()
            self.txtUser.Clear()
            self.txtPass.Clear()

    def OnConfigText( self, event ):
        """
        Add new item
        :param event:
        :return:
        """
        if len(event.GetString()) > 0:
            ref=event.GetString()
            self.chConfig.AppendItems([ref])
            self.config[ref]== {'URL': '', 'USER': '', 'PASS': ''}
            self.txtURL.SetValue(self.config[ref]['URL'])
            self.txtUser.SetValue(self.config[ref]['USER'])
            self.txtPass.SetValue(self.config[ref]['PASS'])

    def OnConfigSelect( self, event ):
        """
        Select config ref and load fields
        :param event:
        :return:
        """
        ref = self.chConfig.GetStringSelection()
        if self.config is not None and ref in self.config.keys():
            self.txtURL.SetValue(self.config[ref]['URL'])
            self.txtUser.SetValue(self.config[ref]['USER'])
            self.txtPass.SetValue(self.config[ref]['PASS'])

    def OnLoadConfig( self, event ):
        """
        Load values from config file
        :param event:
        :return:
        """
        dlg = wx.FileDialog(self, "Choose a config file to load")
        if dlg.ShowModal() == wx.ID_OK:
            cfile = str(dlg.GetPath())
            self.load(cfile)
            print 'Config file loaded'
        dlg.Destroy()

    def OnSaveConfig( self, event ):
        """
        Save values to new or existing config
        :param event:
        :return:
        """
        if self.config is not None:
            self.config = ConfigObj(join(expanduser('~'),'.xnat.cfg'))
            url = self.txtURL.GetValue()
            user = self.txtUser.GetValue()
            passwd =self.txtPass.GetValue()
            self.config[self.chConfig.GetValue()] = {'URL': url, 'USER': user, 'PASS': passwd}
            self.config.write()
            print 'Config file updated'

        self.Close()

    def OnRemoveConfig( self, event ):
        """
        Remove selected ref
        :param event:
        :return:
        """
        ref = self.chConfig.GetStringSelection()
        if self.config is not None:
            del self.config[ref]
            self.config.write()
            print 'Config setting removed'
            self.load(configfile=self.config.filename)

class LogOutput():
    def __init__(self,aWxTextCtrl):
        self.out = aWxTextCtrl

    def write(self, string):
        self.out.WriteText(string)

class OPEXUploaderGUI(UploaderGUI):
    def __init__(self, parent):
        """
        Load from userhome/.xnat.cfg
        :param parent:
        """
        super(OPEXUploaderGUI, self).__init__(parent)
        self.SetTitle("XNAT Connector App")
        self.SetSize((850, 850))
        self.runoptions = self.__loadOptions()
        self.configfile = join(expanduser('~'), '.xnat.cfg')
        self.loaded = self.__loadConfig()
        if self.loaded:
            self.chOptions.SetItems(self.runoptions.keys())
        redir = LogOutput(self.tcResults)
        sys.stdout = redir
        sys.stderr = redir
        #print 'test'
        self.Show()

    def __loadConfig(self):
        if self.configfile is not None and access(self.configfile, R_OK):
            print("Loading config file")
            config = ConfigObj(self.configfile, encoding='UTF-8')

            return True
        else:
            raise IOError("Config file not accessible: %s", self.configfile)

    def __loadOptions(self):
        optionsfile = join('resources','run_options.cfg')
        config = ConfigObj(optionsfile)
        if 'options' in config:
            runoptions = config['options']
        else:
            runoptions = {'Help':'--h'}
        return runoptions

    def __loadCommand(self, options, report=0):
        """
        Load command for several scripts
        :param options:
        :param report:
        :return:
        """
        s = " "
        if report == 1:
            cwd = join(os.getcwd(), "qbixnat","report","OPEXReport.py")
        elif report == 2:
            cwd = join(os.getcwd(), "XnatOrganizeFiles.py")
        else:
            cwd = join(os.getcwd(), "OPEXUploader.py")
        if ('PYTHONEXE' in os.environ):
            pythoncmd = os.environ('PYTHONEXE')
        else:
            pythoncmd = sys.prefix + os.sep + "Scripts" + os.sep + "python.exe"

        cmd = pythoncmd + " " + cwd + " " + s.join(options)
        return cmd

    def __loadConnection(self):
        db = self.dbedit.GetValue()
        proj = self.projectedit.GetValue()
        if len(db) <= 0 and len(proj) <= 0:
            dlg = wx.MessageDialog(self, "Database or project configuration is empty or invalid", "Connection Config Error", wx.OK)
            dlg.ShowModal()
            dlg.Destroy()
            return (None, None)
        else:
            return (db,proj)

    def OnAbout(self, e):
        # A message dialog box with an OK button. wx.OK is a standard ID in wxWidgets.
        dlg = wx.MessageDialog(self, "Uploader for OPEX data to XNAT\n(c)2017 QBI Software", "About OPEX Uploader", wx.OK)
        dlg.ShowModal()  # Show it
        dlg.Destroy()  # finally destroy it when finished.

    def OnHelp(self,e):
        self.tcResults.Clear()
        cmd = self.__loadCommand(['--h'])
        try:
            output = subprocess.check_output(cmd, shell=True)
            self.tcResults.AppendText(output)
        except subprocess.CalledProcessError as e:
            msg = "Program Execution failed:" + e.message + "(" + str(e.returncode) + ")"
            print >> sys.stderr, msg
            self.tcResults.AppendText(msg)

    def OnTest(self,e):
        """
        Test connection is correctly configured
        :param e:
        :return:
        """
        self.tcResults.Clear()
        (db,proj) = self.__loadConnection()
        if db is None:
            return 0
        options = ['--projects', db, proj]
        cmd = self.__loadCommand(options)
        try:
            output = subprocess.check_output(cmd, shell=True)
            msg = "Connection to %s for project=%s\n" % (db,proj)
            self.tcResults.AppendText(msg)
            self.tcResults.AppendText(output)
        except subprocess.CalledProcessError as e:
            msg = "Program Execution failed:" + e.message + "(" + str(e.returncode) + ")"
            print >> sys.stderr, msg
            self.tcResults.AppendText(msg)

    def OnLaunch( self, event ):
        """
        Dialog for XnatScans organizer
        :param event:
        :return:
        """
        dlg = dlgScans(self)
        if dlg.ShowModal() == wx.ID_OK:
            scaninput = dlg.txtInputScans.GetPath()
            scanoutput = dlg.txtOutputScans.GetPath()
            ignore = dlg.txtIgnoreScans.GetPath()
            opexid = dlg.chkOPEX.GetValue()
            if len(scaninput)<=0 or len(scanoutput) <=0:
                dlg = wx.MessageDialog(self, "Please specify data directories", "Scan organizer", wx.OK)
                dlg.ShowModal()  # Show it
                dlg.Destroy()
            else:
                runoptions = ['--scandir','"'+scanoutput+'"']
                if opexid:
                    runoptions.append('--opexid')
                if len(ignore) > 0:
                    runoptions.append('--ignore')
                    runoptions.append('"'+ignore+'"')
                #compile options
                options = ['"'+scaninput+'"', " ".join(runoptions)]
                cmd = self.__loadCommand(options, 2)
                self.tcResults.AppendText(cmd)
                self.tcResults.AppendText("\n*******\n")
                try:
                    output = subprocess.check_output(cmd, shell=True)
                    self.tcResults.AppendText(output)
                    self.tcResults.AppendText("\n***FINISHED***\n")
                except subprocess.CalledProcessError as e:
                    retcode = e.returncode
                    if retcode < 0:
                        msg = "Program was terminated by signal [" + str(retcode) + "]"
                        print >> sys.stderr, msg
                    elif retcode == 1:
                        msg = "Program ran successfully [" + str(retcode) + "]"
                        print >> sys.stderr, msg
                    else:
                        msg = "Program error [" + str(retcode) + "] - check output"
                        print >> sys.stderr, msg
                    self.tcResults.AppendText(msg)

    def OnClose(self, e):
        self.Close(True)  # Close the frame.

    def OnOpen(self, e):
        """ Open a file"""
        #self.dirname = ''
        dlg = wx.DirDialog(self, "Choose a directory containing input files")
        if dlg.ShowModal() == wx.ID_OK:
            self.dirname = '"{0}"'.format(dlg.GetPath())
            self.dirname = dlg.GetPath()
            #self.StatusBar.SetStatusText("Loaded: %s\n" % self.dirname)
            self.inputedit.SetValue(self.dirname)
        dlg.Destroy()

    def OnEditDirname(self, event):
        self.dirname = '"{0}"'.format(event.GetString())
        self.dirname = event.GetString()
        #self.StatusBar.SetStatusText("Input dir: %s\n" % self.dirname)

    def OnDownload( self, event ):
        """
        Run downloads
        :param event:
        :return:
        """
        if self.dirname is None or len(self.dirname) <=0:
            dlg = wx.MessageDialog(self, "Please specify output directory", "OPEX Report", wx.OK)
            dlg.ShowModal()  # Show it
        else:
            msg = "Check output directory for downloads: %s" % self.dirname
            dlg = wx.MessageDialog(self,msg , "OPEX Report", wx.OK)
            if dlg.ShowModal() == wx.ID_OK:

                runoption =['--output', self.dirname]
                (db, proj) = self.__loadConnection()
                if db is None:
                    return 0
                options = [db, proj, " ".join(runoption) ]
                cmd = self.__loadCommand(options, 1)
                self.tcResults.AppendText(cmd)
                self.tcResults.AppendText("\n*******\n")
                try:
                    output = subprocess.check_output(cmd, shell=True)
                    self.tcResults.AppendText(output)
                    self.tcResults.AppendText("\n***FINISHED***\n")
                except subprocess.CalledProcessError as e:
                    retcode = e.returncode
                    if retcode < 0:
                        msg = "Program was terminated by signal [" + str(retcode) + "]"
                        print >> sys.stderr, msg
                    elif retcode == 1:
                        msg = "Program ran successfully [" + str(retcode) + "]"
                        print >> sys.stderr, msg
                    else:
                        msg = "Program error [" + str(retcode) + "] - check output"
                        print >> sys.stderr, msg
                    self.tcResults.AppendText(msg)

        dlg.Destroy()

    def OnSettings(self, event):
        """
        Configure database connection
        :param event:
        :return:
        """
        home = expanduser('~')
        configfile = join(home,'.xnat.cfg')
        dlg = ConfigDialog(self)
        dlg.load(configfile)
        dlg.ShowModal()
        dlg.Destroy()



    def OnSelectData(self,event):
        """
        On data selection, enable Run
        :param event:
        :return:
        """
        if self.chOptions.GetStringSelection() != 'Select data':
            self.btnRun.Enable(True)
        else:
            self.btnRun.Enable(False)

    def OnSubmit(self,event):
        """
        Run OPEX Uploader
        :param event:
        :return:
        """
        self.tcResults.Clear()
        runoption = self.runoptions.get(self.chOptions.GetValue())[2:]

        (db, proj) = self.__loadConnection()
        if self.dirname is None or len(self.dirname) <=0:
            dlg = wx.MessageDialog(self, "Data directory not specified", "OPEX Uploader", wx.OK)
            dlg.ShowModal()  # Show it
            dlg.Destroy()
        else:
            #Load uploader args
            args = argparse.ArgumentParser(prog='OPEX Uploader')
            args.config=join(expanduser('~'), '.xnat.cfg')
            args.database = db
            args.projectcode = proj
            args.create = self.cbCreateSubject.GetValue()
            args.skiprows =self.cbSkiprows.GetValue()
            args.checks = self.cbChecks.GetValue()
            args.update = self.cbUpdate.GetValue()

            uploader = OPEXUploader(args)
            uploader.config()
            uploader.xnatconnect()
            logging.info('Connecting to Server:%s Project:%s', uploader.args.database, uploader.args.projectcode)

            try:
                if uploader.xnat.testconnection():
                    logging.info("...Connected")
                    print("Connected")
                if runoption == 'cantab':
                    fields = os.path.join(os.getcwd(), "resources", 'cantab_fields.csv')
                    uploader.runDataUpload(proj, self.dirname, runoption,fields)
            except IOError as e:
                logging.error(e)
                print "Failed IO:", e
            except ConnectionError as e:
                logging.error(e)
                print "Failed connection:", e
            except ValueError as e:
                logging.error(e)
                print "ValueError:", e
            except Exception as e:
                logging.error(e)
                print "ERROR:", e
            finally:  # Processing complete
                uploader.xnatdisconnect()
                logging.info("FINISHED")
                print("FINISHED - see xnatupload.log for details")

    def OnSubmitCmd(self,event):
        """
        Run OPEX Uploader with args - via commandline
        :return: return code shown in status
        """
        self.tcResults.Clear()
        runoption = self.runoptions.get(self.chOptions.GetValue())
        (db, proj) = self.__loadConnection()
        if db is None:
            return 0
        options = [runoption, db, proj]
        if self.dirname is None or len(self.dirname) <=0:
            dlg = wx.MessageDialog(self, "Data directory not specified", "OPEX Uploader", wx.OK)
            dlg.ShowModal()  # Show it
            dlg.Destroy()
        else:
            options.pop(0)
            options.append(runoption + " " + self.dirname)

            if (self.cbCreateSubject.GetValue()):
                options.append('--create')
            if (self.cbSkiprows.GetValue()):
                options.append('--skiprows')
            if (self.cbChecks.GetValue()):
                options.append('--checks')
            if (self.cbUpdate.GetValue()):
                options.append('--update')
            print options

            cmd = self.__loadCommand(options)
            self.tcResults.Clear()
            self.tcResults.AppendText(cmd)
            self.tcResults.AppendText("\n*******\n")

            try:
                p= subprocess.Popen(cmd, shell=True,stdout=subprocess.PIPE, bufsize=1, universal_newlines=True)
                while True:
                    line = p.stdout.readline()
                    self.tcResults.AppendText(line)
                    # if self.tcResults.GetNumberOfLines() >= 500:
                    #     print "Lines cleared: ", self.tcResults.GetNumberOfLines()
                    #     self.tcResults.Clear()
                    #     p.stdout.flush()
                    if line == '' and p.poll() is not None:
                        break

                if p.returncode != 0:
                    raise subprocess.CalledProcessError(p.returncode, cmd)

                self.tcResults.AppendText("\n***FINISHED***\n")

            except subprocess.CalledProcessError as e:
                retcode = e.returncode
                if retcode < 0:
                    msg = "Program was terminated by signal [" + str(retcode) + "]"
                    print >> sys.stderr, msg
                elif retcode == 1:
                    msg = "Program ran successfully [" + str(retcode) + "]"
                    print >> sys.stderr, msg
                else:
                    msg = "Program error [" + str(retcode) + "] - check output"
                    print >> sys.stderr, msg
                self.tcResults.AppendText(msg)


def main():
    app = wx.App(False)
    OPEXUploaderGUI(None)
    app.MainLoop()

#Execute the application
if __name__ == '__main__':
    main()
