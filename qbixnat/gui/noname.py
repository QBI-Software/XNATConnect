# -*- coding: utf-8 -*- 

###########################################################################
## Python code generated with wxFormBuilder (version Jun 17 2015)
## http://www.wxformbuilder.org/
##
## PLEASE DO "NOT" EDIT THIS FILE!
###########################################################################

import wx
import wx.xrc

###########################################################################
## Class UploaderGUI
###########################################################################

class UploaderGUI ( wx.Frame ):
	
	def __init__( self, parent ):
		wx.Frame.__init__ ( self, parent, id = wx.ID_ANY, title = u"XNAT Uploader", pos = wx.DefaultPosition, size = wx.Size( 700,750 ), style = wx.DEFAULT_FRAME_STYLE|wx.TAB_TRAVERSAL )
		
		self.SetSizeHintsSz( wx.DefaultSize, wx.DefaultSize )
		self.SetBackgroundColour( wx.Colour( 244, 254, 255 ) )
		
		bSizer1 = wx.BoxSizer( wx.VERTICAL )
		
		self.m_staticText1 = wx.StaticText( self, wx.ID_ANY, u"Upload Data to XNAT", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_staticText1.Wrap( -1 )
		self.m_staticText1.SetFont( wx.Font( 12, 71, 90, 92, False, wx.EmptyString ) )
		
		bSizer1.Add( self.m_staticText1, 0, wx.ALL, 5 )
		
		self.m_staticline1 = wx.StaticLine( self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.LI_HORIZONTAL )
		bSizer1.Add( self.m_staticline1, 0, wx.EXPAND |wx.ALL, 5 )
		
		fgSizer2 = wx.FlexGridSizer( 0, 2, 0, 0 )
		fgSizer2.SetFlexibleDirection( wx.BOTH )
		fgSizer2.SetNonFlexibleGrowMode( wx.FLEX_GROWMODE_SPECIFIED )
		
		self.m_staticText2 = wx.StaticText( self, wx.ID_ANY, u"Database config", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_staticText2.Wrap( -1 )
		fgSizer2.Add( self.m_staticText2, 0, wx.ALL, 5 )
		
		self.dbedit = wx.TextCtrl( self, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.DefaultSize, 0 )
		fgSizer2.Add( self.dbedit, 0, wx.ALL, 5 )
		
		self.m_staticText3 = wx.StaticText( self, wx.ID_ANY, u"Project code", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_staticText3.Wrap( -1 )
		fgSizer2.Add( self.m_staticText3, 0, wx.ALL, 5 )
		
		self.projectedit = wx.TextCtrl( self, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.DefaultSize, 0 )
		fgSizer2.Add( self.projectedit, 0, wx.ALL, 5 )
		
		self.m_staticText4 = wx.StaticText( self, wx.ID_ANY, u"Input directory", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_staticText4.Wrap( -1 )
		fgSizer2.Add( self.m_staticText4, 0, wx.ALL, 5 )
		
		bSizer2 = wx.BoxSizer( wx.HORIZONTAL )
		
		self.inputedit = wx.TextCtrl( self, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size( 300,-1 ), 0 )
		bSizer2.Add( self.inputedit, 0, wx.ALL, 5 )
		
		self.btnInputdir = wx.Button( self, wx.ID_ANY, u"Browse", wx.DefaultPosition, wx.DefaultSize, 0 )
		bSizer2.Add( self.btnInputdir, 0, wx.ALL, 5 )
		
		
		fgSizer2.Add( bSizer2, 1, wx.EXPAND, 5 )
		
		self.m_staticText5 = wx.StaticText( self, wx.ID_ANY, u"Data Type", wx.DefaultPosition, wx.DefaultSize, 0 )
		self.m_staticText5.Wrap( -1 )
		fgSizer2.Add( self.m_staticText5, 0, wx.ALL, 5 )
		
		chOptionsChoices = []
		self.chOptions = wx.ComboBox( self, wx.ID_ANY, u"Select data", wx.DefaultPosition, wx.Size( 200,-1 ), chOptionsChoices, 0 )
		fgSizer2.Add( self.chOptions, 0, wx.ALL, 5 )
		
		self.cbCreateSubject = wx.CheckBox( self, wx.ID_ANY, u"Create Subjects from data", wx.DefaultPosition, wx.DefaultSize, 0 )
		fgSizer2.Add( self.cbCreateSubject, 0, wx.ALL, 5 )
		
		self.cbSkiprows = wx.CheckBox( self, wx.ID_ANY, u"Skip ABORTED or NOT_RUN (Cantab)", wx.DefaultPosition, wx.DefaultSize, 0 )
		fgSizer2.Add( self.cbSkiprows, 0, wx.ALL, 5 )
		
		self.cbChecks = wx.CheckBox( self, wx.ID_ANY, u"TEST RUN only", wx.DefaultPosition, wx.DefaultSize, 0 )
		fgSizer2.Add( self.cbChecks, 0, wx.ALL, 5 )
		
		self.cbUpdate = wx.CheckBox( self, wx.ID_ANY, u"Update existing data", wx.DefaultPosition, wx.DefaultSize, 0 )
		fgSizer2.Add( self.cbUpdate, 0, wx.ALL, 5 )
		
		
		bSizer1.Add( fgSizer2, 1, wx.EXPAND, 5 )
		
		bSizer3 = wx.BoxSizer( wx.VERTICAL )
		
		self.tcResults = wx.TextCtrl( self, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.Size( 400,300 ), wx.TE_MULTILINE|wx.TE_READONLY|wx.TE_WORDWRAP|wx.SIMPLE_BORDER )
		bSizer3.Add( self.tcResults, 0, wx.ALL|wx.EXPAND, 5 )
		
		bSizer4 = wx.BoxSizer( wx.HORIZONTAL )
		
		self.btnRun = wx.Button( self, wx.ID_ANY, u"RUN", wx.DefaultPosition, wx.DefaultSize, 0|wx.SIMPLE_BORDER )
		self.btnRun.SetForegroundColour( wx.SystemSettings.GetColour( wx.SYS_COLOUR_BTNFACE ) )
		self.btnRun.SetBackgroundColour( wx.Colour( 0, 128, 64 ) )
		
		bSizer4.Add( self.btnRun, 0, wx.ALL, 5 )
		
		self.btnTest = wx.Button( self, wx.ID_ANY, u"Test Connection", wx.DefaultPosition, wx.DefaultSize, 0 )
		bSizer4.Add( self.btnTest, 0, wx.ALL, 5 )
		
		self.m_button7 = wx.Button( self, wx.ID_ANY, u"Help", wx.DefaultPosition, wx.DefaultSize, 0 )
		bSizer4.Add( self.m_button7, 0, wx.ALL, 5 )
		
		self.btnAbout = wx.Button( self, wx.ID_ANY, u"About", wx.DefaultPosition, wx.DefaultSize, 0 )
		bSizer4.Add( self.btnAbout, 0, wx.ALL, 5 )
		
		self.btnCancel = wx.Button( self, wx.ID_ANY, u"Cancel", wx.DefaultPosition, wx.DefaultSize, 0 )
		bSizer4.Add( self.btnCancel, 0, wx.ALL, 5 )
		
		
		bSizer3.Add( bSizer4, 1, wx.EXPAND, 5 )
		
		
		bSizer1.Add( bSizer3, 1, wx.EXPAND, 5 )
		
		
		self.SetSizer( bSizer1 )
		self.Layout()
		
		self.Centre( wx.BOTH )
		
		# Connect Events
		self.inputedit.Bind( wx.EVT_TEXT_ENTER, self.OnEditDirname )
		self.btnInputdir.Bind( wx.EVT_BUTTON, self.OnOpen )
		self.btnRun.Bind( wx.EVT_BUTTON, self.OnSubmit )
		self.btnTest.Bind( wx.EVT_BUTTON, self.OnTest )
		self.m_button7.Bind( wx.EVT_BUTTON, self.OnHelp )
		self.btnAbout.Bind( wx.EVT_BUTTON, self.OnAbout )
		self.btnCancel.Bind( wx.EVT_BUTTON, self.OnClose )
	
	def __del__( self ):
		pass
	
	
	# Virtual event handlers, overide them in your derived class
	def OnEditDirname( self, event ):
		event.Skip()
	
	def OnOpen( self, event ):
		event.Skip()
	
	def OnSubmit( self, event ):
		event.Skip()
	
	def OnTest( self, event ):
		event.Skip()
	
	def OnHelp( self, event ):
		event.Skip()
	
	def OnAbout( self, event ):
		event.Skip()
	
	def OnClose( self, event ):
		event.Skip()
	

