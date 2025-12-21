import argparse
import struct
from typing import List, Dict, Tuple, Any

def read_atom(data:bytes, pos:int) -> Tuple[int, str, int, bytes]:
	size, atom_type = struct.unpack(">I4s", data[pos:pos+8])
	header_len = 8
	if size == 1:
		size = struct.unpack(">Q", data[pos+8:pos+16])[0]
		header_len = 16
	atom_type = atom_type.decode()
	payload = data[pos+header_len: pos+size] if size != 0 else b""
	return size, atom_type, header_len, payload

def parse_atoms(data:bytes, start:int=0, end:int|None=None, depth:int=0) -> List[Dict[str, Any]]:
	"""
	recursive parse `data` from start to end.
	return list of dict：
	{
		"type":    str,
		"size":    int,          # full size including header
		"offset":  int,          # relative to the beginning of whole file
		"header_len": int,
		"children": list[dict],   # sub-atom
		"payload":  bytes,   # payload(contain sub-atom)
	}
	"""
	if end is None:
		end = len(data)

	atoms: List[Dict[str, Any]] = []

	pos = start
	while pos < end:
		try:
			size, tp, hlen, payload = read_atom(data, pos)
		except Exception as e:
			print(e)
			print("There is break atom in the file, stop parse.")
			break
		if size == 0:
			size = end - pos   # 到文件尾

		atom: Dict[str, Any] = {
			"type": tp,
			"size": size,
			"offset": pos,
			"header_len": hlen,
			"payload": payload,
			"children": []
		}

		# if the atom has children, parse sub-atom recurrently.
		if tp in {"moov", "trak", "mdia", "mdhd", "minf", "stbl", "edts", "udta",
			"edts", "udta", "meta", "free", "skip", "mvex"}:
			atom["children"] = parse_atoms(payload, 0, len(payload), depth+1)
		atoms.append(atom)
		pos += size

	return atoms

def find_atoms(atoms:List[Dict[str, Any]], tp:str) -> List[Dict[str, Any]]:
	res: List[Dict[str, Any]] = []
	for a in atoms:
		if a["type"] == tp:
			res.append(a)
		if a["children"]:
			res += find_atoms(a["children"], tp)
	return res

def show_atoms(atoms, depth:int=0):
	columns = ["type", "size", "offset", "header_len"]
	for atom in atoms:
		info = f"{atom["type"]} offset:{atom["offset"]} size:{atom["size"]}"
		print(("|   " * (depth - 1) + "|___" if depth else "") + info)
		if atom["children"]:
			show_atoms(atom["children"], depth+1)

if __name__ == "__main__":
	parser = argparse.ArgumentParser(description="Parse and show atoms of a mp4 file.")
	parser.add_argument("File", type=str, help="Path of mp4 file.")
	args = parser.parse_args()

	with open(args.File, "rb") as f:
		bs = f.read()
	atoms = parse_atoms(bs)
	show_atoms(atoms)
