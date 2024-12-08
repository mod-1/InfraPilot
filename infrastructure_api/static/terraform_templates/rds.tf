module "rds_template" {
  source         = "./modules/rds"
  db_name        = ""
  db_engine      = ""
  instance_class = ""
  db_storage     = ""
}
