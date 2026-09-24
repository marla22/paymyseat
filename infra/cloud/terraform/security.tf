# Security Group per l'istanza EC2 App Server
resource "aws_security_group" "app_sg" {
  name        = "paymyseat-app-sg"
  description = "Allow SSH, HTTP e Ingress traffic"
  vpc_id      = aws_vpc.paymyseat_vpc.id

  # SSH per la gestione tramite Ansible
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # HTTP per l'accesso alle API / Ingress
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Porta Flask payment-api per collaudo diretto
  ingress {
    from_port   = 5000
    to_port     = 5000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Traffico uscente illimitato
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "paymyseat-app-sg"
  }
}