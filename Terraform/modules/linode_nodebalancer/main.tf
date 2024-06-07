# modules/linode_nodebalancer/main.tf
resource "linode_nodebalancer" "hidewall-lb" {
  label  = var.label
  region = var.region
}

resource "linode_nodebalancer_config" "config" {
  nodebalancer_id = linode_nodebalancer.hidewall-lb.id
  protocol        = "https"
  port            = 443
  check           = "connection"
  ssl_cert        = var.ssl_cert
  ssl_key         = var.ssl_key
}

resource "linode_nodebalancer_node" "node" {
  count              = length(var.linode_instance_ids)
  nodebalancer_id    = linode_nodebalancer.hidewall-lb.id
  config_id          = linode_nodebalancer_config.config.id
  address            = "${var.linode_instance_ips[count.index]}:8080"
  label              = "node-${count.index}"
  weight             = 100
}
