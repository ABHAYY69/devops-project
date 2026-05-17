terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "ap-south-1"
}

resource "aws_ecr_repository" "devops_app" {
  name         = "devops-app"
  force_delete = true
}

resource "aws_security_group" "devops_sg" {
  name        = "devops-sg"
  description = "Allow SSH and app traffic"

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 5000
    to_port     = 5000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_instance" "devops_server" {
  ami                    = "ami-07711b2f361d92b11"
  instance_type          = "t3.micro"
  key_name               = "devops-key"
  vpc_security_group_ids = [aws_security_group.devops_sg.id]
   user_data = <<-EOF
    #!/bin/bash
    sudo yum install docker -y
    sudo service docker start
    sudo usermod -a -G docker ec2-user
    aws ecr get-login-password --region ap-south-1 | docker login --username AWS --password-stdin 756269935915.dkr.ecr.ap-south-1.amazonaws.com
    docker pull 756269935915.dkr.ecr.ap-south-1.amazonaws.com/devops-app:latest
    docker run -d --name devops-app -p 5000:5000 756269935915.dkr.ecr.ap-south-1.amazonaws.com/devops-app:latest
  EOF
  tags = {
    Name = "devops-server"
  }
}
resource "aws_eip" "devops_eip" {
  instance = aws_instance.devops_server.id
  domain   = "vpc"
}

output "elastic_ip" {
  value = aws_eip.devops_eip.public_ip
}
output "ec2_public_ip" {
  value = aws_instance.devops_server.public_ip
}

output "ecr_url" {
  value = aws_ecr_repository.devops_app.repository_url
}