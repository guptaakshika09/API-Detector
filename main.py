import ast
import astunparse
import os
import re
from pprint import pprint
from collections import deque
import json

class DocStringVisitor(ast.NodeVisitor):
    """Visits all the Constant Nodes in AST to get the doc string"""
    def __init__(self):
        self.visited = 0
        self.doc_str = ""
    def generic_visit(self,node):
        if isinstance(node, ast.Constant) and self.visited == 0:
            self.visited = 1
            self.doc_str = node.value
        ast.NodeVisitor.generic_visit(self,node)

class FuncVisitor(ast.NodeVisitor):
    """Visits all the FunctionDef Nodes in AST"""
    def __init__(self,api_str):
        super(FuncVisitor, self).__init__()
        self.api_name = api_str
        self.func_map = {}
        self._func_names = []
        self._name_api_map = {}
        self._func_nodes = []
        self.func_dec_map = []

    def flatten_attr(self,node):
        """For Nested Decorators"""
        if isinstance(node, ast.Attribute):
            return str(self.flatten_attr(node.value)) + '.' + node.attr
        elif isinstance(node, ast.Name):
            return str(node.id)
        else:
            pass

    def return_list(self):
        return self.func_dec_map

    def return_decorator_list(self, _func_nodes = None):
        if _func_nodes is None:
            _func_nodes = self._func_nodes
        for node in _func_nodes:
            found_decorators = []
            for decorator in node.decorator_list:
                if isinstance(decorator, ast.Name):
                    found_decorators.append(decorator.id)
                elif isinstance(decorator, ast.Attribute):
                    found_decorators.append(self.flatten_attr(decorator))
                elif isinstance(decorator, ast.Call):
                    comment = ""
                    id1 = ""
                    attr1 = ""
                    for val_node in ast.walk(decorator):
                        if isinstance(val_node,ast.Name):
                            id1 = val_node.id
                        if isinstance(val_node,ast.Attribute):
                            attr1 = val_node.attr
                        if isinstance(val_node,ast.Constant):
                            comment = val_node.value
                    try:
                        found_decorators.append(id1+"."+attr1+" # "+comment)
                    except:
                        pass
            self.func_dec_map.append((node.name,found_decorators))
        return self.func_dec_map

    def generic_visit(self,node):
        if isinstance(node,ast.FunctionDef):
            flag = 0
            if(node.name == "__init__" and self.api_name.find(".")!=-1):
                # print("here - ",node.name,self.api_name)
                name1 = self.api_name
            elif(node.name =="__init__"):
                # print("2 - ",self.api_name)
                flag = 1
            else:
                name1 = self.api_name+"."+node.name+"()"
            if(flag==0):
                self.func_map[name1] = node
                self._func_names.append(name1.split(".")[-1])
                self._name_api_map[name1.split(".")[-1]] = name1
                self._func_nodes.append(node)
        ast.NodeVisitor.generic_visit(self,node)

        
class ClassVisitor(ast.NodeVisitor):
    def __init__(self,api_str):
        self.api_name = api_str
        self.class_map = {}
        self.func_map = {}
        self.func_names = []
    def generic_visit(self,node):
        if isinstance(node, ast.ClassDef):
            name1 = self.api_name+"."+node.name
            self.class_map[name1] = node
            fv = FuncVisitor(name1)
            fv.visit(node)
            for f in fv.func_map:
                self.func_map[f] = fv.func_map[f]
            for f in fv._func_names:
                self.func_names.append(f)
            # if(name1 == "PairGrid"):
            #     print(fv.func_map)
        ast.NodeVisitor.generic_visit(self,node)


def check_for_hard_coded_warning(api_str,node,deprecate_map):
		
	for node1 in ast.walk(node):
		if isinstance(node1,ast.Call):
			description = " warn - "
			id1 = ""
			for n in ast.walk(node1):
				if(isinstance(n,ast.Str)):
					description += n.s 
				if(isinstance(n,ast.Constant)) and n.value and type(n.value)=="str":
					description += n.value
				if(isinstance(n,ast.Name)):
					id1 = n.id

			if id1.find("Deprecat")!=-1 or id1.find("FutureWarning")!=-1:
				# print(astunparse.dump(node1))
				if api_str not in deprecate_map:
					deprecate_map[api_str] = description+id1
				else:
					deprecate_map[api_str] += description+id1
	return deprecate_map

