# modules/linode_nodebalancer/main.tf
resource "linode_nodebalancer" "hidewall-lb" {
  label  = var.label
  region = var.region
}

output "nodebalancer_id" {
  value = linode_nodebalancer.hidewall-lb.id
}
