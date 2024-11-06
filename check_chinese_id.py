def check_china_id(id_num:str) -> bool:
	assert len(id_num) == 18
	S = 0
	for i in range(17):
		S += int(id_num[i]) * 2 ** (17 - i) % 11
	checksum = (12 - (S % 11)) % 11
	checkchar = str(checksum) if checksum < 10 else 'X'
	return checkchar == id_num[17]

id_num = input('Please input Chinese ID card number:')
res = check_china_id(id_num)
print('Checksum correct.' if res else 'Checksum invalid.')
