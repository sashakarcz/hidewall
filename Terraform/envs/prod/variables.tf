variable "linode_token" {
  description = "Token for Linode API"
  type        = string
  sensitive   = true
}

variable "access_key" {
  description = "Token for Linode S3 API"
  type        = string
  sensitive   = true
}

variable "secret_key" {
  description = "Secret for Linode S3 API"
  type        = string
  sensitive   = true
}

variable "allowed_ip" {
  description = "IP allowed for SSH ingress"
  type        = string
}

variable "linode_instance_ids" {
  type    = list(string)
  default = []
}

variable "disk_size" {
  type    = number
  default = 0
}

variable "swap_size" {
  type    = number
  default = 0
}

variable "image" {
  type    = string
  default = ""
}

variable "root_pass" {
  type    = string
}

variable "linode_instance_ips" {
  type    = list(string)
  default = []
}

variable "ssl_key" {
  type = string
}

variable "ssl_cert" {
  type = string
}
