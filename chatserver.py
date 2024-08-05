import threading
import socket
import sys
import re
import hashlib

# maintain user connections and credentials
authentication = {}
active_users = {}
lock = threading.Lock()

# personal message
def pm(client, username, payload):
	# check user
	if username == None:
		client.send('COMMAND ERROR\nNot logged in.'.encode())
		return 'FAIL', None
	client.send('COMMAND OK\n'.encode())

	# get message
	data = client.recv(1024)
	if not data:
		return 'FAIL', None
	data = data.decode()
	if data[:data.find('\n')] != 'DATA PUBLIC':
		return 'FAIL', None
	message = data[data.find('\n')+1:]

	# send message
	for user in active_users:
		if active_users[user] == client:
			continue
		active_users[user].send(('DATA PUBLIC\n' + username + ': ' + message).encode())
	client.send('COMMAND OK\n'.encode())
	return 'PM', None

# direct message
def dm(client, username, payload):
	# check user
	if username == None:
		client.send('COMMAND ERROR\nNot logged in.'.encode())
		return 'FAIL', None
	
	# send user list
	user_list = list(active_users.keys())
	client.send(('COMMAND OK\n' + '\n'.join(user_list)).encode())
	
	# get message and recipient
	data = client.recv(1024)
	if not data:
		return 'FAIL', None
	data = data.decode()
	if data[:data.find('\n')] != 'DATA DIRECT':
		return
	recipient = data[data.find('\n')+1:data.find(':')]
	if recipient not in active_users:
		client.send('COMMAND ERROR\nUser not found.'.encode())
		return 'FAIL', None
	message = data[data.find(':')+2:]

	# send message
	active_users[recipient].send(('DATA DIRECT\n' + username + ': ' + message).encode())
	client.send('COMMAND OK\n'.encode())
	return 'DM', None

# exit
def exit(client, username, payload):
	return 'EX', None

# login
def login(client, username, payload):
	# check user
	username = re.sub(r'\W', '', payload)
	if username == '':
		client.send('COMMAND ERROR\nInvalid username.'.encode())
		return 'FAIL', None
	if username in active_users:
		client.send('COMMAND ERROR\nUser already logged in.'.encode())
		return 'FAIL', None
	client.send(f'COMMAND {"LOGIN" if username in authentication else "REGISTER"}\n'.encode())

	# get password
	data = client.recv(1024)
	if not data:
		return 'FAIL', None
	data = data.decode()
	if data[:data.find('\n')] != 'COMMAND PASSWORD':
		return 'FAIL', None
	password = data[data.find('\n')+1:]

	status = 'FAIL'
	content = None
	message = 'COMMAND ERROR\n'
	file_content = None
	with lock:
		if username in active_users:
			message = 'COMMAND ERROR\nUser already logged in.'
		# register
		elif username not in authentication:
			authentication[username] = hashlib.sha256(password.encode()).hexdigest()
			file_content = f'{username}:{authentication[username]}\n'
			message = 'COMMAND OK\n'
			status = 'LOGIN'
			content = username
			active_users[username] = client
		# login
		elif authentication[username] == hashlib.sha256(password.encode()).hexdigest():
			message = 'COMMAND OK\n'
			status = 'LOGIN'
			content = username
			active_users[username] = client
		else:
			message = 'COMMAND ERROR\nInvalid password.'

	# manage resource intense file and network operations outside of lock
	if file_content:
		with open('users.txt', 'a') as file:
			file.write(f'{username}:{authentication[username]}\n')
	client.send(message.encode())
	return status, content

# available commands
COMMANDS = {
	'PM': pm,
	'DM': dm,
	'EX': exit,
	'LOGIN': login,
}

def handle_client(client):
	username = None
	try:
		while True:
			# receive and parse data
			data = client.recv(1024)
			if not data:
				break
			data = data.decode()
			type = data[:data.find(' ')]
			if type != 'COMMAND':
				continue
			command = data[data.find(' ')+1:data.find('\n')].upper()
			payload = data[data.find('\n')+1:]
			if command not in COMMANDS:
				continue

			# execute command
			status, content = COMMANDS[command](client, username, payload)
			if status == 'LOGIN':
				username = content
			if status == 'EX':
				break
	except ConnectionResetError:
		pass
	finally:
		# cleanup
		with lock:
			active_users.pop(username, None)
		client.close()

def main():
	# load authentication
	with open('users.txt', 'r') as file:
		for line in file:
			username, password = line.strip().split(':')
			authentication[username] = password

	# get port
	if len(sys.argv) != 2:
		print('Usage: python3 chatserver.py <port>')
		return
	port = int(sys.argv[1])

	# create socket
	server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	server.bind(('', port))
	server.listen(5)
	print('Server is listening on port', port)

	while True:
		# accept connection
		client, addr = server.accept()
		# handoff to thread
		thread = threading.Thread(target=handle_client, args=(client,))
		thread.start()

if __name__ == '__main__':
	main()