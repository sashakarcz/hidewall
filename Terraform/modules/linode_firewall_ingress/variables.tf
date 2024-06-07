variable "label" {
  type    = string
  default = ""
}

variable "linodes" {
  type    = list(number)
  default = []
}

variable "nodebalancers" {
  type    = list(number)
  default = []
}

variable "allowed_ip" {
  type    = string
  default = ""
}
