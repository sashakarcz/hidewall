variable "linode_token" {
  description = "Token for Linode API"
  type        = string
}

variable "access_key" {
  description = "Token for Linode S3 API"
  type        = string
}

variable "secret_key" {
  description = "Secret for Linode S3 API"
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
  default = ""
}