#!/usr/bin/env python

import os, sys, cherrypy, json, argparse

import psycopg2, psycopg2.pool

from controllers.enhancers.enhancers import EnhancersSite
from controllers.promoters.promoters import PromotersSite
from controllers.hic.hic import HiCSite

sys.path.append(os.path.join(os.path.dirname(__file__), '../metadata/utils'))
from dbs import DBS
from templates import Templates
from utils import Utils

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--local', action="store_true", default=False)
    parser.add_argument('--debug', action="store_true", default=False)
    parser.add_argument('--dev', action="store_true", default=True)
    parser.add_argument('--port', default=9191)
    args = parser.parse_args()
    return args

class MainApp():
    def __init__(self, args):
        self.args = args

        viewDir = os.path.join(os.path.dirname(__file__), "views")
        self.templates = Templates(viewDir)

        self.staticDir = os.path.realpath(os.path.join(os.path.dirname(__file__),
                                                       "views/static"))
        self.config = {
            '/static': {
                'tools.staticdir.on': True,
                'tools.staticdir.dir': self.staticDir
                }
            }

    @cherrypy.expose
    def index(self):
        raise cherrypy.HTTPRedirect("/enhancers")

def dbconn(args):
    if args.local:
        dbs = DBS.localAnnotations()
    else:
        dbs = DBS.pgdsn("Annotations")
    dbs["application_name"] = os.path.realpath(__file__)
    return psycopg2.pool.ThreadedConnectionPool(1, 32, **dbs)

def getRootConfig(siteName):
    cacheDir = os.path.realpath(os.path.join(os.path.dirname(__file__),
                                             "cache", siteName))
    Utils.mkdir_p(cacheDir)

    logDir = os.path.join(cacheDir, "logs")
    Utils.mkdir_p(logDir)

    return {
        '/': {
            'tools.sessions.on' : True,
            'tools.sessions.timeout' : 60000,
            'tools.sessions.storage_type' : "file",
            'tools.sessions.storage_path' : cacheDir,
            'log.access_file' : os.path.join(logDir, "access.log"),
            'log.error_file' : os.path.join(logDir, "error.log"),
            'log.screen' : False,
        }
    }

def main():
    args = parse_args()

    mainIndex = MainApp(args)
    cherrypy.tree.mount(mainIndex, '/', config = mainIndex.config)

    DBCONN = dbconn(args)

    cherrypy.tree.mount(HiCSite(DBCONN, args, mainIndex.staticDir), '/hic',
                        config=getRootConfig("hic"))
    cherrypy.tree.mount(EnhancersSite(DBCONN, args), '/enhancers',
                        config=getRootConfig("enhancers"))
    cherrypy.tree.mount(PromotersSite(DBCONN, args), '/promoters',
                        config=getRootConfig("promoters"))

    if args.dev:
        cherrypy.config.update({'server.environment': "development", })
    cherrypy.config.update({'server.socket_host': '0.0.0.0', })
    cherrypy.config.update({'server.socket_port': int(args.port), })

    if not args.local:
        # fend off harassment by the cluster
        cherrypy.config.update({'server.socket_queue_size': 512})
        cherrypy.config.update({'server.thread_pool': 30})

    cherrypy.engine.start()
    cherrypy.engine.block()

if __name__ == '__main__':
    sys.exit(main())
