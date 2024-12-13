module "rds_template_{unique_id}" {
  source         = "./modules/rds"
  db_name        = ""
  db_engine      = ""
  instance_class = ""
  db_storage     = ""
}

output "rds_template_output_{unique_id}" {
  description = "The endpoint of the RDS instance"
  value       = "${module.rds_template_{unique_id}.rds_endpoint},admin,password123"
}
output "rds_username_{unique_id}" {
  description = "The RDS database username"
  value       = "admin"
}

output "rds_password_{unique_id}" {
  description = "The RDS database password"
  value       = "mypassword123"
}
