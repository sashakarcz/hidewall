# modules/linode_instance/variables.tf
variable "image" {
  type        = string
  default     = "linode/debian12"
  description = "The default image for the disk"
}

variable "label" {
  description = "The label for the Linode instance"
  type        = string
  default     = "hidewall-swarm"
}

variable "region" {
  description = "The region where the Linode instance will be created"
  type        = string
  default     = "us-ord"
}

variable "tags" {
  description = "The tags for the Linode instance"
  type        = list(string)
  default     = ["swarm"]
}

variable "type" {
  description = "The Linode instance type"
  type        = string
  default     = "g6-nanode-1"
}

variable "root_pass" {
  description = "The root password for the Linode instance"
  type        = string
}
