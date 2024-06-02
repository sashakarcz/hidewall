# modules/linode_nodebalancer/variables.tf
variable "label" {
  description = "The label for the Linode NodeBalancer"
  type        = string
  default     = ""
}

variable "region" {
  description = "The region for the Linode NodeBalancer"
  type        = string
  default     = "us-ord"
}

variable "linode_instance_ips" {
  description = "The IP addresses of the Linode instances"
  type        = list(string)
}

variable "linode_instance_ids" {
  description = "The IDs of the Linode instances"
  type        = list(string)
}
