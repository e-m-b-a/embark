# On the VM we need to use:

# sudo apt update (optinoal)
# sudo apt install openssh-server
# sudo systemctl enable ssh
# sudo systemctl start ssh
# sudo apt install sshfs
# pip install sshfs

from sshfs import SSHFileSystem

# Connect to the VM using SSHFS
fs = SSHFileSystem(host='PLACEHOLDER', username='PLACEHOLDER', password='PLACEHOLDER', port='PLACEHOLDER') #nosec

# Specify the remote file path and the local destination path
remote_path = 'test'        # Path to the remote file on the VM
local_path = r'test'      # Local path where the file will be saved

with fs.open(remote_path, 'rb') as remote_file:
    with open(local_path, 'wb') as local_file:
        local_file.write(remote_file.read())

print(f"File was successfully saved: {local_path}")
