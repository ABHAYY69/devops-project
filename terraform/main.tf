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
  ingress {
    from_port   = 5432
    to_port     = 5432
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
resource "aws_db_instance" "campusbazaar_db" {
  identifier           = "campusbazaar-db"
  engine               = "postgres"
  engine_version       = "18.2"
  instance_class       = "db.t3.micro"
  allocated_storage    = 20
  db_name              = "campusbazaar"
  username             = "dbadmin"
  password             = "CampusBazaar123!"
  publicly_accessible  = true
  skip_final_snapshot  = true
  vpc_security_group_ids = [aws_security_group.devops_sg.id]

  tags = {
    Name = "campusbazaar-db"
  }
}
resource "aws_s3_bucket" "campusbazaar_images" {
  bucket        = "campusbazaar-images-756269935915"
  force_destroy = true

  tags = {
    Name = "campusbazaar-images"
  }
}

resource "aws_s3_bucket_public_access_block" "campusbazaar_images" {
  bucket = aws_s3_bucket.campusbazaar_images.id

  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

resource "aws_s3_bucket_policy" "campusbazaar_images" {
  bucket = aws_s3_bucket.campusbazaar_images.id
  depends_on = [aws_s3_bucket_public_access_block.campusbazaar_images]

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "PublicReadGetObject"
        Effect    = "Allow"
        Principal = "*"
        Action    = "s3:GetObject"
        Resource  = "${aws_s3_bucket.campusbazaar_images.arn}/*"
      }
    ]
  })
}

output "s3_bucket_name" {
  value = aws_s3_bucket.campusbazaar_images.bucket
}
output "db_endpoint" {
  value = aws_db_instance.campusbazaar_db.endpoint
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