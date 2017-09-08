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
import pandas as pd
from os import environ,access,R_OK
from configobj import ConfigObj
import logging
import sys

""" 
OPEX Report DASHBOARD via DASH
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
        logging.basicConfig(filename='xnatreport.log', dir=self.logs, level=logging.DEBUG,
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
            self.database = 'opex-ro'
            self.project = 'P1'
            self.cache = 'cache'
            self.dbconfig = join(home,'.xnat.cfg')
            self.logs = 'logs'

    def loadData(self):
        output = "ExptCounts_%s.csv" % datetime.today().strftime("%Y%m%d")
        outputfile = join(self.cache, output)
        if exists(outputfile):
            report = OPEXReport(csvfile=outputfile)
            logging.info("Loading via cache")
        else:
            logging.info("Loading from database")
            configfile = self.dbconfig
            xnat = XnatConnector(configfile, self.database)
            try:
                xnat.connect()
                if xnat.testconnection():
                    print "...Connected"
                    subjects = xnat.get_subjects(self.project)
                    if (subjects.fetchone() is not None):
                        report = OPEXReport(subjects)
                        report.xnat = xnat
                        active_subjects = [s for s in subjects if s.attrs.get('group') != 'withdrawn']
                        subjects = list(active_subjects)
                        #Parallel processing for getting counts
                        start = time.time()
                        logging.info("Starting multiprocessing ..." + str(start))

                        total_tasks = len(subjects)
                        tasks = []
                        mm = multiprocessing.Manager()
                        q = mm.dict()
                        for i in range(total_tasks):
                            p = multiprocessing.Process(target=report.processCounts, args=(subjects[i], q))
                            tasks.append(p)
                            p.start()

                        for p in tasks:
                            p.join()

                        logging.info("Finished multiprocessing:" +  str(time.time() - start) + 'secs')
                        headers = ['Group', 'Subject', 'M/F'] + report.exptintervals.keys() + ['Stage']
                        report.data = pd.DataFrame(q.values(), columns=headers)
                        report.data.to_csv(outputfile, index=False)  # cache
                        logging.info("Data saved to cache: " + outputfile)
            except IOError:
                logging.error("Connection error - terminating app")
                print "Connection error - terminating app"
                sys.exit(1)
            finally:
                xnat.conn.disconnect()

        #Generate dataframes for display
        self.df_participants = report.getParticipants()
        logging.debug('Participants loaded')
        print self.df_participants
        self.df_report = report.printMissingExpts()
        self.df_report.sort_values(by='Progress', inplace=True, ascending=False)
        logging.debug("Missing experiments loaded")
        print self.df_report.head()
        # Get expts
        self.df_expts = report.getExptCollection()
        logging.debug("Experiment collection loaded")
        print self.df_expts.head()

    def colors(self):
        colors = {
        'background': '#111111',
        'text': '#7FDBFF'
        }
        return colors

    def tablecell(self,val):
        basecolors = dict(mcolors.BASE_COLORS, **mcolors.CSS4_COLORS)
        by_hsv = sorted((tuple(mcolors.rgb_to_hsv(mcolors.to_rgba(color)[:3])), name)
                        for name, color in basecolors.items())
        # Sort by hue, saturation, value and name.
        mycolors = list(sorted(mcolors.CSS4_COLORS.keys()))

            #sorted(mcolors.rgb_to_hsv(mcolors.to_rgba(color)[:3])for color in basecolors.items())
            #ist(mcolors.CSS4_COLORS.keys())

        if type(val) != str:
            if val <= 0:
                return html.Td([html.Span(className="glyphicon glyphicon-ok")],
                               className="btn-success")
            else:
                return html.Td([html.Span(val)], style={'color':'black','background-color': mycolors[val]})
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
            figure={
                'data': [
                    {'x': df['Group'], 'y': df['Male'], 'type': 'bar', 'name': 'Male'},
                    {'x': df['Group'], 'y': df['Female'], 'type': 'bar', 'name': 'Female'},
                ],
                'layout': {
                    'barmode':'stack',
                    'plot_bgcolor': colors['background'],
                    'paper_bgcolor': colors['background'],
                    'font': {
                        'color': colors['text']
                    }
                }
            }
        ),
        # Expts stacked bar
        dcc.Graph(
           id='expts',
           figure=go.Figure(
               data=[
                   go.Bar(
                       text=df_expts['Subject'],
                       y=df_expts[i],
                       name=i,
                   ) for i in df_expts.columns[2:]

               ],
               layout=go.Layout(
                       xaxis={'type': 'linear', 'title': 'Participants'},
                       yaxis={'title': 'Expts Count'},
                       margin={'l': 40, 'b': 40, 't': 10, 'r': 10},
                       legend={'x': 0, 'y': 1},
                       hovermode='closest'
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
op.loadData()
op.app.layout = op.participants_layout()


# for local deployment
if __name__ == '__main__':
    op.app.run_server(debug=True, port=8089)
