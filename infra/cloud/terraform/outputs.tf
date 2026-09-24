output "ec2_public_ip" {
  description = "IP pubblico dell'istanza EC2"
  value       = aws_instance.app_server.public_ip
}

# Genera il file per Ansible
resource "local_file" "ansible_inventory" {
  content  = <<EOF
[app_servers]
${aws_instance.app_server.public_ip} ansible_user=ubuntu ansible_ssh_private_key_file=./paymyseat_key.pem ansible_ssh_common_args='-o StrictHostKeyChecking=no'
EOF
  filename = "${path.module}/../ansible/inventory.ini"
}