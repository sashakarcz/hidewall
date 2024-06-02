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

