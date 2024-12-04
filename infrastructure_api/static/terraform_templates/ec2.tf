locals {
  instance_name = "ec2-instance-template"
  instance_type = "t2.micro"
  ami_id        = "ami-09d56f8956ab235b3"
}

# Create EC2 Instance
resource "aws_instance" "app_server" {
  ami           = local.ami_id
  instance_type = local.instance_type

  tags = {
    Name = local.instance_name
  }

  lifecycle {
    ignore_changes = [ami]
  }
}

# Output the public IP
output "public_ip" {
  value = aws_instance.app_server.public_ip
}
