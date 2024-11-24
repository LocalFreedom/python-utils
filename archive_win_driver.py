import argparse
import datetime
import logging
import os
import pathlib
import re
import shutil

import chardet


def util_equal_sign_in_inf_line(s:str) -> bool:
	quote = False
	for c in s:
		if c == '"':
			quote = not quote
		elif quote:
			continue
		elif c == '=':
			return True
	return False

def parse_inf(inf_path:str) -> dict:
	"""
	parse a windows inf file as a diction.
	[section] name lower.
	without variable replace.
	return {section: {key: value}, section: string}
	"""
	config = {}
	section = None

	with open(inf_path, "rb") as f:
		inf_context = f.read()
		inf_code = chardet.detect(inf_context)
		lines = inf_context.decode(inf_code['encoding']).split('\n')

	for line in lines:
		line = line.split(";")[0].strip()

		if not line:
			continue

		if line.startswith("[") and line.endswith("]"):
			section = line[1:-1].strip().lower()
			if section in config:
				logging.warning("parse_inf find repeat section [%s]." % section)
			config[section] = {}
			continue

		if section == "Strings".lower():
			key, value = line.split("=", 1)
			key = key.strip()
			if key in config[section]:
				logging.warning("parse_inf find repeat key in [Strings] section.")
			config[section][key] = value.strip()
			continue

		if util_equal_sign_in_inf_line(line):
			key, value = line.split("=", 1)
			config[section][key.strip()] = value.strip()
		else:
			if not config[section]:
				config[section] = line
			elif type(config[section]) is str:
				config[section] += '\n' + line
			else:
				logging.warning("parse_inf find undefined format in [%s]." % section)

	logging.debug("parse_inf(%s) complete." % inf_path)
	return config

def extra_version(inf:dict) -> (datetime.date, str):
	verstr = inf["Version".lower()]["DriverVer"]

	if '%' in verstr:
		for key, value in inf["Strings".lower()].items():
			verstr = verstr.replace(f"%{key}%", value)
	# replace variable

	rd, version = verstr.split(",")
	rd = datetime.datetime.strptime(rd.strip(), "%m/%d/%Y")
	version = version.strip()
	logging.debug("extra_version %s, %s." % (rd, version))
	return rd, version

def get_inf_name(dirname:str) -> str:
	dirver_name = os.path.split(dirname)[-1].split('.')[0].lower()
	filenames = os.listdir(dirname)
	for filename in filenames:
		if filename.lower().endswith('.inf') and filename[:-4].lower() == dirver_name:
			return filename
	return None

def analyse_batch(drivers_dir:str) -> dict:
	"""
	analyse one driver-export directory.
	return {device: [(date, version, hash, path)]}
	"""
	dirs = os.listdir(drivers_dir)
	driver_info = {}

	for dirname in dirs:
		prefix, suffix = dirname.split(".")
		inf_name = get_inf_name(os.path.join(drivers_dir, dirname))
		if inf_name is None:
			logging.error("get_inf_name failed of %s." % dirname)
			continue
		inf_path = os.path.join(drivers_dir, dirname, inf_name)
		inf_config = parse_inf(inf_path)
		release_date, version = extra_version(inf_config)
		driver_info[prefix] = driver_info.get(prefix, [])
		driver_info[prefix].append((release_date, version, suffix, os.path.join(drivers_dir, dirname)))

	logging.info("analyse_batch(%s) find %d kinds of device drivers." % (drivers_dir, len(driver_info)))
	return driver_info

def analyse_multibatch(drivers_dirs:list) -> dict:
	"""
	combine multi directories exported driver infomation.
	driver_stat: {device: {version: [(release_date, hash, path)]}}
	"""
	driver_stat = {}

	for batch_dir in drivers_dirs:
		batch_info = analyse_batch(batch_dir)
		for device, info in batch_info.items():
			driver_stat[device] = driver_stat.get(device, {})
			for item in info:
				version = item[1]
				driver_stat[device][version] = driver_stat[device].get(version, [])
				driver_stat[device][version].append((item[0], item[2], item[3]))

	logging.info("analyse_multibatch(%s) find %d kinds of device drivers." % (drivers_dirs, len(driver_stat)))
	return driver_stat

