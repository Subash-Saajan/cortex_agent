resource "aws_db_subnet_group" "main" {
  name       = "cortex-agent-db-subnet-group"
  subnet_ids = aws_subnet.public[*].id

  tags = {
    Name = "cortex-agent-db-subnet-group"
  }
}

resource "aws_rds_cluster" "db" {
  cluster_identifier      = "cortex-agent-db"
  engine                  = "aurora-postgresql"
  engine_version          = "15.3"
  database_name           = "cortexdb"
  master_username         = "postgres"
  master_password         = var.db_password
  db_subnet_group_name    = aws_db_subnet_group.main.name
  vpc_security_group_ids  = [aws_security_group.rds.id]
  skip_final_snapshot     = true
  deletion_protection     = false

  tags = {
    Name = "cortex-agent-db"
  }
}

resource "aws_rds_cluster_instance" "db" {
  cluster_identifier = aws_rds_cluster.db.id
  instance_class     = "db.t3.micro"
  engine              = aws_rds_cluster.db.engine
  engine_version      = aws_rds_cluster.db.engine_version
  publicly_accessible = true

  tags = {
    Name = "cortex-agent-db-instance"
  }
}
