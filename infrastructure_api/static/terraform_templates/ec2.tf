module "ec2_template" {
  source            = "./modules/ec2"
  ec_instance_name  = ""
  ec2_instance_type = ""
  ec2_ami_id        = ""
}
