import argparse
import ast
import logging
import os
import sys
import traceback

def extra_imports(file_path:str) -> set:
	"""
	Extract imports from a python file.
	Args:
		file_path(str): python file path.
	Returns:
		set: all import package name in the file.
	"""
	with open(file_path, 'r', encoding='utf-8') as f:
		tree = ast.parse(f.read(), filename=file_path)

	raw_imports = set()
	for node in ast.walk(tree):
		if isinstance(node, ast.Import):
			for alias in node.names:
				raw_imports.add(alias.name)
		elif isinstance(node, ast.ImportFrom):
			if node.module:
				raw_imports.add(node.module)

	imports = set()
	for name in raw_imports:
		module = name.split('.')[0]
		imports.add(module)
	# Ex: from django.conf --> django.conf. But we only want django as an import.

	return imports

def extra_all_imports(project_path:str, ignore_dirs:list=None, follow_links:bool=True, ignore_error:bool=False) -> [dict, set]:
	all_imports = {}
	current_packages = set()

	for root, dirs, files in os.walk(project_path, topdown=True, followlinks=follow_links):
		dirs[:] = [d for d in dirs if d not in ignore_dirs]
		current_packages.add(os.path.basename(root))

		for fn in files:
			if fn.endswith('.py'):
				file_path = os.path.join(root, fn)
				try:
					imports = extra_imports(file_path)
				except Exception as e:
					if ignore_error:
						traceback.print_exc()
						logging.warn("Failed on file: %s" % file_name)
						continue
					else:
						logging.error("Failed on file: %s" % file_name)
						raise e
				for item in imports:
					all_imports[item] = all_imports.get(item, set())
					all_imports[item].add(file_path)
				current_packages.add(os.path.splitext(fn)[0])
	return all_imports, current_packages

def is_stdlib(module_name:str) -> bool:
	return module_name in sys.stdlib_module_names

def classify_imports(project_path:str, ignore_dirs=None, follow_links=True, ignore_error=False) -> [set, set, dict]:
	all_imports, current_packages = extra_all_imports(project_path, ignore_dirs=ignore_dirs, follow_links=follow_links, ignore_error=ignore_error)
	imports_std = set()
	imports_self = set()
	imports_third = {}
	for module_name in all_imports:
		if is_stdlib(module_name):
			imports_std.add(module_name)
		elif module_name in current_packages:
			imports_self.add(module_name)
		else:
			imports_third[module_name] = all_imports[module_name]
	return imports_std, imports_self, imports_third

if __name__ == '__main__':
	parser = argparse.ArgumentParser(description="Analyze a Python project, extract all imported packages, list the package names, and classify them into standard libraries, self-contained, and third-party packages.")
	parser.add_argument("Project", type=str, help="The Python project root path.")
	default_ignore_dirs = [
		".hg",
		".svn",
		".git",
		".tox",
		".ipynb_checkpoints",
		"__pycache__",
		"env",
		"venv",
		".venv",
	]
	parser.add_argument("-i", "--ignore-dirs", action="extend", nargs="*", default=default_ignore_dirs, type=str, help="The folder names to be ignored in the project.", metavar="Folder")
	parser.add_argument("-l", "--follow-links", action="store_true", help="Follow the symbolic link in the project folder.")
	parser.add_argument("-e", "--ignore-error", action="store_true", help="Skip any errors when extract imports info.")
	parser.add_argument("-t", "--show-third-distribution", action="store_true", help="Show the files where third-party packages are imported.")
	args = parser.parse_args()
	assert os.path.isdir(args.Project)

	imports_std, imports_self, imports_third = classify_imports(args.Project, ignore_dirs=args.ignore_dirs, follow_links=args.follow_links, ignore_error=args.ignore_error)
	print("\nIMPORT STDLIB %d:\n\t" % len(imports_std), imports_std)
	print("\nIMPORT SELF %d:\n\t" % len(imports_self), imports_self)
	print("\nIMPORT THIRD %d:\n\t" % len(imports_third), imports_third.keys())
	if args.show_third_distribution:
		print("="*10, "Third-party Package Distribution", "="*10)
		for item in imports_third:
			print("\n%s be imported in %d files:\n\t" % (item, len(imports_third[item])), imports_third[item])
