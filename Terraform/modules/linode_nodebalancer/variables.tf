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

variable "instances" {
  description = "List of strings of Linodes"
  type        = list(string)
  default     = []
}