def print_driver_stat(driver_stat:dict, path_cut:int=10):
	"""
	driver_stat: {device: {version: [(release_date, hash, path)]}}
	"""
	devices = sorted(driver_stat.keys())
	none_cnt = 0
	single_cnt = 0
	multi_cnt = 0

	for device in devices:
		print(device)
		for version in sorted(driver_stat[device].keys()):
			print("\t%s" % version)
			for item in driver_stat[device][version]:
				date = item[0].strftime("%Y%m%d")
				print("\t\t%s\t%s\t%s" % (date, item[1], item[2][:path_cut]))
		driver_cnt = len(driver_stat[device])
		if driver_cnt > 1:
			multi_cnt += 1
		elif driver_cnt == 1:
			single_cnt += 1
		else:
			none_cnt += 1
	print("Total %d devices:" % len(devices))
	print("\t%d have only one driver." % single_cnt)
	print("\t%d have multi drivers." % multi_cnt)
	print("\t%d extra with some error." % none_cnt)

def execute(driver_stat:dict, dst_dir:str, method:str="copy", exclude_prefix:list=[]):
	candidate_list = []
	exclude_cnt = 0
	if exclude_prefix:
		exclude_pattern = re.compile(r"^(%s)" % "|".join(map(re.escape, exclude_prefix)))

	for device in driver_stat:
		if exclude_prefix:
			if exclude_pattern.match(device):
				exclude_cnt += 1
				logging.info("execute %s is exclude by prefix rule." % device)
				continue

		version_max = ""
		release_latest = None
		selected = None
		for version in driver_stat[device]:
			for item in driver_stat[device][version]:
				if not release_latest or release_latest < item[0]:
					selected = (device, item[0], version, item[1], item[2], version<version_max)
					if version < version_max:
						logging.warning("%s drivers occur more recent with less version." % device)
						logging.warning("version %s less than %s, but release date %s is newer than %s." % (version, version_max, item[0], release_latest))
					release_latest = item[0]
					version_max = version

			if version > version_max:
				version_max = version
		candidate_list.append(selected)

	print("--------------- Select Result ---------------")
	for item in candidate_list:
		print("%s will select %s %s from %s.%s" % (item[0], item[1].strftime("%Y%m%d"), item[2], item[4], "\033[91m Note!\033[0m" if item[5] else ""))
	# candidate_list(device, release_date, version, hash, path, flag)
	if exclude_prefix:
		print("%d device drivers are excluded by prefix rule." % exclude_cnt)

	ans = input("Are you sure %s these %d drivers to %s?(Yes/No)" % (method, len(candidate_list), dst_dir))
	if ans != "Yes":
		logging.info("execute be canceled by user.")
		print("execute be canceled by user.")
		return 0
	else:
		if not os.path.exists(dst_dir):
			mkd = input("The destination directory is not exist.\nContinue with y/yes:")
			if mkd.lower() == "y" or  mkd.lower() == "yes":
				os.makedirs(dst_dir)
			else:
				logging.info("execute stop at creating dst_dir by user.")
				print("You deny to create destination directory, program will stop and exit.")
				return 0

		if method == "copy":
			for item in candidate_list:
				shutil.copytree(item[4], os.path.join(dst_dir, os.path.split(item[4])[-1]), copy_function=shutil.copy2)
			print("Copy %d drivers to %s success." % (len(candidate_list), dst_dir))
		elif method == "move":
			for item in candidate_list:
				shutil.move(item[4], dst_dir)
			print("Move %d drivers to %s success." % (len(candidate_list), dst_dir))
		else:
			logging.warn("undefined method.")
			return -1

	logging.info("execute %s %d drivers to %s complete." % (method, len(candidate_list), dst_dir))
	return 0

if __name__ == "__main__":
	logging.basicConfig(format="%(levelname)s:%(message)s", level=logging.ERROR)

	parser = argparse.ArgumentParser(description="Collect the latest version windows driver of devices from some dism export directories.\nYou can export drivers use `dism /online /export-driver /destination:C:\MyDrivers` in windows terminal.")
	parser.add_argument("-s", "--src", action="extend", nargs="+", type=pathlib.Path)
	parser.add_argument("-d", "--dst", default="LatestDrivers", type=pathlib.Path, help="Where to collect the selected drivers.")
	parser.add_argument("-m", "--method", default="copy", choices=["copy", "move"])
	parser.add_argument("--exclude-prefix", action="extend", nargs="+", type=str, help="Exclude devices driver with the prefix.")
	parser.add_argument("--print-cut", default=10, type=int, help="Cut too long path in print.")
	args = parser.parse_args()

	driver_stat = analyse_multibatch(args.src)
	print_driver_stat(driver_stat, path_cut=args.print_cut)
	ret = execute(driver_stat, args.dst, method=args.method, exclude_prefix=args.exclude_prefix)
