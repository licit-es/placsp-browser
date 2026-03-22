#!/bin/bash
set -e

USERNAME=$1
SSH_PUBKEY=$2

if [ -z "$USERNAME" ] || [ -z "$SSH_PUBKEY" ]; then
  echo "Uso: ./01-setup-users.sh <usuario> <clave_publica_ssh>"
  exit 1
fi

adduser --disabled-password --gecos "" "$USERNAME"
mkdir -p /home/$USERNAME/.ssh
echo "$SSH_PUBKEY" > /home/$USERNAME/.ssh/authorized_keys
chown -R $USERNAME:$USERNAME /home/$USERNAME/.ssh
chmod 700 /home/$USERNAME/.ssh
chmod 600 /home/$USERNAME/.ssh/authorized_keys

echo "Usuario $USERNAME creado. Para darle sudo: usermod -aG sudo $USERNAME"
