resource "aws_db_subnet_group" "main" {
  name       = "cortex-agent-db-subnet-group"
  subnet_ids = aws_subnet.public[*].id

  tags = {
    Name = "cortex-agent-db-subnet-group"
  }
}

resource "aws_db_instance" "db" {
  identifier           = "cortex-agent-db"
  engine               = "postgres"
  instance_class       = "db.t3.micro"
  allocated_storage    = 20
  db_name              = "cortexdb"
  username             = "postgres"
  password             = var.db_password
  db_subnet_group_name = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  publicly_accessible  = true
  skip_final_snapshot  = true
  deletion_protection  = false

  tags = {
    Name = "cortex-agent-db"
  }
}
