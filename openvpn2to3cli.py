import argparse
import os

def insert_auth(config:list, name:str, auth_file):
	assert os.path.exists(auth_file), auth_file
	if name+'\n' in config:
	    pos = config.index(name+'\n') + 1
	else:
	    pos = len(config)
	    config.insert(pos, name+'\n')
	    pos += 1
	with open(auth_file) as af:
		auth = af.read()
	username, password = auth.strip().split('\n')
	config.insert(pos, f'</{name}>\n')
	config.insert(pos, f'{password}\n')
	config.insert(pos, f'{username}\n')
	config.insert(pos, f'<{name}>\n')
	return config

def combine_config(ovpn_file:str, auth_user_pass:str=None, http_proxy:list=None, http_proxy_user_pass:str=None, http_proxy_option:list=None, data_ciphers:str=None, data_ciphers_fallback:str=None):
	assert os.path.exists(ovpn_file), ovpn_file
	with open(ovpn_file) as of:
		config = of.readlines()

	if auth_user_pass:
		insert_auth(config, 'auth-user-pass', auth_user_pass)

	if http_proxy:
		ip, port = http_proxy
		config.append(f'http-proxy {ip} {port}\n')
	if http_proxy_user_pass:
		insert_auth(config, 'http-proxy-user-pass', http_proxy_user_pass)
	if http_proxy_option:
		for option in http_proxy_option:
			config.append(f'http-proxy-option {option}\n')

	if data_ciphers:
		config.append(f'data-ciphers {data_ciphers}\n')
	if data_ciphers_fallback:
		config.append(f'data-ciphers-fallback {data_ciphers_fallback}\n')

	return config

def pipeline(config:list, tmp_config_fn:str):
	with open(tmp_config_fn, 'w') as tf:
		tf.writelines(config)
	print(f'Combined config file is writed to {tmp_config_fn}.')

	os.system(f'openvpn3 session-start --config {tmp_config_fn}')
	os.system('openvpn3 sessions-list')
	input('Press Enter to stop VPN:')
	os.system(f'openvpn3 session-manage --config {tmp_config_fn} --disconnect')

if __name__ == '__main__':
	parser = argparse.ArgumentParser(description="Combining the start command line of openvpn2.x to the .ovpn config file for openvpn3.x")
	parser.add_argument("--config", type=str, required=True)
	parser.add_argument("--auth-user-pass", type=str, default=None)
	parser.add_argument("--http-proxy-retry", action='store_true', default=None)
	parser.add_argument("--http-proxy", nargs=2, type=str, default=None)
	parser.add_argument("--http-proxy-user-pass", type=str, default=None)
	parser.add_argument("--http-proxy-option", action='append', type=str, default=None)
	parser.add_argument("--socks-proxy", nargs='?', type=str, default=None)
	parser.add_argument("--data-ciphers", type=str, default=None)
	parser.add_argument("--data-ciphers-fallback", type=str, default=None)
	parser.add_argument("-s", "--only-show-combined", action='store_true', help="Only print the ovpn config file without write and run.")
	parser.add_argument("-o", "--tmp-config-fn", type=str, default="__.ovpn")

	args = parser.parse_args()
	print(args.http_proxy_option)
	assert not args.socks_proxy, "socks-proxy is not support in 3.x version."

	config = combine_config(args.config, auth_user_pass=args.auth_user_pass, http_proxy=args.http_proxy, http_proxy_user_pass=args.http_proxy_user_pass, http_proxy_option=args.http_proxy_option, data_ciphers=args.data_ciphers, data_ciphers_fallback=args.data_ciphers_fallback)
	if args.only_show_combined:
		print("".join(config))
		exit(0)
	pipeline(config, args.tmp_config_fn)
