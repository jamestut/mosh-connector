#!/usr/bin/env python3

import argparse
import sys
from subprocess import run, PIPE, STDOUT
import os
import random

# env var name: (desc, default)


class Enviro:
	_inst = None

	def __new__(cls):
		if cls._inst is None:
			cls.envparams = {
				"MOSH_SERVER": ("The location of mosh server in remote.", "mosh-server"),
				"MOSH_CLIENT": ("The location of local mosh client.", "mosh-client"),
				"MOSH_PROGRESS": ("Set to nonempty to show progress.", None)
			}
			cls._inst = super().__new__(cls)
		return cls._inst

	def __getitem__(self, key):
		_, default = self.envparams[key]
		return os.environ.get(key, default)

def _run(*args, **kwargs):
	defaults = {
		'stderr': PIPE,
		'stdout': PIPE,
		'check': True
	}
	for k, v in defaults.items():
		kwargs.setdefault(k, v)
	return run(*args, **kwargs)

def _get_local_locale():
	r = _run(['locale'])
	for l in r.stdout.split(b'\n'):
		k, v = l.split(b'=', 1)
		if k == b'LANG':
			return v.decode('ascii')
	raise ValueError("Cannot find 'LANG' in system locale.")

def _get_local_mosh_term_color():
	r = _run(['mosh-client', '-c'])
	return r.stdout[:-1].decode('ascii')

def _run_mosh_server(sshargs, color, locale):
	"""
	Returns a tuple of (remote server IP, mosh port, mosh secret)
	Returns None OR raises exception on error!
	"""
	DELIMSTR = f"-MOSH-CONNECT-DELIM-{random.randrange(sys.maxsize)}"
	env = Enviro()

	# since mosh only supports v4, we ask SSH to do so as well
	if "-4" not in sshargs:
		sshargs = ["-4"] + sshargs

	mosh_args = [env["MOSH_SERVER"], "new", "-c", color, "-s", "-l", f"LANG={locale}"]

	ssh_cmds = [
		"echo $SSH_CONNECTION", # we find out remote IP via "SSH_CONNECTION"
		f"echo {DELIMSTR}", # so that we know where is the end of "env"
		" ".join(mosh_args)
	]
	r = _run(['ssh'] + sshargs + ["--"] + [" && ".join(ssh_cmds)],
		stderr=STDOUT, check=False)
	lines = r.stdout.split(b"\n")

	try:
		delim_idx = lines.index(DELIMSTR.encode('ascii'))
	except ValueError:
		print("Cannot find delimiter in server's response.", file=sys.stderr)
		print("Server returned:", file=sys.stderr)
		return None
		raise ValueError("Cannot found delimiter in server's response.")

	if r.returncode:
		# error from server's side, let the user know
		print("Error running mosh-server on SSH host!", file=sys.stderr)
		print("Server returned:", file=sys.stderr)
		for l in lines[delim_idx + 1:]:
			print(l.decode('utf8'), file=sys.stderr)
		return None

	if delim_idx == 0:
		raise ValueError("No content found before delimiter in server's response.")

	# info to be returned
	remote_ip = None
	mosh_port = None
	mosh_secret = None

	scinfo = lines[delim_idx - 1].split()
	if len(scinfo) != 4:
		raise ValueError("Unknown SSH_CONNECTION response.")
	remote_ip = scinfo[2].decode('ascii')

	for l in lines[delim_idx + 1:]:
		if l.startswith(b"MOSH CONNECT"):
			splt = l.rsplit(maxsplit=2)
			if len(splt) != 3:
				raise ValueError("Unknown MOSH CONNECT response.")
			mosh_port = splt[-2].decode('ascii')
			mosh_secret = splt[-1].decode('ascii')
			# check if port is a valid integer
			int(mosh_port)
			break

	if remote_ip and mosh_port and mosh_secret:
		return remote_ip, mosh_port, mosh_secret

	raise ValueError("Failed to retreive server's response.")

def main():
	"""
	1. get local locale
	2. get local terminal color
	3. get remote IP address
	4. start mosh on server
	5. connect local mosh
	6. profit!
	"""
	app_name = os.path.basename(sys.argv[0])
	env = Enviro()

	if len(sys.argv) < 2:
		print(f"Usage: {app_name} (ssh arguments)")
		print()
		print("To change this connector's defaults, set the following environment variable:")
		for e, v in env.envparams.items():
			desc, default = v
			print(f" - {e}" + (f" (default: {default})" if default is not None else ""))
			print(f"   {desc}")
		return 1

	progress = env["MOSH_PROGRESS"]

	# get the local info necessary to start mosh server
	if progress:
		print("Retreiving local terminal info ...")
	lc = _get_local_mosh_term_color()
	ll = _get_local_locale()

	try:
		if progress:
			print("Starting mosh server on remote host ...")
		r = _run_mosh_server(sys.argv[1:], lc, ll)
		# assume the _run_mosh_server already printed the error out if we got None
		if r is None:
			return 1
		remote_ip, mosh_port, mosh_secret = r
	except Exception as ex:
		print(f"Error running mosh on server: {ex}", file=sys.stderr)
		return 1

	os.environ["MOSH_KEY"] = mosh_secret
	if progress:
		print("Starting mosh client ...")
	os.execvp(env["MOSH_CLIENT"], ["mosh-client", remote_ip, mosh_port])

if __name__ == "__main__":
	exit(main())
