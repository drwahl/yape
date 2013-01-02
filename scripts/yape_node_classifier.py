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

def configure():
    """Read configuration file and intialize connection to the mongodb instance"""

    from pymongo import Connection
    import os
    from ConfigParser import SafeConfigParser

    parser = SafeConfigParser()
    if os.path.isfile('/etc/yape/conf.ini'):
        config = '/etc/yape/conf.ini'
    else:
        config = os.path.join(os.path.dirname(__file__), "../conf/conf.ini")
    parser.read(config)
    database = parser.get('mongodb_info', 'mongodb_db_name')
    collection = parser.get('mongodb_info', 'mongodb_collection_name')
    host = parser.get('mongodb_info', 'mongodb_server')
    con = Connection(host)
    col = con[database][collection]
    return col

def classify(cnode):
    """Classify the requested node, including inheritances"""

    col = configure()
    try:
        node_classes = col.find_one({'node': cnode})['enc']['classes']
    except TypeError:
        node_classes = {}

    try:
        # Grab the info from the inheritance node
        inode = col.find_one({'node': cnode})
        if not inode['inherit']:
            raise KeyError
        inode_classes = classify(inode['inherit'])
        if not col.find_one({"node" : cnode}):
            print "ERROR: Inheritance node " + cnode + " not found in ENC"
            sys.exit(1)
        node_classes = col.find_one({"node": cnode})['enc']['classes']
        # Grab the requested node's classes
        tmp_class_store = node_classes
        # Apply the inheritance node classes
        node_classes = dict(inode_classes)
        # Apply the requested node's classes and overrides
        node_classes.update(tmp_class_store)
    except KeyError:
        pass 
    except TypeError:
        pass 

    return node_classes

def main(node):
    """This script is called by puppet"""

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
    main(sys.argv[1])
