# modules/linode_instance_disk/variables.tf
variable "label" {
  type        = string
  default     = "linode-disk"
  description = "The label for the disk"
}

variable "size" {
  type        = number
  default     = 25088
  description = "The size of the disk in MB"
}

variable "image" {
  type        = string
  default     = "linode/debian12"
  description = "The default image for the disk"
}

variable "linode_id" {
  type        = string
  default     = ""
  description = "The ID of the Linode instance to attach the disk to"
}
