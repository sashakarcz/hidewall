# envs/prod/main.tf
provider "linode" {
  token = var.linode_token
}

# Define the inputs for the instance and disks module
locals {
  instances = {
    "ord-swarm-1" = { label = "instance1" }
    "ord-swarm-2" = { label = "instance2" }
    "ord-swarm-3" = { label = "instance3" }
  }

  disks = {
    "ord-swarm-1" = { label = "disk1" }
    "ord-swarm-2" = { label = "disk2" }
    "ord-swarm-3" = { label = "disk3" }
  }
}

module "instances" {
  source = "../../modules/linode_instance"

  for_each = local.instances

  label      = each.value.label
}

module "disks" {
  source = "../../modules/linode_disks"

  for_each = local.disks

  label      = each.value.label
  linode_id = module.instances[each.key].id
}


# Define Linode NodeBalancer Module
module "my_nodebalancer" {
  source = "../../modules/linode_nodebalancer"

  label        = "lb-hidewall"
  region       = "us-ord"
  instances    = [for instance in module.instances : instance.id]
}

module "firewall_cloudflare" {
  source = "../../modules/linode_firewall_cloudflare"

  nodebalancers = [module.my_nodebalancer.nodebalancer_id]
}

# Define Linode Firewall Ingress Module
module "firewall_ingress" {
  source = "../../modules/linode_firewall_ingress"
}
