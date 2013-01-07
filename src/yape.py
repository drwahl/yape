#!/usr/bin/python
# vim: set expandtab:
"""
**********************************************************************
GPL License
***********************************************************************
This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <http://www.gnu.org/licenses/>.

***********************************************************************/

:author: David Wahlstrom
:email: david.wahlstrom@gmail.com

"""

import sys
import logging

logging.basicConfig(level=logging.WARN,
                    format='%(asctime)s %(levelname)s - %(message)s',
                    datefmt='%y.%m.%d %H:%M:%S'
                   )
console = logging.StreamHandler(sys.stderr)
console.setLevel(logging.WARN)
logging.getLogger("yape").addHandler(console)
log = logging.getLogger("yape")

class Node(object):
    """Class to facilitate adding/modifying a node"""
    log.debug('in class Node()')

    def __init__(self, nodename, nodeclass=None, classparams=None, nodeparam=None, puppet_inherit=None, environment=None):
        """Initialize variables for use"""
        log.debug('in Node().__init__')

        #create an initial connection to the mongodb
        self.mongo_collection = self.configure()

        #verify the inherit node exists
        if puppet_inherit:
            if self.verifynode(puppet_inherit) is False:
                print "ERROR: Inherit node does not exist, please add %s and then retry" % puppet_inherit
            else:
                self.puppet_inherit = puppet_inherit
        self.node = nodename
        if nodeclass:
            self.nodeclass = nodeclass
        else:
            self.nodeclass = ''
        self.classparams = classparams
        self.nodeparam = nodeparam
        if puppet_inherit:
            self.puppet_inherit = puppet_inherit
        else:
            self.puppet_inherit = 'none'
        if environment:
            self.environment = environment
        else:
            self.environment = ''

    def configure(self):
        """Read configuration file and intialize connection to the mongodb instance"""
        log.debug('in Node().configure')

        from pymongo import Connection
        import os
        from ConfigParser import SafeConfigParser

        parser = SafeConfigParser()
        if os.path.isfile('/etc/yape/conf.ini'):
            log.debug('reading config from: /etc/yape/conf.ini')
            config = '/etc/yape/conf.ini'
        else:
            log.debug('reading config from: ../conf/conf.ini')
            config = os.path.join(os.path.dirname(__file__), "../conf/conf.ini")
        parser.read(config)
        host = parser.get('mongodb_info', 'mongodb_server')
        log.debug('connecting to mongodb host: %s' % host)
        database = parser.get('mongodb_info', 'mongodb_db_name')
        log.debug('connecting to database name: %s' % database)
        collection = parser.get('mongodb_info', 'mongodb_collection_name')
        log.debug('using collection name: %s' % collection)
        con = Connection(host)
        col = con[database][collection]
        return col

    def verifynode(self, vernode=None):
        """Verify that the node exists in the DB. Returns True if it does exist, Return False if it does not"""
        log.debug('in Node().verifynode')

        if not vernode:
            testnode = self.node
        else:
            testnode = vernode

        log.debug('verifying node: %s' % testnode)
        docnode = self.mongo_collection.find_one({'node': testnode})
        if docnode is None:
            log.debug('node %s not found in database' % testnode)
            return False
        else:
            if docnode['node'] == testnode:
                log.debug('node %s found in database' % testnode)
                return True
            else:
                log.debug('node %s not found in database' % testnode)
                return False

    def parse_node_classification(self, puppet_class=None, class_params=None, parameters=None, environment=None, inherit=None):
        """Parse puppet_class, class_params, parameters, and environment, and return a dict with the result"""
        log.debug('in Node().parse_node_classification')

        puppet_enc = {
            'classes': '',
            'environment': '',
            'parameters': '',
        }

        if not puppet_class:
            puppet_class = self.nodeclass
        puppet_enc['classes'] = puppet_class

        if not class_params:
            class_params = self.classparams

        if parameters:
            puppet_enc['parameters'] = parameters
        else:
            if self.nodeparam:
                puppet_enc['parameters'] = self.nodeparam
            else:
                puppet_enc['parameters'] = ''

        if environment:
            puppet_enc['environment'] = environment
        else:
            puppet_enc['environment'] = self.environment

        if not puppet_enc['classes']:
            puppet_enc['classes'] = []

        if not puppet_enc['parameters']:
            puppet_enc['parameters'] = {}

        if not puppet_enc['environment']:
            del puppet_enc['environment']

        paramclass = {}
        try:
            log.debug('trying to get class parameters')
            paramclass = self.mongo_collection.find_one({'node': self.node})['enc']['classes']
            log.debug('got class parameters: %s' % paramclass)
        except:
            log.debug('unable to get class parameters (not a parameterised class?)')
            paramclass = {}

        if not paramclass:
            paramclass = {}

        #Pull parameters for each class
        if puppet_class:
            log.debug('processing puppet class: %s' % puppet_class)
            paramkeyvalue = {}
            paramvalue = []
            if not class_params:
                log.debug('no class parameters for class: %s' % puppet_class)
                paramkeyvalue = ''
            else:
                log.debug('parameters found for class: %s' % puppet_class)
                for param in class_params.split(','):
                    log.debug('processing parameter "%s" for class "%s"' % (param, puppet_class))
                    paramkey = ''
                    paramkey = param.split('=')[0]
                    log.debug('found parameter key to be: %s' % paramkey)
                    paramvalue.append(param.split('=')[1])
                    log.debug('found parameter value to be: %s' % paramvalue)
                paramkeyvalue[paramkey] = paramvalue

            log.debug('setting class "%s" with key/value: %s' % (puppet_class, paramkeyvalue))
            paramclass[puppet_class] = paramkeyvalue

            #Since we stored them as lists above, reduce single item lists to strings
            for puppetclass in paramclass:
                log.debug('cleaning up class: %s' % puppetclass)
                for param in paramclass[puppetclass]:
                    log.debug('cleaning up parameter: %s' % param)
                    if type(paramclass[puppetclass][param]) is type(list()):
                        log.debug('processing %s as a list')
                        if len(paramclass[puppetclass][param]) == 1:
                            log.debug('%s is a list with a single entry')
                            paramclass[puppetclass][param] = paramclass[puppetclass][param][0]

            puppet_enc['classes'] = paramclass

        log.debug('returning puppet_enc as: %s' % puppet_enc)
        return puppet_enc

    def update(self, enc, inherit=None):
        """Add/modify "enc" properties on "node" """
        log.debug('in Node().update')

        if inherit:
            log.debug('inherit passed to Node().update as %s' % inherit)
            tmp_inherit = inherit
        else:
            log.debug('inherit not passed to Node().update. using: %s' % self.puppet_inherit)
            tmp_inherit = self.puppet_inherit

        if not self.verifynode('none'):
            log.debug('adding node "none" to mongodb server: {\'node\': \'none\'}, {"$set": {\'enc\': {\'classes\': []}, \'inherit\': ''}}, True')
            self.mongo_collection.update({'node': 'none'}, {"$set": {'enc': {'classes': []}, 'inherit': ''}}, True)

        log.debug('sending update to mongodb server: {\'node\': %s}, {"$set": {\'enc\': %s, \'inherit\': %s}}, True' % (self.node, enc, tmp_inherit))
        self.mongo_collection.update({'node': self.node}, {"$set": {'enc': enc, 'inherit': tmp_inherit}}, True)

    def remove(self, rmnode=None):
        """Remove node from mongodb"""
        log.debug('in Node().remove')

        if rmnode:
            log.debug('rmnode passed to Node().remove as: %s' % rmnode)
            nodename = rmnode
        else:
            log.debug('rmnode not passed to Node().remove. using: %s' % self.node)
            nodename = self.node

        nodes_with_inheritance = self.mongo_collection.find({'inherit': nodename})
        for inheritnode in nodes_with_inheritance:
            print "%s inherits the node you are removing." % inheritnode['node']

        log.debug('sending remove to mongodb server: {\'node\': %s}' % nodename)
        self.mongo_collection.remove({'node': nodename})

