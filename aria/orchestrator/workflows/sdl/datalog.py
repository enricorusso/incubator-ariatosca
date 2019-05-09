from aria import workflow
from aria.orchestrator.workflows.api import task
from aria.orchestrator.workflows.exceptions import TaskException
from string import Template
from lark import Lark, Tree, Token
import re, copy, tempfile

class TemplateBehavior(Template):
	delimiter = "$"
	idpattern = r'[a-z][->._$a-z0-9\[\]]*'


class BehaviorParser:
    def compile(self, tree, ptr):
        if len(tree.children) > 1:
            if not isinstance(tree.children[1], Token):
                # print(tree.children[0] + "->" + tree.children[1].children[0])
                if tree.data == "ref":
                    matches = [x for x in ptr.outbound_relationships if x.name == tree.children[1].children[0]]
                    assert len(matches) == 1
                    ptr = matches[0].target_node
                    # print("Tosca ID: " + ptr.attributes['tosca_id'])
                return self.compile(tree.children[1], ptr)
            else:
                if tree.data == "ref":
                    matches = [x for x in ptr.outbound_relationships if x.name == tree.children[1]]
                    assert len(matches) == 1
                    return "_".join(matches[0].target_node.attributes['tosca_id'].split('_')[:-1])

                if tree.data == "prop":
                    return ptr.properties[tree.children[1]]

                if tree.data == "mapaccess":
                    if ptr.properties[tree.children[0]].__class__.__name__ != '_InstrumentedList':
                        return ptr.properties[tree.children[0]][tree.children[1]]
                    else:
                        retList = []
                        for x in ptr.properties[tree.children[0]]:
                            retList.append(x[tree.children[1]])
                        return retList

@workflow
def createmodel(ctx, graph):
    parser = Lark('''?path: ref "->" path -> ref
                            | access

                            ?access: ref "." prop -> prop
                            | ref

                            ?ref: "$" ID

    			            ?prop: ID | mapaccess

    			            ?mapaccess: ID "[" ID "]"

                            SYMBOL: LETTER | DIGIT | "_"
                            ID: SYMBOL+                 
                            
                            %import common.LETTER
                            %import common.DIGIT
                            ''', start='path')

    temp = open("/tmp/test.py", "w")
    #temp = tempfile.NamedTemporaryFile(suffix='.py')
    print("Tempfile: " + temp.name)

    temp.write("import logging\n")
    temp.write("from pyDatalog import pyDatalog\n")
    temp.write("from pyDatalog import pyEngine\n")
    temp.write("pyEngine.Logging = True\n")
    temp.write("logging.basicConfig(level=logging.DEBUG)\n\n")

    names = ['isConnected', 'hasAccount', 'hasUser', 'hostACL', 'listeningOn', 'knows' ]
    facts = []
    clauses = []
    queries = []

    for n in ctx.nodes:
        # maaazinga, compile behavior :)

        if 'behavior' in n.properties.keys():
            for key in n.properties['behavior']:
                e = n.properties['behavior'][key]

                tstring = TemplateBehavior(e)
                result = re.findall(tstring.pattern, tstring.template)
                dstring = [{}]
                k = 0
                for r in result:
                    if r[1] != "this":
                        parse_tree = parser.parse("$" + r[1])
                        behavior = BehaviorParser().compile(parse_tree, n)
                    else:
                        behavior = "_".join(n.attributes['tosca_id'].split('_')[:-1])

                    if type(behavior) == list:
                        for i, item in enumerate(behavior):
                            if len(dstring)-1 < i:
                                dstring.insert(i, copy.copy(dstring[i-1]))

                            dstring[i][r[1]] = item
                    else:
                        dstring[k][r[1]] = behavior

                print("# " + "_".join(n.name.split('_')[:-1]))

                for x in dstring:
                    try:
                        found = re.findall('\((.+?)\)', tstring.safe_substitute(x))
                    except AttributeError:
                        found = ''  # apply your error handling
                    for f in found:
                        f = f[f.find("(") + 1:]
                        #print "f: " + f
                        for f1 in f.split(','):
                            f2 = f1.strip()
                            if f2[0] != "'" and (not f2.isdigit()):
                                print ("term: " + f2)
                                names.append(f2)
                    v = tstring.safe_substitute(x)
                    print("ecco: " + tstring.safe_substitute(x))
                    if "<=" in v:
                        clauses.append(v)
                    else:
                        if v[0:5] == "print":
                            queries.append(v)
                        else:
                            facts.append(v)

                    #temp.write(tstring.safe_substitute(x) + "\n")

    # terms
    temp.write("pyDatalog.create_terms('")
    i = 0
    print set(names)
    for t in set(names):
        if i == 0:
            temp.write(t)
        else:
            temp.write(", " + t)
        i=i+1
    temp.write("')\n\n")
    # facts
    for t in facts:
        temp.write(t + "\n")
    temp.write("\n")
    # clauses
    for t in clauses:
        temp.write(t + "\n")
    temp.write("\n\n")
    # goals
    for t in queries:
        temp.write(t + "\n")

    temp.close()
    temp.close()
    # for node in ctx.model.node.iter():
    #     print('{0}'.format(node.attributes['tosca_name']))
    #     try:
    #         graph.add_tasks(task.OperationTask(node, interface_name='Datalog', operation_name='createmodel'))
    #     except TaskException:
    #         pass
