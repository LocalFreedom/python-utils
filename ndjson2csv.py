import argparse
import csv
import json
import sys

def read_ndjson(ndjson_file:open) -> dict:
	lines = ndjson_file.readlines()
	data = [json.loads(line) for line in lines]
	ndjson_file.close()
	return data
# read multi-line json data

def write_csv(csv_file:str, data:dict):
	tab_head = set()
	for item in data:
		tab_head |= set(item.keys())
	# combine keys as table titles

	writer = csv.DictWriter(csv_file, fieldnames=tab_head)
	writer.writeheader()
	for item in data:
		writer.writerow(item)
	csv_file.close()
# write dict data to the csv file

def ndjson_to_csv(ndjson_file:open, csv_file) -> dict:
	data = read_ndjson(ndjson_file)
	write_csv(csv_file, data)
	return data

if __name__ == '__main__':
	parser = argparse.ArgumentParser(prog='ndjson2csv.py', description='Convert ndjson file to csv format file.')
	parser.add_argument('ndjson_file', type=open, help='ndjson filename')
	parser.add_argument('-o', '--output', type=argparse.FileType('w', encoding='utf-8'), required=False, help='csv filename')
	args = parser.parse_args()
	if args.output is None:
		args.output = open(args.ndjson_file.name + '.csv', 'w', encoding='utf-8')
	ndjson_to_csv(args.ndjson_file, args.output)