def check_for_doc_string_comments(api_str,doc_str,deprecate_map):
	if doc_str==None:
		return deprecate_map
	doc_str = doc_str.lower()
	if doc_str.find("deprecat")!=-1:
		doc_str_1 = doc_str.split("\n\n")
		str1 = " ~"
		for doc in doc_str_1:
			if doc.find("deprecat")!=-1:
				str1+=doc+" "
		str1 = ' '.join(str1.split())
		if api_str not in deprecate_map:
			deprecate_map[api_str] = str1
		else:
			deprecate_map[api_str] +=str1
	return deprecate_map

def check_for_deprecation_in_function(func_map,deprecate_map,temp):
	if func_map == None:
		return deprecate_map
	for name in func_map:
		node = func_map[name]
		doc_str = ast.get_docstring(node)
		deprecate_map = check_for_doc_string_comments(name,doc_str,deprecate_map)
		deprecate_map = check_for_hard_coded_warning(name,node,deprecate_map)
		fv = FuncVisitor(name)
		fv.visit(node)
		f = fv.return_decorator_list([node])
		#print(f)
		

		for i in range(len(f)):
			for j in f[i][1]:
				#print(f[i],j)
				if len(j)>0 and j.find('deprecate')!=-1 or j.find('api')!=-1:
					if name not in deprecate_map:
						# print(temp,name,j)
						deprecate_map[name] = "@"+j
					else:
						deprecate_map[name] += ", @"+j
	return deprecate_map
def check_for_deprecation_in_class(class_map,deprecate_map):
	for name in class_map:
		doc_str = ast.get_docstring(class_map[name])
		deprecate_map =  check_for_doc_string_comments(name,doc_str,deprecate_map)
	return deprecate_map


def automatic_api_deprecation_detection(file1, file2, package, path1):
    
    deprecate_map = {}

    def generate_ast_tree(path):
        code_text = open(path,encoding='utf-8').read()
        tree = ast.parse(code_text, type_comments = True)
        return tree

    def print_py_files(path,files_list):
        for file in os.listdir(path):
            if file == "tests":
                continue
            if(files_list == [] and file=="__init__"):
                continue
            if(os.path.isfile(path+str(file)) and re.search(".*\.py$",file)):
                files_list.append(path+str(file))
            elif(os.path.isdir(path+str(file))):
                print_py_files(path+str(file)+"/",files_list)
        return files_list
    py_files = print_py_files(path1,[])
    for file in py_files:
        l1 = file.split('/')
        API_string = package
        for i in range(3,len(l1)-1):
            API_string+="."+l1[i]   
        # print(l1,API_string)
        tree = generate_ast_tree(file)
        cv = ClassVisitor(API_string)
        cv.visit(tree)
        class_map = cv.class_map
        # print(class_map)
        func_map = cv.func_map
        func_names = cv.func_names
        deprecate_map = check_for_deprecation_in_class(cv.class_map,{})
        fv = FuncVisitor(API_string)
        fv.visit(tree)
        func_names_1 = fv._func_names
        func_map_1 = fv.func_map
        # print(func_names_1)
        functions_list = [f for f in func_names_1 if f not in func_names]
        f_map = {}
        # print(func_map)
        for f in functions_list:
            api_name = fv._name_api_map[f]
            # print(f,api_name)
            f_map[api_name] = func_map_1[api_name]
        if len(f_map)>0:
            deprecate_map = check_for_deprecation_in_function(f_map,deprecate_map,1)
        # print(f_map)
        deprecate_map = check_for_deprecation_in_function(func_map,deprecate_map,2) 

        for key, value in deprecate_map.items(): 
            str1 = key.split(".")[-1]
            file1.write('%s: %s\n' % (str1, value))
            file2.write('%s: %s, %s\n' % (key, value, file))


path_list = ['./sklearn/','./numpy/','./pandas/','./scipy/', './matplotlib/','./seaborn/','./keras/','./theano/','./tk/']
# path_list = ['./seaborn/seaborn/']
#path_list = ['./sklearn/']
for path in path_list:
	package = path.split("/")[-2]
	#print(package)
	file1 = open("./out/"+package+"_deprecated_api_elements.txt","w")
	file2 = open("./out/"+package+"_deprecated_api_elements_full.txt","w")
	automatic_api_deprecation_detection(file1,file2,package,path)
   