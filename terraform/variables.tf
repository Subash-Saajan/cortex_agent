variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "db_password" {
  description = "RDS master password"
  type        = string
  sensitive   = true
}

variable "google_client_id" {
  description = "Google OAuth Client ID"
  type        = string
  sensitive   = true
}

variable "google_client_secret" {
  description = "Google OAuth Client Secret"
  type        = string
  sensitive   = true
}

variable "claude_api_key" {
  description = "Anthropic Claude API Key"
  type        = string
  sensitive   = true
}

variable "jwt_secret" {
  description = "JWT Secret Key"
  type        = string
  sensitive   = true
  default     = "your-secret-key"
}

variable "google_redirect_uri" {
  description = "Google OAuth Redirect URI"
  type        = string
  default     = "https://cortex.subashsaajan.site/api/auth/callback"
}