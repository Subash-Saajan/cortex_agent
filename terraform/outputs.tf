output "ecs_service_public_ip" {
  description = "Public IP of ECS service"
  value       = aws_ecs_service.backend.network_configuration[0].subnets
}

output "rds_endpoint" {
  description = "RDS endpoint"
  value       = aws_db_instance.db.endpoint
}

output "cloudfront_domain" {
  description = "CloudFront distribution domain"
  value       = aws_cloudfront_distribution.frontend.domain_name
}

output "ecr_backend_repository_url" {
  description = "ECR backend repository URL"
  value       = aws_ecr_repository.backend.repository_url
}

output "ecr_frontend_repository_url" {
  description = "ECR frontend repository URL"
  value       = aws_ecr_repository.frontend.repository_url
}

output "ecs_cluster_name" {
  description = "ECS cluster name"
  value       = aws_ecs_cluster.main.name
}

output "ecs_service_name" {
  description = "ECS service name"
  value       = aws_ecs_service.backend.name
}

output "alb_dns_name" {
  description = "ALB DNS name"
  value       = aws_lb.backend.dns_name
}

output "alb_zone_id" {
  description = "ALB Zone ID for Route53/Cloudflare"
  value       = aws_lb.backend.zone_id
}

output "acm_certificate_arn" {
  description = "ACM certificate ARN"
  value       = aws_acm_certificate.backend.arn
}

output "acm_certificate_validation_options" {
  description = "ACM certificate DNS validation records"
  value       = aws_acm_certificate.backend.domain_validation_options
}
