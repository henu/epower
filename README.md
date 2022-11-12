Installing to Raspberry
=======================

```
sudo apt install ansible sshpass
cd ansible
printf "[raspberry]\nYOUR_RASPBERRY_IP_ADDRESS\n" > hosts.ini
ansible-playbook install_epower.yaml -i hosts.ini -k
```
