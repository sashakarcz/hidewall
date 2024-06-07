# envs/prod/main.tf

provider "linode" {
  token = var.linode_token
}

# Define the inputs for the instance and disks module
locals {
  instances = {
    "ord-swarm-1" = { label = "ord-swarm-1" }
    "ord-swarm-2" = { label = "ord-swarm-2" }
    "ord-swarm-3" = { label = "ord-swarm-3" }
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

  label              = each.value.label
  root_pass          = var.root_pass
  linode_token       = var.linode_token
}


# Define Linode NodeBalancer Module
module "my_nodebalancer" {
  source = "../../modules/linode_nodebalancer"

  label                = "lb-hidewall"
  region               = "us-ord"
  linode_instance_ids  = [for hidewall-node in module.instances : hidewall-node.id]
  linode_instance_ips  = flatten([for hidewall-node in module.instances : hidewall-node.ip_address])
  ssl_key              = file(var.ssl_key)
  ssl_cert             = file(var.ssl_cert)
}

module "firewall_cloudflare" {
  source = "../../modules/linode_firewall_cloudflare"

  nodebalancers = [module.my_nodebalancer.nodebalancer_id]
}

module "firewall_ingress" {
  source     = "../../modules/linode_firewall_ingress"

  linodes    = [for hidewall-node in module.instances : hidewall-node.id]
  allowed_ip = var.allowed_ip
}

resource "null_resource" "create_hosts_file" {
  count = length(module.instances)

  triggers = {
    instance_id = module.instances[keys(module.instances)[count.index]].id
  }

  provisioner "local-exec" {
    command = <<EOF
    echo "${module.instances[keys(module.instances)[count.index]].ip_address} node-${count.index}" >> hosts
    EOF
  }
}
