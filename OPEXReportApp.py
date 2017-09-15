import dash
import dash_core_components as dcc
import dash_html_components as html
import plotly.graph_objs as go
import pandas as pd
from os.path import expanduser, join, exists
from qbixnat.XnatConnector import XnatConnector  # Only for testing
from qbixnat.OPEXReport import OPEXReport
import time
import multiprocessing
from datetime import datetime
from matplotlib import colors as mcolors
import matplotlib.pyplot as plt
import pandas as pd
from os import environ,access,R_OK
from configobj import ConfigObj
import logging
import sys

""" 
OPEX Report DASHBOARD via DASH
https://plot.ly/python/create-online-dashboard/
"""

class OPEXReportApp(object):

    def __init__(self):
        self.app = dash.Dash(__name__)
        self.database = None
        self.project = None
        self.cache = None
        self.dbconfig = None
        self.df_participants = {}
        self.df_report = {}
        self.df_expts = {}
        self.__loadParams()
        logging.basicConfig(filename=join(self.logs,'xnatreport.log'), level=logging.DEBUG,
                            format='%(asctime)s %(message)s', datefmt='%d-%m-%Y %I:%M:%S %p')

    def __loadParams(self):
        home = expanduser('~')
        params = join(home,'.opex.cfg')
        if params is not None and access(params, R_OK):
            config = ConfigObj(params)
            self.database = config['DATABASE']
            self.project = config['PROJECT']
            self.cache = config['CACHEDIR']
            self.dbconfig = config['DBCONFIG']
            self.logs = config['LOGS']
        else:
            logging.error('Unable to read config - using defaults')
            self.database = 'opex'
            self.project = 'P1'
            self.cache = 'cache'
            self.dbconfig = join(home,'.xnat.cfg')
            self.logs = 'logs'

    def loadData(self):
        #output = "ExptCounts_%s.csv" % datetime.today().strftime("%Y%m%d")
        # output = "ExptCounts.csv"
        # outputfile = join(self.cache, output)


        # if exists(outputfile):
        #     report = OPEXReport(csvfile=outputfile)
        #     logging.info("Loading via cache")
        # else:
        #     logging.info("Loading from database")
        configfile = self.dbconfig
        xnat = XnatConnector(configfile, self.database)
        try:
            xnat.connect()
            if xnat.testconnection():
                print "...Connected"
                output = "ExptCounts.csv"
                outputfile = join(self.cache, output)
                if access(outputfile, R_OK):
                    csv = outputfile
                else:
                    csv = None
                subjects = xnat.getSubjectsDataframe(self.project)
                msg = "Loaded %d subjects from %s : %s" % (len(subjects), self.database, self.project)
                logging.info(msg)
                report = OPEXReport(subjects=subjects,csvfile=csv)
                report.xnat = xnat
                # Generate dataframes for display
                self.df_participants = report.getParticipants()
                logging.debug('Participants loaded')
                print self.df_participants
                self.df_report = report.printMissingExpts(self.project)
                self.df_report.sort_values(by=['MONTH', 'Subject'], inplace=True, ascending=False)
                logging.debug("Missing experiments loaded")
                print self.df_report.head()
                # Get expts
                self.df_expts = report.getExptCollection(projectcode=self.project)
                logging.debug("Experiment collection loaded")
                print self.df_expts.head()

        except IOError:
            logging.error("Connection error - terminating app")
            print "Connection error - terminating app"
            sys.exit(1)
        finally:
            xnat.conn.disconnect()



    def colors(self):
        colors = {
        'background': '#111111',
        'text': '#7FDBFF'
        }
        return colors

    def tablecell(self,val):
        mycolors = list(['#fafad2','#eee8aa','#ffff00','#ffa500','#ff8c00','#ff7f50','#f08080','#ff6347','#ff4500','#ff0000'])

        if type(val) != str:
            val = int(val)
            if val <= 0:
                return html.Td([html.Span(className="glyphicon glyphicon-ok")],
                               className="btn-success")
            else:
                valcolor = val % len(mycolors)
                return html.Td([html.Span(val)], style={'color':'black','background-color': mycolors[valcolor]})
        else:
            return html.Td(val)

    def generate_table(self,dataframe, max_rows=10):
        colors = self.colors()
        return html.Table(
            # Header
            [html.Tr([html.Th(col) for col in dataframe.columns])] +

            # Body
            [html.Tr([
                self.tablecell(dataframe.iloc[i][col]) for col in dataframe.columns
            ]) for i in range(min(len(dataframe), max_rows))]
            ,
            className='table',
            style={
                    'textAlign': 'center',
                    'color': colors['text']
                })

    def participants_layout(self):
        logging.info("Loading data from db")
        self.loadData()
        logging.info("Data loaded - rendering")
        df = self.df_participants
        df_expts = self.df_expts
        df_report = self.df_report
        if df is None or df_expts is None or df_report is None:
            logging.error("No data to load")
            return 0

        colors = self.colors()
        title = 'OPEX XNAT participants [Total=' + str(sum(df['All'])) + ']'
        #self.app.css.append_css({"external_url": "https://codepen.io/chriddyp/pen/bWLwgP.css"})
        self.app.css.append_css({"external_url": "https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/css/bootstrap.min.css"})
        return html.Div(className='container',
                                   style={'backgroundColor': colors['background']},
                                   children=[
        html.H1(children='OPEX Report',
                style={
                    'textAlign': 'center',
                    'color': colors['text']
                }
                ),

        html.Div(children=title,
                 style={
            'textAlign': 'center',
            'color': colors['text']
        }),

        dcc.Graph(
            id='participants',
            style={'width': '50%', 'float':'left'},
            figure={
                'data': [
                    {'x': df['Group'], 'y': df['Male'], 'type': 'bar', 'name': 'Male'},
                    {'x': df['Group'], 'y': df['Female'], 'type': 'bar', 'name': 'Female'},
                ],
                'layout': {
                    'barmode':'stack',
                    'plot_bgcolor': colors['background'],
                    'paper_bgcolor': colors['background'],
                    'title' : 'Participants',
                    'font': {
                        'color': colors['text']
                    }
                }
            }
        ),
        # Expts stacked bar
        dcc.Graph(
           id='expts',
           style={'width':'50%', 'float':'left'},
           figure=go.Figure(
               data=[
                   go.Pie(
                       values=df_expts.sum(),
                       labels=df_expts.columns,
                   )

               ],
               layout=go.Layout(
                       title='Experiments',
                       yaxis={'title': 'Expts Total'},
                       margin={'l': 40, 'b': 10, 't': 30, 'r': 10},
                       #legend={'x': 0, 'y': 1},
                       hovermode='closest',
                       font={ 'color': colors['text']},
                       plot_bgcolor= colors['background'],
                       paper_bgcolor= colors['background']
               )

           ),

        ),
        html.Div(id='missing',
                 children=[
           html.H3(children='Missing Data report',
                   style={
                       'textAlign': 'center',
                       'color': colors['text']
                   }),
            self.generate_table(df_report, max_rows=100)
            ])
    ])




#####################################################################

#for wsgi deployment
op = OPEXReportApp()
server  = op.app.server
server.secret_key = environ.get('SECRET_KEY', 'my-secret-key')
#op.loadData()
op.app.layout = op.participants_layout()


# for local deployment
if __name__ == '__main__':
    # op = OPEXReportApp()
    # op.loadData()
    # op.app.layout = op.participants_layout()
    op.app.run_server(debug=True, port=8089)