if __name__ == "__main__":

    import argparse

    cmd_parser = argparse.ArgumentParser(description='Add/remove/modify nodes in MongoDB ENC.')
    cmd_parser.add_argument('-n', '--node', dest='puppet_node', help='Puppet node hostname.', required=True)
    cmd_parser.add_argument('-r', '--remove', dest='remove_attr', help='Remove supplied attributes from host.', action='store_true', default=False)
    cmd_parser.add_argument('-c', '--class', dest='puppet_class', help='Apply (or remove with -r) class on node (-n). Parameters can be passed to the class with -m.', action='store', default=None)
    cmd_parser.add_argument('-m', '--classparameters', dest='class_params', help='Apply (or remove with -r) class parameters to class (-c) on node (-n).', action='store', default=None)
    cmd_parser.add_argument('-p', '--param', dest='puppet_param', help='Apply (or remove with -r) parameters (global variables) to node (-n).', action='store', default=None)
    cmd_parser.add_argument('-i', '--inherit', dest='puppet_inherit', help='Apply (or remove with -r) inherit node.  Only a single node can be set to inherit from.', action='store', default=None)
    cmd_parser.add_argument('-e', '--environment', dest='environment', help='Apply (or remove with -r) puppet agent environment.', default=None)
    cmd_parser.add_argument('-d', '--debug', dest='debug', action='store_true', help='Enable debugging during execution', default=None)
    args = cmd_parser.parse_args()

    if args.debug:
        log.setLevel(logging.DEBUG)

    node = Node(args.puppet_node, args.puppet_class, args.class_params, args.puppet_param, args.puppet_inherit, args.environment)

    if args.remove_attr is True:
        log.debug('remove attributes requested')
        node.remove(node.node)
    else:
        log.debug('node update requested')
        node.update(node.parse_node_classification())
