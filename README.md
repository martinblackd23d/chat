# Run

server:
```python3 chatserver.py <port>```
eg. ```python3 chatserver.py 12345```
client
```python3 chatclient.py <host> <port> <username>```
eg. ```python3 chatclient.py localhost 12345 user1```

client only works on Linux or WSL, because using selectors with stdin and pipes breaks on Windows

# Messages
```
TYPE OPERATION
<payload>
```

1. login
```
client -> server
```
COMMAND LOGIN
<username>
```
server -> client
```
COMMAND REGISTER/LOGIN
```
client -> server
```
COMMAND PASSWORD
<password>
```
server -> client
```
COMMAND OK
```

2. public message
client -> server
```
COMMAND PM
```
server -> client
```
COMMAND OK
```
client -> server
```
DATA PUBLIC
<message>
```
server -> all clients
```
DATA PUBLIC
<username>: <message>
```
server -> client
```
COMMAND OK
```

3. direct message
client -> server
```
COMMAND DM
```
server -> client
```
COMMAND OK
<userlist>
```
client -> server
```
DATA DIRECT
<recipient>: <message>
```
server -> recipient
```
DATA DIRECT
<sender>: <message>
```
server -> client
```
COMMAND OK
```

4. exit
client -> server
```
COMMAND EX
```

5. error
```
COMMAND ERROR
<error message>
```


