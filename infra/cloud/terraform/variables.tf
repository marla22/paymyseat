variable "aws_region" {
  description = "Regione AWS per il deployment"
  type        = string
  default     = "eu-central-1"
}

variable "environment" {
  description = "Ambiente di deploy"
  type        = string
  default     = "dev"
}