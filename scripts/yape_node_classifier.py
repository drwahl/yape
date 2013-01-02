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

import yaml
import sys
import logging

logging.basicConfig(level=logging.WARN,
                    format='%(asctime)s %(levelname)s - %(message)s',
                                        datefmt='%y.%m.%d %H:%M:%S'
                                                           )
console = logging.StreamHandler(sys.stderr)
console.setLevel(logging.WARN)
logging.getLogger("yape_node_classifier").addHandler(console)
log = logging.getLogger("yape_node_classifier")

def configure():
    """Read configuration file and intialize connection to the mongodb instance"""
    log.debug('in configure()')

    from pymongo import Connection
    import os
    from ConfigParser import SafeConfigParser

    parser = SafeConfigParser()
    if os.path.isfile('/etc/yape/conf.ini'):
        log.debug('loaded config file from: /etc/yape/conf.ini')
        config = '/etc/yape/conf.ini'
    else:
        log.debug('loaded config file from: ../conf/conf.ini')
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

def classify(cnode):
    """Classify the requested node, including inheritances"""
    log.debug('in classify(%s)' % cnode)

    col = configure()
    try:
        log.debug('attempting to retrieve classes for %s' % cnode)
        node_classes = col.find_one({'node': cnode})['enc']['classes']
        log.debug('classes found for %s: %s' % (cnode, node_classes))
    except TypeError:
        log.debug('unable to retrieve classes for %s' % cnode)
        node_classes = {}

    try:
        log.debug('grabbing info from the inheritance node')
        inode = col.find_one({'node': cnode})
        if not inode['inherit']:
            log.debug('no inheritance node found')
            raise KeyError
        log.debug('found inheritance node: %s' % inode)
        inode_classes = classify(inode['inherit'])
        if not col.find_one({"node" : cnode}):
            print "ERROR: Inheritance node " + cnode + " not found in ENC"
            sys.exit(1)
        tmp_class_store = col.find_one({"node": cnode})['enc']['classes']
        log.debug('retrieved classes for %s: %s' % (cnode, tmp_class_store))
        node_classes = dict(inode_classes)
        log.debug('setting inheritance node (%s) classes: %s' % (inode['inherit'], dict(inode_classes)))
        node_classes.update(tmp_class_store)
        log.debug('replaying requested nodes classes on top of inheritance node classes: %s' % node_classes)
    except KeyError:
        pass 
    except TypeError:
        pass 

    log.debug('returning node_classes as: %s' % node_classes)
    return node_classes

def main(node):
    """This script is called by puppet"""
    log.debug('in main(%s)' % node)

    if (len(sys.argv) < 2):
        print "ERROR: Please supply a hostname or FQDN"
        sys.exit(1)

    col = configure()

    # Find the node given at a command line argument
    d = col.find_one({"node": node}) 
    if d == None:
        print "ERROR: Node %s not found in ENC"  % node
        sys.exit(1)

    # Classify node
    d['enc']['classes'] = classify(node)

    print yaml.safe_dump(d['enc'], default_flow_style=False)


if __name__ == "__main__":

    try:
        if sys.argv[2] == '-d':
            log.setLevel(logging.DEBUG)
    except:
        pass

    main(sys.argv[1])
