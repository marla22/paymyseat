# Generazione Key Pair SSH per l'accesso ad EC2
resource "tls_private_key" "ssh_key" {
  algorithm = "RSA"
  rsa_bits  = 4096
}

resource "aws_key_pair" "generated_key" {
  key_name   = "paymyseat-ec2-key"
  public_key = tls_private_key.ssh_key.public_key_openssh
}

# Salva la chiave privata locale per consentire ad Ansible di connettersi
resource "local_file" "private_key" {
  content         = tls_private_key.ssh_key.private_key_pem
  filename        = "${path.module}/../ansible/paymyseat_key.pem"
  file_permission = "0600"
}

# AMI Ubuntu 22.04 LTS più recente
data "aws_ami" "ubuntu" {
  most_recent = true
  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }
  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
  owners = ["099720109477"] # Canonical
}

# Istanza EC2
resource "aws_instance" "app_server" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = "t3.micro"
  subnet_id              = aws_subnet.public_subnet.id
  vpc_security_group_ids = [aws_security_group.app_sg.id]
  key_name               = aws_key_pair.generated_key.key_name

  tags = {
    Name = "paymyseat-app-server"
  }
}