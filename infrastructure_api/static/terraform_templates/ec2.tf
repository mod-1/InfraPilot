module "ec2_template_{unique_id}" {
  source            = "./modules/ec2"
  ec_instance_name  = ""
  ec2_instance_type = ""
  ec2_ami_id        = ""
}

output "ec2_template_output_{unique_id}" {
  description = "The ID of the EC2 instance"
  value       = module.ec2_template_{unique_id}.ec2_public_ip
}
