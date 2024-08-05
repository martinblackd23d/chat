import socket
import re
import sys
import threading
import selectors
import os

# create pipes
command_read, command_write = os.pipe()
data_read, data_write = os.pipe()
exited = False

# listen for messages
def listen(client):
	global exited
	sel = selectors.DefaultSelector()
	sel.register(client, selectors.EVENT_READ)

	while not exited:
		# receive message
		# handle timeout for responsiveness and graceful exit
		for key, _ in sel.select(timeout=1):
			if key.fileobj != client:
				continue
			if not (_ & selectors.EVENT_READ):
				continue
			raw_data = client.recv(1024)
			data = raw_data.decode()
			if data[:4] == 'DATA':
				# send to data pipe
				os.write(data_write, raw_data)
			if data[:7] == 'COMMAND':
				# send to command pipe
				os.write(command_write, raw_data)
	client.close()

# login
def login(client, username):
	# initiate login
	client.send(f'COMMAND LOGIN\n{username}'.encode())
	response = os.read(command_read, 1024).decode()
	if not (response == 'COMMAND REGISTER\n' or response == 'COMMAND LOGIN\n'):
		print('Error logging in')
		if response[:13] == 'COMMAND ERROR':
			print(response[14:])
		return False
	
	# get password
	print('Enter password: ', end='')
	password = input()
	client.send(f'COMMAND PASSWORD\n{password}'.encode())
	response = os.read(command_read, 1024).decode()
	if response[:10] != 'COMMAND OK':
		print('Error logging in')
		if response[:13] == 'COMMAND ERROR':
			print(response[14:])
		return False
	return True

# exit
def exit(client, sel):
	client.send('COMMAND EX\n'.encode())
	return 'EX', None

# get input while handling incoming messages
def get_input(sel, prompt):
	input_received = False
	while not input_received:
		print(prompt, end='', flush=True)
		for key, _ in sel.select():
			if key.fileobj == sys.stdin:
				# get input and return
				user_input = input()
				input_received = True
			if key.fileobj == data_read:
				# print message arriving while waiting for input
				print_message()
	return user_input

# public message
def pm(client, sel):
	# initiate public message
	client.send('COMMAND PM\n'.encode())
	data = os.read(command_read, 1024).decode()
	if data[:10] != 'COMMAND OK':
		print('Error sending message')
		if data[:13] == 'COMMAND ERROR':
			print(data[14:])
		return 'FAIL', None
	
	# send message
	message = get_input(sel, 'Enter message: ')
	client.send(f'DATA PUBLIC\n{message}'.encode())
	data = os.read(command_read, 1024).decode()
	if data[:10] != 'COMMAND OK':
		print('Error sending message')
		if data[:13] == 'COMMAND ERROR':
			print(data[14:])
		return 'FAIL', None
	return 'PM', None

# direct message
def dm(client, sel):
	# initiate direct message
	client.send('COMMAND DM\n'.encode())
	data = os.read(command_read, 1024).decode()
	if data[:10] != 'COMMAND OK':
		print('Error sending message')
		return 'FAIL', None
	
	# get recipient and message
	recipient = get_input(sel, f'Active users:{data[10:]}\nEnter recipient: ')
	message = get_input(sel, 'Enter message: ')
	client.send(f'DATA DIRECT\n{recipient}: {message}'.encode())
	data = os.read(command_read, 1024).decode()
	if data[:10] != 'COMMAND OK':
		print('Error sending message')
		if data[:13] == 'COMMAND ERROR':
			print(data[14:])
		return 'FAIL', None
	return 'DM', None

# print message from data pipe
def print_message():
	data = os.read(data_read, 1024).decode()
	operation = data[data.find(' ')+1:data.find('\n')]
	message = data[data.find('\n')+1:]
	if operation == 'PUBLIC':
		print(f'\nPublic message from {message}')
	elif operation == 'DIRECT':
		print(f'\nDirect message from {message}')

COMMANDS = {
	'PM': pm,
	'DM': dm,
	'EX': exit,
}

def main():
	global exited
	# get arguments
	if len(sys.argv) != 4:
		print('Usage: python3 chatclient.py <server_name> <port> <username>')
		return
	host = sys.argv[1]
	port = int(sys.argv[2])
	if port < 1 or port > 65535:
		print('Invalid port number')
		return
	username = re.sub(r'\W', '', sys.argv[3])

	# create socket
	try:
		client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		client.connect((host, port))
		print('Connected to server')
	except ConnectionRefusedError:
		print('Connection refused')
		return
	except socket.gaierror:
		print('Invalid server name')
		return

	# create listener thread
	listener = threading.Thread(target=listen, args=(client,))
	listener.start()

	# login
	if not login(client, username):
		exited = True
		client.close()
		listener.join()
		return

	# main loop
	sel = selectors.DefaultSelector()
	sel.register(data_read, selectors.EVENT_READ)
	sel.register(sys.stdin, selectors.EVENT_READ)
	while not exited:
		# get command
		command = get_input(sel, f'{username}>').upper()
		if command not in COMMANDS:
			continue

		# execute command
		status, content = COMMANDS[command](client, sel)
		if status == 'EX':
			exited = True
			break

	# cleanup
	client.close()
	listener.join()



if __name__ == '__main__':
	main()
