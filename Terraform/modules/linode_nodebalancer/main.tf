# modules/linode_nodebalancer/main.tf
resource "linode_nodebalancer" "nodebalancer" {
  label  = var.label
  region = var.region
}

output "nodebalancer_id" {
  value = linode_nodebalancer.nodebalancer.id
}
